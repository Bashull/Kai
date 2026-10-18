"""One bounded observation/recovery pass over the existing operation ledger.

This loop never submits work or chooses a visual design. Calling it requires the
transport's write scope because remote status observations produce audit events.
The caller chooses whether to download an output; failures never regenerate it.
"""
from __future__ import annotations

import time

from .core import ForgeError


def cycle_operations(engine, job_id, *, timeout=20, max_operations=20):
    if (isinstance(timeout, bool) or not isinstance(timeout, (int, float))
            or not 0 < timeout <= 30):
        raise ForgeError('INVALID_OPERATION_LOOP_TIMEOUT')
    if isinstance(max_operations, bool) or not isinstance(max_operations, int) or not 1 <= max_operations <= 50:
        raise ForgeError('INVALID_OPERATION_LOOP_LIMIT')
    job = engine.forge.get_job(job_id)['job']
    if job['rejected']:
        return {'next_action': 'REJECTED_REQUIRES_NEW_REFERENCE', 'paid_submission_performed': False}
    if job['local_cancelled']:
        return {'next_action': 'LOCALLY_CANCELLED_REMOTE_UNCHANGED', 'paid_submission_performed': False}
    operations = engine.list_operations(job_id)
    end = time.monotonic() + timeout
    results = []
    for operation in operations[:max_operations]:
        if time.monotonic() >= end:
            break
        operation_id = operation['operation_id']
        status = operation['status']
        action = 'REVIEW_OPERATION'
        error = None
        if status == 'PLANNED':
            action = 'EXPLICIT_AUTHORIZED_SUBMIT_REQUIRED'
        elif status == 'SUBMISSION_UNKNOWN':
            action = 'RECONCILE_ORIGINAL_REQUEST_NEVER_REPEAT_POST'
        elif status in ('PENDING', 'IN_PROGRESS'):
            try:
                state = engine.refresh_operation(job_id, operation_id,
                                                 timeout=max(0.1, end - time.monotonic()))
                status = state['status']
                action = 'RECOVER_EXISTING_OUTPUT' if status == 'SUCCEEDED' else 'OBSERVE_EXISTING_TASK'
            except ForgeError as exc:
                # Preserve original task and reservation on transport failure.
                action = 'RETRY_READ_ONLY_OBSERVATION'
                error = str(exc)
        elif status == 'SUCCEEDED':
            action = 'RECOVER_EXISTING_OUTPUT'
        elif status in ('FAILED', 'CANCELED'):
            action = 'REVIEW_TERMINAL_RESULT_NO_AUTO_RETRY'
        entry = {'operation_id': operation_id, 'status': status, 'next_action': action}
        if error:
            entry['error'] = error
        results.append(entry)
    return {'job_id': job_id, 'operations': results,
            'observed': len(results), 'remaining': len(operations) - len(results),
            'next_action': 'REVIEW_OPERATION_GATES', 'paid_submission_performed': False,
            'max_attempts_per_operation': 1}
