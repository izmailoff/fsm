from uuid import UUID

from datetime import datetime
from typing import Optional, List, TypeVar, Dict, Any, Generic

from fsm import JsonParams

RunId = TypeVar('RunId', int, str, UUID)


class StateEntryT(Generic[RunId]):
    runId: RunId
    name: str
    yielded: bool
    params: Dict[str, Any]
    visitCount: int

    def is_terminal(self) -> bool:
        raise NotImplementedError


class StateStorage(Generic[RunId]):

    def get_last_state(self) -> Optional[StateEntryT[RunId]]:
        pass

    def new_initial_state(self) -> StateEntryT[RunId]:
        pass

    def save_state(self, state: StateEntryT[RunId]) -> None:
        pass

    def yield_state(self, state: StateEntryT[RunId], is_yielded: bool) -> None:
        pass

    def find_state(self, state_name: str, run_id: RunId) -> Optional[StateEntryT[RunId]]:
        pass

    def terminate(self, run_id: RunId) -> None:
        pass

    def set_current_state(self, state_name: str, run_id: RunId, err: Optional[str], params: JsonParams,
                          start_time: datetime, end_time: datetime) -> None:
        pass

    def get_db_history(self) -> List[StateEntryT[RunId]]:
        pass

    def set_last_state(self, state: StateEntryT[RunId]) -> None:
        pass

