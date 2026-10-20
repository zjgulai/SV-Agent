class InvalidRunTransition(Exception):
    code = "RUN_TRANSITION_INVALID"


class InvalidReplicationAxis(Exception):
    code = "REPLICATION_AXIS_INVALID"


class InvalidTaskRevision(Exception):
    code = "TASK_REVISION_INVALID"


class InvalidTaskBrief(Exception):
    code = "TASK_BRIEF_INVALID"


class InvalidRunRevision(Exception):
    code = "RUN_REVISION_INVALID"


class InvalidRunPlan(Exception):
    code = "RUN_PLAN_INVALID"


class TaskNotFound(Exception):
    code = "TASK_NOT_FOUND"


class TaskRevisionConflict(Exception):
    code = "TASK_REVISION_CONFLICT"


class RunRevisionConflict(Exception):
    code = "RUN_REVISION_CONFLICT"


class RunNotFound(Exception):
    code = "RUN_NOT_FOUND"


class ToolRunNotFound(Exception):
    code = "TOOL_RUN_NOT_FOUND"


class ToolRunRevisionConflict(Exception):
    code = "TOOL_RUN_REVISION_CONFLICT"


class IdempotencyConflict(Exception):
    code = "IDEMPOTENCY_CONFLICT"


class EventSchemaUnsupported(Exception):
    code = "EVENT_SCHEMA_UNSUPPORTED"


class EventDigestMismatch(Exception):
    code = "EVENT_DIGEST_MISMATCH"


class JournalIntegrityError(Exception):
    code = "JOURNAL_INTEGRITY_ERROR"
