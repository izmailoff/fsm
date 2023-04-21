from datetime import datetime
from typing import Optional, List

from bson import ObjectId

from fsm import TERMINAL_STATE, INITIAL_STATE
from fsm.fsm_persistence import StateStorage

from fsm.fsm_mongo.fsm_mongo_models import StateEntry, StateStatus, StateError


class MongoStateStorage(StateStorage):

    def get_last_state(self) -> Optional[StateEntry]:
        last_state = StateStatus.objects().first()
        if last_state:
            return StateEntry.objects(id=last_state.lastStateId).first()
        else:
            return None

    def new_initial_state(self):
        return StateEntry(name=INITIAL_STATE, startTime=datetime.utcnow(),
                          endTime=datetime.utcnow(), params={})

    def _upsert_state(self, state: StateEntry) -> None:
        state = StateEntry.objects(name=state.name, runId=state.runId).modify(
            upsert=True, new=True, set__startTime=state.startTime, set__endTime=state.endTime, set__params=state.params,
            set__visitCount=state.visitCount, set__errors=state.errors, set__yielded=state.yielded
        )
        self.set_last_state(state)

    def find_state(self, state_name: str, run_id: ObjectId) -> StateEntry:
        return StateEntry.objects(runId=run_id, name=state_name).first()

    def yield_state(self, state: StateEntry, is_yielded: bool) -> None:
        state.yielded = is_yielded
        state.save()

    def save_state(self, state: StateEntry) -> None:
        state.save()
        self.set_last_state(state)

    def terminate(self, run_id) -> None:
        state = StateEntry(name=TERMINAL_STATE, startTime=datetime.utcnow(),
                           endTime=datetime.utcnow(),
                           errors=[StateError(error="Max retry count reached", visitIdx=1)], runId=run_id)
        self._upsert_state(state)

    def set_current_state(self, state_name, run_id, err: Optional[str], params, start_time, end_time) -> None:
        existing_state = self.find_state(state_name, run_id) # TODO: rewrite as a single upsert or update?
        if existing_state:
            if err:
                existing_state.errors.append(StateError(error=err, visitIdx=existing_state.visitCount + 1))
            existing_state.params = params
            existing_state.startTime = start_time
            existing_state.endTime = end_time
            existing_state.visitCount += 1
            self.save_state(existing_state)
        else:
            state = StateEntry(name=state_name, startTime=start_time, endTime=end_time,
                               errors=[StateError(error=err, visitIdx=1)] if err else [],
                               params=params, runId=run_id,
                               visitCount=1)
            self._upsert_state(state)

    def get_db_history(self) -> List[StateEntry]:
        return list(StateEntry.objects.order_by("_id"))

    def set_last_state(self, state: StateEntry) -> None:
        StateStatus.objects().modify(upsert=True, new=True, set__lastStateId=state.id,
                                     set__updateTime=datetime.utcnow(), set__refStateName=state.name)
