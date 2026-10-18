"""Bounded structural inspection; never claims geometric or printing approval."""
import json
import math
from pathlib import Path
import struct
from .core import ForgeError, digest

MAX_FILE_BYTES = 1024 * 1024 * 1024
MAX_JSON_BYTES = 20 * 1024 * 1024


def _glb(path, size):
    with path.open('rb') as f:
        header = f.read(12)
        if len(header) != 12:
            raise ForgeError('GLB_HEADER_TRUNCATED')
        magic, version, length = struct.unpack('<4sII', header)
        if magic != b'glTF' or version != 2 or length != size:
            raise ForgeError('GLB_HEADER_INVALID')
        chunks = []; meta = None; bin_bytes = 0
        while f.tell() < length:
            offset = f.tell()
            raw = f.read(8)
            if len(raw) != 8:
                raise ForgeError('GLB_CHUNK_HEADER_TRUNCATED')
            count, kind = struct.unpack('<II', raw)
            if count % 4 or f.tell() + count > length:
                raise ForgeError('GLB_CHUNK_BOUNDS_INVALID')
            if not chunks and kind != 0x4E4F534A:
                raise ForgeError('GLB_JSON_MUST_BE_FIRST')
            if kind == 0x4E4F534A:
                if meta is not None or count > MAX_JSON_BYTES:
                    raise ForgeError('GLB_JSON_COUNT_OR_SIZE_INVALID')
                try:
                    meta = json.loads(f.read(count).decode('utf8').rstrip(' \t\r\n\x00'))
                except (ValueError, UnicodeError):
                    raise ForgeError('GLB_JSON_INVALID') from None
                if not isinstance(meta, dict) or meta.get('asset', {}).get('version') != '2.0':
                    raise ForgeError('GLB_ASSET_VERSION_INVALID')
            else:
                if kind == 0x004E4942:
                    if bin_bytes:
                        raise ForgeError('GLB_MULTIPLE_BINARY_CHUNKS')
                    bin_bytes = count
                f.seek(count, 1)
            chunks.append({'offset': offset, 'length': count, 'kind': hex(kind)})
        if meta is None or f.tell() != length:
            raise ForgeError('GLB_JSON_MISSING_OR_LENGTH_INVALID')
    buffers = meta.get('buffers', [])
    views = meta.get('bufferViews', [])
    if not isinstance(buffers, list) or not isinstance(views, list):
        raise ForgeError('GLB_BUFFER_METADATA_INVALID')
    for index, buffer in enumerate(buffers):
        count = buffer.get('byteLength')
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            raise ForgeError('GLB_BUFFER_SIZE_INVALID')
        if 'uri' not in buffer and (index != 0 or count > bin_bytes or bin_bytes - count > 3):
            raise ForgeError('GLB_EMBEDDED_BUFFER_SIZE_MISMATCH')
    for view in views:
        index = view.get('buffer'); count = view.get('byteLength'); offset = view.get('byteOffset', 0)
        if any(isinstance(x, bool) or not isinstance(x, int) or x < 0 for x in (index, count, offset)):
            raise ForgeError('GLB_BUFFER_VIEW_INVALID')
        if index >= len(buffers) or offset + count > buffers[index]['byteLength']:
            raise ForgeError('GLB_BUFFER_VIEW_OUT_OF_BOUNDS')
    def count(key):
        value = meta.get(key, [])
        if not isinstance(value, list):
            raise ForgeError('GLB_ARRAY_METADATA_INVALID')
        return len(value)
    return {'format': 'GLB', 'version': version, 'chunks': chunks, 'scenes': count('scenes'),
            'meshes': count('meshes'), 'materials': count('materials'), 'animations': count('animations'),
            'skin_count': count('skins'), 'external_buffers': sum('uri' in b for b in buffers)}


def _obj(path):
    vertices = faces = 0; max_index = 0; min_negative = 0
    with path.open('r', encoding='utf8', errors='strict') as f:
        for line in f:
            if len(line) > 1024 * 1024:
                raise ForgeError('OBJ_LINE_TOO_LONG')
            words = line.split()
            if not words or words[0].startswith('#'):
                continue
            if words[0] == 'v':
                try:
                    xyz = [float(v) for v in words[1:4]]
                except ValueError:
                    raise ForgeError('OBJ_VERTEX_INVALID') from None
                if len(xyz) != 3 or not all(math.isfinite(x) for x in xyz):
                    raise ForgeError('OBJ_VERTEX_INVALID')
                vertices += 1
            elif words[0] == 'f':
                if len(words) < 4:
                    raise ForgeError('OBJ_FACE_INVALID')
                try:
                    indices = [int(item.split('/')[0]) for item in words[1:]]
                except ValueError:
                    raise ForgeError('OBJ_INDEX_INVALID') from None
                if 0 in indices or any(x < -vertices for x in indices):
                    raise ForgeError('OBJ_INDEX_OUT_OF_BOUNDS')
                max_index = max(max_index, *indices); min_negative = min(min_negative, *indices)
                faces += 1
    if max_index > vertices:
        raise ForgeError('OBJ_INDEX_OUT_OF_BOUNDS')
    return {'format': 'OBJ', 'vertices': vertices, 'faces': faces}


def inspect_model(path, format_hint=None):
    p = Path(path).expanduser().resolve(strict=True)
    if not p.is_file() or p.stat().st_size > MAX_FILE_BYTES:
        raise ForgeError('MODEL_FILE_INVALID_OR_TOO_LARGE')
    size = p.stat().st_size
    result = {'name': p.name, 'bytes': size, 'sha256': digest(p),
              'scope': 'FILE_STRUCTURE_ONLY', 'mesh_qa_verified': False, 'printability_verified': False}
    if format_hint is not None and format_hint not in {'glb', 'obj', 'fbx'}:
        raise ForgeError('INVALID_STRUCTURE_FORMAT_HINT')
    suffix = '.' + format_hint if format_hint else p.suffix.lower()
    if suffix == '.glb':
        result.update(_glb(p, size))
    elif suffix == '.obj':
        try:
            result.update(_obj(p))
        except UnicodeError:
            raise ForgeError('OBJ_TEXT_ENCODING_INVALID') from None
    elif suffix == '.fbx':
        with p.open('rb') as f:
            header = f.read(27)
        if header.startswith(b'Kaydara FBX Binary'):
            if len(header) != 27:
                raise ForgeError('FBX_HEADER_TRUNCATED')
            result.update(format='FBX_BINARY', fbx_version=struct.unpack_from('<I', header, 23)[0])
        elif header.lstrip().startswith(b'; FBX'):
            result.update(format='FBX_ASCII', fbx_version=None)
        else:
            raise ForgeError('FBX_SIGNATURE_INVALID')
    else:
        raise ForgeError('SUPPORTED_STRUCTURE_FORMATS_GLB_OBJ_FBX')
    return result
