import logging
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Optional, List
from fsm import TERMINAL_STATE, INITIAL_STATE, JsonParams
from fsm.fsm_persistence import StateStorage
from sqlalchemy import asc, inspect, DateTime
from sqlalchemy.exc import OperationalError

from fsm.fsm_postgre.fsm_postgre_models import StateEntry, StateStatus, StateError
from sqlalchemy.orm.session import Session, sessionmaker

logger = logging.getLogger(__name__)


@contextmanager
def _acquire_db_session(DBSession: sessionmaker) -> Session:
    """used in 'with' statement"""
    db_session = DBSession(expire_on_commit=False)
    db_session.expire_on_commit = False
    try:
        yield db_session
        db_session.commit()
        db_session.expunge_all()
    except BaseException as ex:
        logger.error('Error on commit - {}'.format(str(ex)))
        try:
            db_session.rollback()
            raise
        except OperationalError:
            logger.error('Error on rollback')
            raise ex
    finally:
        db_session.close()


class PostgreStateStorage(StateStorage):
    def __init__(self, DBSession: sessionmaker, tenant_id: str) -> None:
        self.DBSession = DBSession
        self.tenant_id = tenant_id
        super().__init__()

    def get_last_state(self, run_id: Optional[str]) -> Optional[StateEntry]:
        with _acquire_db_session(self.DBSession) as db_session:
            last_state_query = db_session.query(StateStatus).filter(StateStatus.tenant_id == self.tenant_id)
            if run_id is not None:
                last_state_query = last_state_query.filter(StateStatus.run_id == run_id)
            last_state = last_state_query.first()
            if last_state:
                return db_session.query(StateEntry).\
                    filter(StateEntry.tenant_id == self.tenant_id).\
                    filter(StateEntry.id == last_state.last_state_id).\
                    first()
            else:
                return None

    def new_initial_state(self, params=None) -> StateEntry:
        entry: StateEntry = StateEntry(name=INITIAL_STATE,
                                       run_id=str(uuid.uuid4()),
                                       start_time=datetime.utcnow(),
                                       end_time=datetime.utcnow(),
                                       params=params,
                                       tenant_id=self.tenant_id)
        with _acquire_db_session(self.DBSession) as db_session:
            db_session.add(entry)
        return entry

    def _upsert_state(self, state: StateEntry) -> None:
        with _acquire_db_session(self.DBSession) as db_session:
            existing_state: Optional[StateEntry] = db_session.query(StateEntry).\
                filter(StateEntry.name == state.name).\
                filter(StateEntry.tenant_id == self.tenant_id).\
                filter(StateEntry.run_id == state.run_id).\
                first()
            if existing_state is None:
                db_session.add(state)
            else:
                state.id = existing_state.id
                db_session.merge(state)

        self.set_last_state(state)

    def find_state(self, state_name: str, run_id: str) -> StateEntry:
        with _acquire_db_session(self.DBSession) as db_session:
            return db_session.query(StateEntry).\
                filter(StateEntry.run_id == run_id). \
                filter(StateEntry.tenant_id == self.tenant_id).\
                filter(StateEntry.name == state_name).\
                first()

    def yield_state(self, state: StateEntry, is_yielded: bool) -> None:
        state.yielded = is_yielded
        with _acquire_db_session(self.DBSession) as db_session:
            db_session.merge(state)

    def save_state(self, state: StateEntry) -> None:
        with _acquire_db_session(self.DBSession) as db_session:
            db_session.merge(state)
        self.set_last_state(state)

    def terminate(self, run_id: str) -> None:
        state = StateEntry(name=TERMINAL_STATE,
                           start_time=datetime.utcnow(),
                           end_time=datetime.utcnow(),
                           errors=[StateError(error="Max retry count reached", visit_idx=1)],
                           run_id=run_id,
                           tenant_id=self.tenant_id)
        self._upsert_state(state)

    def set_current_state(self, state_name: str, run_id: str, err: Optional[str], params: JsonParams,
                          start_time: DateTime, end_time: DateTime) -> None:
        existing_state = self.find_state(state_name, run_id)
        if existing_state:
            if err:
                existing_state.errors.append(StateError(error=err, visit_idx=existing_state.visit_count + 1))
            existing_state.params = params
            existing_state.start_time = start_time
            existing_state.end_time = end_time
            existing_state.visit_count += 1
            self.save_state(existing_state)
        else:
            state = StateEntry(name=state_name,
                               start_time=start_time,
                               end_time=end_time,
                               errors=[StateError(error=err, visit_idx=1)] if err else [],
                               params=params,
                               run_id=run_id,
                               visit_count=1,
                               tenant_id=self.tenant_id)
            self._upsert_state(state)

    def get_db_history(self) -> List[StateEntry]:
        with _acquire_db_session(self.DBSession) as db_session:
            return db_session.query(StateEntry).order_by(asc(StateEntry.id)).all()

    def set_last_state(self, state: StateEntry) -> None:
        inspect(state)
        with _acquire_db_session(self.DBSession) as db_session:
            status: StateStatus = db_session.query(StateStatus).\
                filter(StateStatus.tenant_id == self.tenant_id).\
                first()
            if status is not None:
                db_session.delete(status)
            status = StateStatus(last_state_id=state.id,
                                 ref_state_name=state.name,
                                 update_time=datetime.utcnow(),
                                 tenant_id=self.tenant_id)
            db_session.add(status)
