from functools import wraps

from copy import copy
from datetime import datetime
from inspect import isfunction
from typing import Dict, Tuple, Callable, Any, Optional, TypeVar, Union, cast, Generic

from logging_conf.logging import get_child_logger, add_dynamic_fields_to_logger
from fsm import DEFAULT, StateDefinition
from fsm.fsm_persistence import StateStorage, RunId


FsmTransitionResult = Tuple[bool, Optional[str], Optional[Dict[str, Any]]]

FsmParams = Dict[str, Any]

FsmAction = Callable[[FsmParams], FsmTransitionResult]

S = TypeVar('S')
U = Optional[Callable[[], 'U']]


def trampoline(f: Callable[..., Union[Callable[..., S], S]]) -> Callable[..., S]:
    def g(*args: Any, **kwargs: Any) -> S:
        result = f(*args, **kwargs)
        while isfunction(result):
            res = cast(Callable[[], S], result)()
            result = res
        return cast(S, result)
    return g


class FiniteStateMachine(Generic[RunId]):
    def __init__(self, state_storage: StateStorage[RunId],
                 state_transitions: StateDefinition,
                 max_state_visits: Dict[str, int] = {DEFAULT: 1},
                 log_extra: Dict[str, Any] = {}) -> None:
        self.store: StateStorage[RunId] = state_storage
        self.state_transitions = state_transitions
        self.max_visits = copy(max_state_visits)
        self.max_visits[DEFAULT] = self.max_visits.get(DEFAULT, 1)
        self.pipeline_str = {k: (v[1:]) for k, v in self.state_transitions.items()}
        self.run_id: Optional[RunId] = None
        self.logger = get_child_logger("", "fsm", log_extra)
        add_dynamic_fields_to_logger(self.logger, {'runid': self._get_run_id})

    def _get_run_id(self) -> str:
        return str(self.run_id)

    def run(self) -> None:
        self.logger.debug("Run function called.")
        trampoline(self._advance_to_next)()

    def _advance_to_next(self, current_run_id: Optional[RunId] = None) -> U:
        self.logger.info("Started FSM execution. Trying to advance to the next state of pipeline.")
        self.logger.debug("PIPELINE: {}.".format(self.pipeline_str))
        last_state = self.store.get_last_state()
        if not last_state or (last_state.is_terminal() and current_run_id is None):
            current_state = self.store.new_initial_state()
            self.logger.debug("Starting a new run with run ID [{}].".format(current_state.runId))
            self.store.save_state(current_state)
        else:
            current_state = last_state
        self.run_id = current_state.runId
        self.logger.info("Current state is: [{}] for run ID [{}].".format(current_state.name, current_state.runId))
        transition, success_state, failure_state, continue_run = self.state_transitions[current_state.name]
        if not transition:
            self.logger.info("No transition step defined. Nothing else to do, terminating.")
            return None
        else:
            self.logger.info("We have next state to advance to, checking if we need to yield execution.")
            if continue_run:
                self.logger.info("Execution can continue without yielding.")
            else:
                if current_state.yielded:
                    self.store.yield_state(current_state, False)
                    self.logger.info("Resuming execution of the yielded state.")
                else:
                    self.store.yield_state(current_state, True)
                    self.logger.info("Yielding execution of the next state until next run.")
                    return None
            self.logger.info("Checking if next state has been visited before.")
            if self._max_visits_exceeded(success_state, current_state.runId):
                return None
            else:
                start_time = datetime.utcnow()
                self.logger.debug("Entering transition from {} to {} with params {}.".format(current_state.name, success_state, current_state.params))
                is_successful, err, params = self.with_state_transition_result(transition)(current_state.params)
                self.logger.debug("Transition from {} to {} finished with new params {}.".format(current_state.name, success_state, params))
                end_time = datetime.utcnow()
                if not is_successful and self._max_visits_exceeded(failure_state, current_state.runId):
                    return None
                next_state = success_state if is_successful else failure_state
                self.store.set_current_state(next_state, current_state.runId, err, params, start_time, end_time)
                return lambda: self._advance_to_next(current_state.runId)

    def _max_visits_exceeded(self, state_name: str, run_id: RunId) -> bool:
        next_state = self.store.find_state(state_name, run_id)
        success_visit_limit = self.max_visits.get(state_name, self.max_visits[DEFAULT])
        if next_state and next_state.visitCount >= success_visit_limit:
            self.logger.warning("Maximum attempts for state [{}] reached. Terminating.".format(state_name))
            self.store.terminate(next_state.runId)
            self.logger.debug("Successfully saved terminal state for run ID [{}].".format(run_id))
            return True
        else:
            if next_state:
                visits = next_state.visitCount + 1
            else:
                visits = 1
            self.logger.info("Visited state [{}] {} out of max {} times.".format(state_name, visits, success_visit_limit))
            return False

    def with_state_transition_result(self, func: FsmAction) -> Callable[..., FsmTransitionResult]:
        @wraps(func)
        def wrapper(*args: Any) -> FsmTransitionResult:
            try:
                result = func(*args)
                if isinstance(result, bool):  # True == success, False == failed, no way to pass params down the chain
                    return result, None, {}
                elif isinstance(result, tuple):  # format: (success?, str error or None, params as dict, {} or None)
                    return result
                else:
                    # returns value directly, which has to be a dictionary or None,
                    # otherwise we wouldn't know what to do with it.
                    return True, None, result if result else {}
            except Exception as e:
                self.logger.exception(e)
                return False, "class: [{}], doc: [{}], msg: [{}]".format(e.__class__, e.__doc__, str(e)), {}
        return wrapper


