import unittest
from unittest.mock import MagicMock

import mongomock as mongomock
from mongoengine.connection import get_connection

from mongoengine import connect

from fsm.fsm_mongo.fsm_mongo_storage import MongoStateStorage

from fsm import TERMINAL_STATE, INITIAL_STATE, DEFAULT

from fsm.fsm import FiniteStateMachine as FSM


class TestFiniteStateMachine(unittest.TestCase):

    def setUp(self):
        connect('mongoenginetest', mongo_client_class=mongomock.MongoClient)
        conn = get_connection()
        conn.drop_database('mongoenginetest')
        self.db = MongoStateStorage()

    def assert_current_FSM_state(self, state):
        last_state = self.db.get_last_state()
        self.assertEqual(state, last_state.name)

    def test_fsm_with_no_states_should_raise_exception_because_init_state_is_missing(self):
        fsm = FSM(self.db, {})

        with self.assertRaises(KeyError):
            fsm.run()

    def test_fsm_with_init_only_and_no_transitions_should_terminate_without_errors(self):
        fsm = FSM(self.db, {INITIAL_STATE: (None, None, None, False)})

        fsm.run()

    def test_fsm_should_successfully_execute_transition_actions(self):
        params = {"val": 1}
        transition_action = MagicMock(return_value=(True, "", params))
        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, TERMINAL_STATE, "ABORT", True),
            TERMINAL_STATE: (None, None, None, False)
        })

        self.assertIsNone(self.db.get_last_state())
        fsm.run()
        transition_action.assert_called_once_with({})
        self.assert_current_FSM_state(TERMINAL_STATE)

    def test_fsm_should_transition_to_failed_state_if_action_failed(self):
        params = {"val": 1}
        transition_action = MagicMock(return_value=(False, "", params))
        failure_transition_action = MagicMock(return_value=(True, "", {}))
        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, TERMINAL_STATE, "ABORT", True),
            "ABORT": (failure_transition_action, TERMINAL_STATE, "NOT-EXISTENT", True),
            TERMINAL_STATE: (None, None, None, False)
        })

        self.assertIsNone(self.db.get_last_state())
        fsm.run()
        transition_action.assert_called_once_with({})
        failure_transition_action.assert_called_once_with(params)
        self.assert_current_FSM_state(TERMINAL_STATE)

    def test_fsm_should_yield_execution_but_be_able_to_proceed_next_time_we_run_it(self):
        params = {"val": 1}
        transition_action = MagicMock(return_value=(True, "", params))
        next_transition_action = MagicMock(return_value=(True, "", {}))
        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, "NEXT", "NOT-EXISTENT", True),
            "NEXT": (next_transition_action, TERMINAL_STATE, "NOT-EXISTENT", False),
            TERMINAL_STATE: (None, None, None, False)
        })

        self.assertIsNone(self.db.get_last_state())
        fsm.run()
        transition_action.assert_called_once_with({})
        next_transition_action.assert_not_called()
        self.assert_current_FSM_state("NEXT")

        fsm.run()
        next_transition_action.assert_called_once_with(params)
        self.assert_current_FSM_state(TERMINAL_STATE)

    def test_state_transition_result_decorator_should_return_false_on_exception(self):
        expected_err_str = "class: [<class 'Exception'>], " \
                           "doc: [Common base class for all non-exit exceptions.], msg: [total fail]"

        fsm = FSM(self.db, {})
        @fsm.with_state_transition_result
        def exception_throwing_function():
            raise Exception("total fail")

        is_successful, err_str, result = exception_throwing_function()

        self.assertFalse(is_successful)
        self.assertEqual(expected_err_str, err_str)
        self.assertEqual({}, result)

    def test_state_transition_result_decorator_should_return_true_on_successful_non_tuple_result(self):
        expected_result = {"smth": 1}

        fsm = FSM(self.db, {})
        @fsm.with_state_transition_result
        def successful_function():
            return expected_result

        is_successful, err_str, result = successful_function()

        self.assertTrue(is_successful)
        self.assertEqual(expected_result, result)
        self.assertIsNone(err_str)

    def test_regular_fsm_run_should_save_all_visited_states_in_history(self):
        params = {"val": 1}
        transition_action = MagicMock(return_value=(True, "", params))
        next_transition_action = MagicMock(return_value=(True, "", {}))
        one_more_transition_action = MagicMock(return_value=(True, "", {}))
        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, "NEXT", "NOT-EXISTENT", True),
            "NEXT": (next_transition_action, "ONE_MORE", "NOT-EXISTENT", True),
            "ONE_MORE": (one_more_transition_action, TERMINAL_STATE, TERMINAL_STATE, True),
            TERMINAL_STATE: (None, None, None, False)
        })

        history_before_run = self.db.get_db_history()
        self.assertFalse(history_before_run)

        fsm.run()

        history_after_run = self.db.get_db_history()
        self.assertTrue(history_after_run)
        self.assertEqual(4, len(history_after_run))
        self.assertListEqual([INITIAL_STATE, "NEXT", "ONE_MORE", TERMINAL_STATE], [x.name for x in history_after_run])
        self.assertListEqual([1, 1, 1, 1], [x.visit_count for x in history_after_run])
        self.assertListEqual([{}, params, {}, {}], [x.params for x in history_after_run])

    def test_multiple_fsm_runs_should_return_correct_current_state(self):
        params = {"val": 1}
        transition_action = MagicMock(return_value=(True, "", params))
        next_transition_action = MagicMock(return_value=(True, "", {}))
        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, "NEXT", "NOT-EXISTENT", True),
            "NEXT": (next_transition_action, TERMINAL_STATE, "NOT-EXISTENT", False),
            TERMINAL_STATE: (None, None, None, False)
        })

        self.assertIsNone(self.db.get_last_state())
        fsm.run()
        transition_action.assert_called_once_with({})
        next_transition_action.assert_not_called()
        self.assert_current_FSM_state("NEXT")

        fsm.run()
        next_transition_action.assert_called_once_with(params)
        self.assert_current_FSM_state(TERMINAL_STATE)

        fsm.run()
        self.assert_current_FSM_state("NEXT")
        fsm.run()
        self.assert_current_FSM_state(TERMINAL_STATE)

        history_after_run = self.db.get_db_history()
        self.assertEqual(6, len(history_after_run))

    def test_fsm_should_terminate_if_max_visits_were_reached(self):
        transition_action = MagicMock(return_value=(True, "", {}))
        next_transition_action = MagicMock(return_value=(True, "", {}))
        another_transition_action = MagicMock(return_value=(True, "", {}))

        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, "LOOP-START", "NOT-EXISTENT", True),
            "LOOP-START": (next_transition_action, "LOOP-END", "NON-EXISTENT", False),
            "LOOP-END": (another_transition_action, "LOOP-START", "NON-EXISTENT", False),
            TERMINAL_STATE: (None, None, None, False)
        })

        self.assertIsNone(self.db.get_last_state())
        fsm.run()
        transition_action.assert_called_once()
        next_transition_action.assert_not_called()
        another_transition_action.assert_not_called()
        self.assert_current_FSM_state("LOOP-START")

        fsm.run()
        next_transition_action.assert_called_once()
        another_transition_action.assert_not_called()
        self.assert_current_FSM_state("LOOP-END")

        fsm.run()
        another_transition_action.assert_not_called()
        self.assert_current_FSM_state(TERMINAL_STATE)

    def test_fsm_should_terminate_if_transition_fails_continuously(self):
        transition_action = MagicMock(return_value=(True, "", {}))
        next_transition_action = MagicMock(return_value=(False, "", {}))

        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, "NEXT", "NOT-EXISTENT", True),
            "NEXT": (next_transition_action, TERMINAL_STATE, "NEXT", False),
            TERMINAL_STATE: (None, None, None, False)
            },
            {DEFAULT: 2}
        )

        self.assertIsNone(self.db.get_last_state())
        fsm.run()
        transition_action.assert_called_once()
        next_transition_action.assert_not_called()
        self.assert_current_FSM_state("NEXT")

        fsm.run()
        next_transition_action.assert_called_once()
        self.assert_current_FSM_state("NEXT")

        fsm.run()
        self.assert_current_FSM_state(TERMINAL_STATE)

    def test_fsm_state_exists(self):
        transition_action = MagicMock(return_value=(True, "", {}))

        fsm = FSM(self.db, {
            INITIAL_STATE: (transition_action, "NEXT", "NOT-EXISTENT", True),
            TERMINAL_STATE: (None, None, None, False)
        })

        self.assertIsNone(self.db.get_last_state())
        self.assertRaises(KeyError, fsm.run)
