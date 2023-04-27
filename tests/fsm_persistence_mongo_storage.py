from datetime import datetime
from typing import Optional, List

from bson import ObjectId

from fsm import INITIAL_STATE, TERMINAL_STATE
from fsm.fsm_persistence import StateStorage
from tests.fsm_persistence_mongo_models import StateEntry, StateStatus, StateError


class MongoStateStorage(StateStorage):

    def get_last_state(self) -> Optional[StateEntry]:
        last_state = StateStatus.objects().first()
        if last_state:
            return StateEntry.objects(id=last_state.last_state_id).first()
        else:
            return None

    def new_initial_state(self):
        return StateEntry(name=INITIAL_STATE, start_time=datetime.utcnow(),
                          end_time=datetime.utcnow(), params={})

    def _upsert_state(self, state: StateEntry) -> None:
        state = StateEntry.objects(name=state.name, run_id=state.run_id).modify(
            upsert=True, new=True, set__start_time=state.start_time, set__end_time=state.end_time, set__params=state.params,
            set__visit_count=state.visit_count, set__errors=state.errors, set__yielded=state.yielded
        )
        self.set_last_state(state)

    def find_state(self, state_name: str, run_id: ObjectId) -> StateEntry:
        return StateEntry.objects(run_id=run_id, name=state_name).first()

    def yield_state(self, state: StateEntry, is_yielded: bool) -> None:
        state.yielded = is_yielded
        state.save()

    def save_state(self, state: StateEntry) -> None:
        state.save()
        self.set_last_state(state)

    def terminate(self, run_id) -> None:
        state = StateEntry(name=TERMINAL_STATE, start_time=datetime.utcnow(),
                           end_time=datetime.utcnow(),
                           errors=[StateError(error="Max retry count reached", visitIdx=1)], run_id=run_id)
        self._upsert_state(state)

    def set_current_state(self, state_name, run_id, err: Optional[str], params, start_time, end_time) -> None:
        existing_state = self.find_state(state_name, run_id) # TODO: rewrite as a single upsert or update?
        if existing_state:
            if err:
                existing_state.errors.append(StateError(error=err, visitIdx=existing_state.visit_count + 1))
            existing_state.params = params
            existing_state.start_time = start_time
            existing_state.end_time = end_time
            existing_state.visit_count += 1
            self.save_state(existing_state)
        else:
            state = StateEntry(name=state_name, start_time=start_time, end_time=end_time,
                               errors=[StateError(error=err, visitIdx=1)] if err else [],
                               params=params, run_id=run_id,
                               visit_count=1)
            self._upsert_state(state)

    def get_db_history(self) -> List[StateEntry]:
        return list(StateEntry.objects.order_by("_id"))

    def set_last_state(self, state: StateEntry) -> None:
        StateStatus.objects().modify(upsert=True, new=True, set__last_state_id=state.id,
                                     set__update_time=datetime.utcnow(), set__ref_state_name=state.name)
