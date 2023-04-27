from datetime import datetime
from sqlalchemy import (Column, Integer, BigInteger, String, Boolean, DateTime)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from fsm import TERMINAL_STATE, INITIAL_STATE

Base = declarative_base()


class StateError(dict):
    def __init__(self, error: str, visit_idx: int) -> None:
        dict.__init__(self, error=error, visit_idx=visit_idx)


class StateEntry(Base):
    __tablename__ = 'state_entry'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    tenant_id = Column(String(255), nullable=False)  # TODO: define FK
    name = Column(String(255), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    params = Column(JSON, nullable=False, default=lambda: {})
    run_id = Column(String(255), nullable=False)
    visit_count = Column(Integer, nullable=False, default=1)
    errors = Column(JSON, nullable=False, default=lambda: [])
    yielded = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return "<StateEntry(id='%s', name='%s', run_id='%s')>" % (self.id, self.name, self.run_id)

    def is_initial(self) -> bool:
        return self.name == INITIAL_STATE

    def is_terminal(self) -> bool:
        return self.name == TERMINAL_STATE

    def append_error(self, state_error: StateError) -> None:
        errors_clone = self.errors[:]
        errors_clone.append(state_error)
        self.errors = errors_clone


class StateStatus(Base):
    __tablename__ = 'state_status'

    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(String(255), nullable=False)  # TODO: define FK
    last_state_id = Column(BigInteger, nullable=False)
    update_time = Column(DateTime, nullable=False)
    ref_state_name = Column(String(255), nullable=False)

    def __repr__(self) -> str:
        return "<StateStatus(last_state_id='%s', update_time='%s', ref_state_name='%s')>" % (
            self.last_state_id, self.update_time, self.ref_state_name)
