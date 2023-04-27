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
    start_time = DateTimeField(required=True)
    end_time = DateTimeField(required=True)
    params = DictField(required=False, default={})
    run_id = ObjectIdField(required=True, default=ObjectId) # ??? remove default
    visit_count = IntField(required=True, default=1)
    errors = EmbeddedDocumentListField(StateError, default=[])
    yielded = BooleanField(required=True, default=False)

    def is_initial(self) -> bool:
        return self.name == INITIAL_STATE

    def is_terminal(self) -> bool:
        return self.name == TERMINAL_STATE


class StateStatus(Document):
    meta = {'collection': 'fsm_status'}

    last_state_id = ObjectIdField(required=True)
    update_time = DateTimeField(required=True)
    ref_state_name = StringField(required=True)
