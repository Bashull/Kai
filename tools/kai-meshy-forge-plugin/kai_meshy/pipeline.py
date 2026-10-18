"""Bounded recovery tick. Paid submissions always remain explicit tool calls."""
from .core import ForgeError


def cycle(forge, job_id, timeout=60):
    if not isinstance(timeout, (int, float)) or isinstance(timeout, bool) or not 0 < timeout <= 3600:
        raise ForgeError('INVALID_CYCLE_TIMEOUT')
    state = forge.get_job(job_id)
    if state['job']['rejected']:
        return {'next_action': 'REJECTED_REQUIRES_NEW_REFERENCE', 'job_id': job_id}
    if state['job']['local_cancelled']:
        return {'next_action': 'LOCALLY_CANCELLED_REMOTE_UNCHANGED', 'job_id': job_id}
    if (state['job'].get('workflow_kind', 'brick') != 'brick'
            or any(s['stage'].startswith('op:') for s in state['stages'])):
        return {'next_action': 'USE_CAPABILITY_OPERATION_LOOP', 'job_id': job_id,
                'paid_submission_performed': False}
    stages = {s['stage']: s for s in state['stages']}
    if 'prototype' not in stages:
        return {'next_action': 'SUBMIT_PROTOTYPE', 'estimated_credits': 6, 'paid_submission_performed': False}
    prototype = stages['prototype']
    if prototype['status'] == 'SUBMISSION_UNKNOWN':
        return {'next_action': 'RECONCILE_PROTOTYPE', 'never_repeat_post': True}
    if prototype['status'] in ('PENDING', 'IN_PROGRESS'):
        prototype = forge.wait(job_id, 'prototype', timeout=timeout)
    if prototype['status'] != 'SUCCEEDED':
        return {'next_action': 'REVIEW_PROTOTYPE', 'stage': prototype}
    # Always recover the preview, including when resumed after SUCCEEDED.
    preview = forge.download(job_id, 'prototype', 'preview')
    if not state['job']['preview_approved']:
        return {'next_action': 'HUMAN_VISUAL_QA', 'preview': preview, 'paid_submission_performed': False}
    if 'build' not in stages:
        return {'next_action': 'SUBMIT_BUILD', 'estimated_credits': 30, 'paid_submission_performed': False}
    build = stages['build']
    if build['status'] == 'SUBMISSION_UNKNOWN':
        return {'next_action': 'RECONCILE_BUILD', 'never_repeat_post': True}
    if build['status'] in ('PENDING', 'IN_PROGRESS'):
        build = forge.wait(job_id, 'build', timeout=timeout)
    if build['status'] != 'SUCCEEDED':
        return {'next_action': 'REVIEW_BUILD', 'stage': build}
    model = forge.download(job_id, 'build', 'glb')
    return {'next_action': 'OFFLINE_ASSET_QA', 'model': model, 'paid_submission_performed': False}
