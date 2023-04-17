from bson import ObjectId
from mongoengine import EmbeddedDocument, StringField, IntField, Document, DateTimeField, DictField, ObjectIdField, \
    EmbeddedDocumentListField, BooleanField

from fsm import TERMINAL_STATE, INITIAL_STATE


class StateError(EmbeddedDocument):
    error = StringField(required=True)
    visitIdx = IntField(required=True)


class StateEntry(Document):
    meta = {'collection': 'fsm_log'} #,
            #'indexes': ['modelInfo.version']}

    name = StringField(required=True)
    startTime = DateTimeField(required=True)
    endTime = DateTimeField(required=True)
    params = DictField(required=False, default={})
    runId = ObjectIdField(required=True, default=ObjectId) # ??? remove default
    visitCount = IntField(required=True, default=1)
    errors = EmbeddedDocumentListField(StateError, default=[])
    yielded = BooleanField(required=True, default=False)

    def is_initial(self) -> bool:
        return self.name == INITIAL_STATE

    def is_terminal(self) -> bool:
        return self.name == TERMINAL_STATE


class StateStatus(Document):
    meta = {'collection': 'fsm_status'}

    lastStateId = ObjectIdField(required=True)
    updateTime = DateTimeField(required=True)
    refStateName = StringField(required=True)
