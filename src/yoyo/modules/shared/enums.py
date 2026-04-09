from enum import StrEnum


class QuestionnaireSubmissionStatus(StrEnum):
    SUBMITTED = "submitted"
    PROCESSED = "processed"


class ItineraryStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"


class ItineraryVersionStatus(StrEnum):
    DRAFT = "draft"
    ACTIVE = "active"
    ARCHIVED = "archived"


class GuideGenerationJobType(StrEnum):
    GUIDE_BUNDLE = "guide_bundle"


class GuideGenerationJobStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AssetStatus(StrEnum):
    MISSING = "missing"
    PENDING = "pending"
    READY = "ready"
    FAILED = "failed"
    STALE = "stale"


class GuideSessionStatus(StrEnum):
    ACTIVE = "active"
    FINISHED = "finished"


class GuidePlaybackState(StrEnum):
    NOT_TRIGGERED = "not_triggered"
    TRIGGERED = "triggered"
    PLAYING = "playing"
    PLAYED = "played"
    SKIPPED = "skipped"


class QAMessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class QAMessageValidationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
