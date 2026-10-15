"""Read a fixed historical skill census, preserving each occurrence and byte object.

Own offline collector; never executes captured content, installs dependencies,
follows source links, edits originals, or copies detected credential material.
"""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
import zipfile

LIMIT = 8*1024*1024
TOKEN = re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,}\b|\bgithub_pat_[A-Za-z0-9_]{40,}\b|\bhf_[A-Za-z0-9]{30,}\b|\bsk-(?:proj-)?[A-Za-z0-9_-]{40,}\b|\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\b')
PEM = re.compile(rb'-----BEGIN (?:[A-Z]+ )?PRIVATE KEY-----[\r\n]+[A-Za-z0-9+/=\r\n]{48,}-----END (?:[A-Z]+ )?PRIVATE KEY-----')


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_regular(path, limit=LIMIT):
    path = Path(path)
    for ancestor in (path, *path.parents):
        if ancestor.is_symlink() or getattr(ancestor, 'is_junction', lambda:False)():
            raise ValueError('Source link/junction rejected')
    before = path.stat()
    if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
        raise ValueError('Source must be a bounded regular file')
    with path.open('rb') as f:
        opened = os.fstat(f.fileno())
        if (opened.st_dev,opened.st_ino)!=(before.st_dev,before.st_ino):
            raise ValueError('Source changed while opening')
        data=f.read(limit+1)
        after=os.fstat(f.fileno())
    if len(data)>limit or (opened.st_size,opened.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):
        raise ValueError('Source changed while reading')
    return data


def write_new(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if path.read_bytes()!=data:
            raise ValueError('Content-addressed object collision')
        return
    with path.open('xb') as f:
        f.write(data)


def json_bytes(data):
    return (json.dumps(data,ensure_ascii=False,indent=2)+'\n').encode('utf8')


def within(path, roots):
    return '..' not in path.parts and any(path.is_relative_to(root) for root in roots)


def check_stop(stop):
    if stop and Path(stop).exists():
        raise RuntimeError('STOP requested; sources unchanged, incomplete capture retained')


def credential_in_json(value):
    pending=[value]
    while pending:
        item=pending.pop()
        if isinstance(item,str) and (TOKEN.search(item.encode()) or PEM.search(item.encode())):
            return True
        if isinstance(item,dict):pending.extend(item.keys());pending.extend(item.values())
        elif isinstance(item,list):pending.extend(item)
    return False


def capture(census, output, source, expected_count, stop=None):
    if source not in ('pc-asier','termux') or type(expected_count) is not int or expected_count<1:
        raise ValueError('Explicit source and positive count required')
    output=Path(output).absolute()
    for ancestor in (output,*output.parents):
        if ancestor.is_symlink() or getattr(ancestor,'is_junction',lambda:False)():
            raise ValueError('Output links/junctions rejected')
    if any(p.lower() in ('.agents','.codex','.claude') for p in output.parts):
        raise ValueError('Output must not be an active skills root')
    for p in (output,output.with_name(output.name+'.zip'),
              output.with_name(output.name+'.transport.b64'),output.with_name(output.name+'.receipt.json')):
        if p.exists() or p.is_symlink():
            raise ValueError('All capture output paths must be new')
    check_stop(stop)
    census_data=read_regular(census)
    previous=json.loads(census_data)
    if credential_in_json(previous):
        raise ValueError('Census contains credential patterns; values withheld, no export')
    rows=previous['skills']
    if len(rows)!=expected_count or len({r['path'] for r in rows})!=expected_count:
        raise ValueError('Input census count or unique paths mismatch')
    root_values=previous['roots']
    roots=[Path(x['path'] if isinstance(x,dict) else x).absolute() for x in root_values]
    if any('..' in root.parts for root in roots):
        raise ValueError('Census root traversal rejected')
    def guarded_write(path,data):
        check_stop(stop)
        write_new(path,data)
        check_stop(stop)
    output.mkdir(parents=True)
    guarded_write(output/'SOURCE_CENSUS.json',census_data)
    results=[]; metadata=[]; seen_metadata=set(); bytes_read=0
    for i,old in enumerate(rows,1):
        check_stop(stop)
        path=Path(old['path']).absolute()
        uid='occ:'+source+':'+digest(str(path).replace('\\','/').encode())[:24]
        row={'index':i,'occurrence_id':source+':'+str(i).zfill(4),'occurrence_uid':uid,
             'path':old['path'],'expected_sha256':old['sha256'],'expected_bytes':old['bytes'],
             'state':'BLOCKED','resources':'NOT_CAPTURED_BY_INITIAL_MD_SNAPSHOT'}
        try:
            if path.name.lower()!='skill.md' or not within(path,roots):
                raise ValueError('Source is outside census roots or not SKILL.md')
            data=read_regular(path)
            sha=digest(data);bytes_read+=len(data)
            row.update(sha256=sha,bytes=len(data),matches_census=sha==old['sha256'])
            if TOKEN.search(data) or PEM.search(data):
                row.update(state='BLOCKED',error='CREDENTIAL_PATTERN_REQUIRES_REVIEW; values not copied',
                           credential_material_exported=False)
            else:
                obj='objects/'+sha+'/SKILL.md'
                guarded_write(output/obj,data)
                row.update(object_path=obj,state='CAPTURED' if sha==old['sha256'] else 'CHANGED_SINCE_CENSUS')
            # Only bounded, explicitly named provenance/licence files, not .env,
            # keys, auth files, repository config or arbitrary sibling content.
            for ancestor in list(path.parent.parents)[:3]+[path.parent]:
                if not within(ancestor,roots):
                    continue
                for name in ('LICENSE','LICENSE.md','LICENSE.txt','COPYING','package.json',
                             '.claude-plugin/plugin.json','.codex-plugin/plugin.json'):
                    check_stop(stop)
                    hint=ancestor/name
                    if str(hint) in seen_metadata or not hint.is_file():
                        continue
                    seen_metadata.add(str(hint))
                    rec={'path':str(hint),'kind':'PROVENANCE_CLUE_NOT_PROVIDER_AUTHENTICATION'}
                    try:
                        raw=read_regular(hint,256*1024);sha_hint=digest(raw)
                        rec.update(bytes=len(raw),sha256=sha_hint)
                        if TOKEN.search(raw) or PEM.search(raw):
                            rec['state']='BLOCKED_CREDENTIAL_PATTERN'
                        else:
                            obj='metadata_objects/'+sha_hint
                            guarded_write(output/obj,raw);rec.update(state='CAPTURED',object_path=obj)
                    except Exception as e:
                        rec.update(state='BLOCKED',error=type(e).__name__+': '+str(e))
                    metadata.append(rec)
        except Exception as e:
            row.update(state='BLOCKED',error=type(e).__name__+': '+str(e))
        results.append(row)
    counts={state:sum(r['state']==state for r in results) for state in ('CAPTURED','CHANGED_SINCE_CENSUS','BLOCKED')}
    manifest={'format':'kai.skill_capture/1','source':source,'utc':dt.datetime.now(dt.timezone.utc).isoformat(),
        'scope':'Exact historical census paths; no new broad scan and no source modification',
        'census_sha256':digest(census_data),'expected_count':expected_count,'rows':results,
        'metadata_clues':metadata,'counts':counts,'bytes_read':bytes_read,
        'unique_captured_objects':len({r['sha256'] for r in results if 'object_path' in r}),
        'runtime':{'python':sys.version,'platform':sys.platform},
        'resources_scope':'SKILL.md and bounded named metadata only; auxiliary code not yet captured or functionally understood',
        'provider_code_executed':False,'active_installation':False}
    check_stop(stop)
    guarded_write(output/'CAPTURE_MANIFEST.json',json_bytes(manifest))
    all_files={p.relative_to(output).as_posix():p for p in output.rglob('*') if p.is_file()}
    hashed={}
    for n,p in sorted(all_files.items()):
        check_stop(stop);hashed[n]={'sha256':digest(p.read_bytes()),'bytes':p.stat().st_size}
    integrity={'format':'kai.capture.integrity/1','files':hashed}
    guarded_write(output/'CAPTURE_INTEGRITY.json',json_bytes(integrity))
    archive=output.with_name(output.name+'.zip')
    check_stop(stop)
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in sorted(output.rglob('*')):
            check_stop(stop)
            if p.is_file():
                info=zipfile.ZipInfo(p.relative_to(output).as_posix(),date_time=(2026,10,15,0,0,0))
                info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(archive) as z:
        for n,rec in integrity['files'].items():
            check_stop(stop)
            data=z.read(n)
            if len(data)!=rec['bytes'] or digest(data)!=rec['sha256']:
                raise ValueError('Capture ZIP payload mismatch')
    check_stop(stop)
    raw=archive.read_bytes();encoded=base64.b64encode(raw).decode('ascii')
    transport=output.with_name(output.name+'.transport.b64')
    guarded_write(transport,('\n'.join(encoded[i:i+1024] for i in range(0,len(encoded),1024))+'\n').encode('ascii'))
    receipt={'source':source,'rows':len(results),'counts':counts,'objects':manifest['unique_captured_objects'],
        'zip':str(archive),'bytes':len(raw),'sha256':digest(raw),'CRC':'PASS',
        'transport_path':str(transport),'transport_lines':(len(encoded)+1023)//1024,
        'metadata_clues':len(metadata),'source_modified':False,'code_executed':'OWN_COLLECTOR_ONLY'}
    guarded_write(output.with_name(output.name+'.receipt.json'),json_bytes(receipt))
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--census',required=True);p.add_argument('--output',required=True)
    p.add_argument('--source',required=True);p.add_argument('--expected-count',type=int,required=True)
    p.add_argument('--stop-file')
    a=p.parse_args()
    print(json.dumps(capture(a.census,a.output,a.source,a.expected_count,a.stop_file)))


if __name__=='__main__':
    main()
