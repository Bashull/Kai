"""Pure sanitisation kernel for Windows GUI observations.

No screenshots, user text, file paths, window titles, handles or PIDs in output.
This module is fully testable without Windows or network access.
"""
from __future__ import annotations
from collections import Counter
from typing import Any, Iterable, Mapping

MAX_WINDOWS = 64
# Positive allowlist: do not reveal names of arbitrary open processes.
APP_LABELS = {
    'notepad.exe': 'Notepad',
    'devenv.exe': 'Visual Studio',
    'code.exe': 'VS Code',
    'studio64.exe': 'Android Studio',
    'antigravity.exe': 'Antigravity',
    'powershell.exe': 'PowerShell',
    'pwsh.exe': 'PowerShell',
    'windowsterminal.exe': 'Windows Terminal',
    'ubuntu.exe': 'Ubuntu',
    'ollama app.exe': 'Ollama',
}

class ObservationError(ValueError):
    pass

def _safe_dimension(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ObservationError('INVALID_DIMENSION')
    return min(max(0, value), 16384)

def make_catalog(rows: Iterable[Mapping[str, Any]], *, foreground_pid: int | None,
                 screen_size: tuple[int, int], interactive: bool, truncated: bool = False) -> dict:
    if not isinstance(interactive, bool):
        raise ObservationError('INVALID_SESSION_STATE')
    if not isinstance(screen_size, tuple) or len(screen_size) != 2:
        raise ObservationError('INVALID_DISPLAY')
    width, height = map(_safe_dimension, screen_size)
    if width == 0 or height == 0:
        raise ObservationError('NO_DISPLAY')
    count = 0
    tracked = Counter()
    foreground = 'unknown_or_other'
    overflow = False
    for row in rows:
        if not isinstance(row, Mapping):
            raise ObservationError('INVALID_WINDOW')
        if not (row.get('visible') is True and row.get('titled') is True):
            continue
        if count >= MAX_WINDOWS:
            overflow = True
            break
        count += 1
        exe = row.get('exe')
        if not isinstance(exe, str):
            exe = ''
        label = APP_LABELS.get(exe.casefold())
        if label:
            tracked[label] += 1
        if foreground_pid is not None and row.get('pid') == foreground_pid:
            foreground = label or 'unknown_or_other'
    return {
        'schema': 'kai.gui.catalog/1',
        'visible_window_count': count,
        'tracked_applications': [{'app': name, 'windows': tracked[name]} for name in sorted(tracked)],
        'foreground_app': foreground,
        'screen': {'width': width, 'height': height},
        'interactive_console_session': interactive,
        'truncated': bool(truncated or overflow),
        'privacy': {
            'window_titles': 'redacted', 'window_text': 'redacted',
            'process_ids': 'redacted', 'handles': 'redacted',
            'paths': 'redacted', 'pixels': 'not_collected',
        },
    }


def validate_catalog(data: Any) -> dict:
    """Reject malformed/unredacted adapter data before publishing in a receipt."""
    if not isinstance(data, dict) or set(data) != {
        'schema','visible_window_count','tracked_applications','foreground_app','screen',
        'interactive_console_session','truncated','privacy'}:
        raise ObservationError('CATALOG_SCHEMA_MISMATCH')
    if data['schema'] != 'kai.gui.catalog/1':
        raise ObservationError('UNKNOWN_SCHEMA')
    if not isinstance(data['visible_window_count'], int) or isinstance(data['visible_window_count'], bool) or not 0 <= data['visible_window_count'] <= MAX_WINDOWS:
        raise ObservationError('INVALID_WINDOW_COUNT')
    apps = data['tracked_applications']
    if not isinstance(apps, list) or len(apps) > len(set(APP_LABELS.values())):
        raise ObservationError('INVALID_APPS')
    allow = set(APP_LABELS.values())
    seen = set()
    for app in apps:
        if not isinstance(app, dict) or set(app) != {'app','windows'} or app['app'] not in allow or app['app'] in seen:
            raise ObservationError('INVALID_APP_ENTRY')
        if type(app['windows']) is not int or not 1 <= app['windows'] <= MAX_WINDOWS:
            raise ObservationError('INVALID_APP_COUNT')
        seen.add(app['app'])
    if data['foreground_app'] not in allow | {'unknown_or_other'}:
        raise ObservationError('INVALID_FOREGROUND')
    screen = data['screen']
    if not isinstance(screen, dict) or set(screen) != {'width','height'}:
        raise ObservationError('INVALID_SCREEN')
    for dim in ('width','height'):
        if type(screen[dim]) is not int or not 1 <= screen[dim] <= 16384:
            raise ObservationError('INVALID_SCREEN_SIZE')
    if type(data['interactive_console_session']) is not bool or type(data['truncated']) is not bool:
        raise ObservationError('INVALID_FLAGS')
    if data['privacy'] != {
        'window_titles': 'redacted', 'window_text': 'redacted',
        'process_ids': 'redacted', 'handles': 'redacted',
        'paths': 'redacted', 'pixels': 'not_collected'}:
        raise ObservationError('PRIVACY_INVARIANT_FAILED')
    return data