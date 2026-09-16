"""Closed state transitions for jobs and immutable attempts."""
from __future__ import annotations

from .errors import LoopFactoryError
from .model import ErrorClass, JobState


TERMINAL_STATES = frozenset({
    JobState.SUCCEEDED,
    JobState.FAILED,
    JobState.QUARANTINED,
    JobState.CANCELLED,
})

ATTEMPT_END_STATES = frozenset({*TERMINAL_STATES, JobState.REQUEUE})

_ALLOWED_TRANSITIONS: dict[JobState, frozenset[JobState]] = {
    JobState.QUEUED: frozenset({JobState.READY, JobState.BLOCKED, JobState.CANCELLED}),
    JobState.BLOCKED: frozenset({JobState.READY, JobState.CANCELLED}),
    JobState.READY: frozenset({JobState.RUNNING, JobState.CANCELLED}),
    JobState.RUNNING: frozenset({
        JobState.VERIFYING, JobState.CHECKPOINTED, JobState.REQUEUE,
        JobState.FAILED, JobState.QUARANTINED, JobState.CANCELLED,
    }),
    JobState.VERIFYING: frozenset({
        JobState.CHECKPOINTED, JobState.REQUEUE, JobState.FAILED,
        JobState.QUARANTINED, JobState.CANCELLED,
    }),
    JobState.CHECKPOINTED: frozenset({
        JobState.RUNNING, JobState.VERIFYING, JobState.SUCCEEDED,
        JobState.REQUEUE, JobState.FAILED, JobState.QUARANTINED, JobState.CANCELLED,
    }),
    JobState.REQUEUE: frozenset({JobState.CANCELLED}),
    JobState.SUCCEEDED: frozenset(),
    JobState.FAILED: frozenset(),
    JobState.QUARANTINED: frozenset(),
    JobState.CANCELLED: frozenset(),
}


def is_terminal(state: JobState) -> bool:
    return JobState(state) in TERMINAL_STATES


def is_attempt_end_state(state: JobState) -> bool:
    return JobState(state) in ATTEMPT_END_STATES


def assert_transition(current: JobState, target: JobState) -> None:
    current = JobState(current)
    target = JobState(target)
    if target not in _ALLOWED_TRANSITIONS[current]:
        raise LoopFactoryError(
            ErrorClass.UNKNOWN,
            f"Illegal state transition {current.value} -> {target.value}",
            retryable=False,
        )


def initial_state_for_new_attempt() -> JobState:
    return JobState.READY
