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
    tenantId = Column(String(255), nullable=False)  # TODO: define FK
    name = Column(String(255), nullable=False)
    startTime = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    endTime = Column(DateTime, nullable=True)
    params = Column(JSON, nullable=False, default=lambda: {})
    runId = Column(String(255), nullable=False)
    visitCount = Column(Integer, nullable=False, default=1)
    errors = Column(JSON, nullable=False, default=lambda: [])
    yielded = Column(Boolean, nullable=False, default=False)

    def __repr__(self) -> str:
        return "<StateEntry(id='%s', name='%s', runId='%s')>" % (self.id, self.name, self.runId)

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
    tenantId = Column(String(255), nullable=False)  # TODO: define FK
    lastStateId = Column(BigInteger, nullable=False)
    updateTime = Column(DateTime, nullable=False)
    refStateName = Column(String(255), nullable=False)

    def __repr__(self) -> str:
        return "<StateStatus(lastStateId='%s', updateTime='%s', refStateName='%s')>" % (
        self.lastStateId, self.updateTime, self.refStateName)
