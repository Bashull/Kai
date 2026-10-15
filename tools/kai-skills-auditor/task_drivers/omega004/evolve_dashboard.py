"""Apply only own additions to an exact, separately supplied private skill tree.

No provider text is distributed with this driver. Output is always a new lab tree.
"""
import argparse
from pathlib import Path
import sys

TOOL_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(TOOL_ROOT))
import build_incremental as inc
import bundle_io as b

BASE_SHA256 = 'd3d3f4a3daf77c5a099e6fc13b7ab6d975688f80a6a927e731dc32e118f705f0'
PORTABLE_ADDITION = (
    '- For a portable or selectively staged copy, follow the [portable runtime check]'
    '(references/portable-runtime.md) before preparation. Keep the provider directory '
    'structure and use its verified local helper paths. A copied `SKILL.md`, successful '
    'extraction, or copied shared policy does not establish that the authoring runtime '
    'or conditional connector workflows are available.\n')
ACCESSIBILITY_ADDITION = (
    'Exercise the primary filter, drill-down, and return/reset path using the keyboard '
    'as well as the pointer; verify meaningful labels and visible focus. Provide an '
    "accessible text or table equivalent for the chart's relevant values and relationships "
    'using the same filtered population, units, missing-value semantics, and source scope. '
    'Record unavailable accessibility checks as unperformed, rather than inferring them '
    'from the build.\n')


def evolve(source, output, reference):
    files = inc.snapshot_directory(source)
    if 'SKILL.md' not in files or b.sha(files['SKILL.md']) != BASE_SHA256:
        raise ValueError('Source must match the exact separately supplied baseline')
    text = files['SKILL.md'].decode('utf-8')
    for anchor in ('\n## Dependencies\n', '\nReconcile the final artifact'):
        if text.count(anchor) != 1:
            raise ValueError('Expected unique insertion anchor is absent')
    text = text.replace('\n## Dependencies\n', PORTABLE_ADDITION + '\n## Dependencies\n')
    text = text.replace('\nReconcile the final artifact', '\n' + ACCESSIBILITY_ADDITION + '\nReconcile the final artifact')
    files['SKILL.md'] = text.encode()
    files['references/portable-runtime.md'] = inc._regular_bytes(reference)
    inc._candidate_header(files['SKILL.md'], 'build-dashboard')
    output = Path(output).absolute()
    for part in (output, *output.parents):
        if part.is_symlink() or getattr(part, 'is_junction', lambda: False)():
            raise ValueError('Output ancestors must not be links')
    if (output.exists() or output.is_relative_to(Path(source).resolve())
            or any(p.lower() in {'.codex', '.agents', '.claude'} for p in output.parts)):
        raise ValueError('Output must be a new isolated lab outside source')
    output.mkdir(parents=True, exist_ok=False)
    for name, data in sorted(files.items()):
        path = output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
    return {name: inc.record(data) for name, data in sorted(files.items())}


if __name__ == '__main__':
    import json
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--reference', type=Path, required=True)
    a = p.parse_args()
    print(json.dumps(evolve(a.source, a.output, a.reference), indent=2))
