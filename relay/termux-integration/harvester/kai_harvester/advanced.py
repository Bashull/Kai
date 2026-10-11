"""Offline diagnostic, search and reconciliation extensions; no network access."""
import hashlib
import json
import os
import platform
import shutil
import sqlite3
import sys
from pathlib import Path
from .dag import message_text

CAPABILITIES = ('python','node','git','unzip','curl','restic','rclone','termux-notification',
                'termux-job-scheduler','termux-wake-lock','termux-storage-get','ssh','proot-distro')

def doctor():
    flags = {x: bool(shutil.which(x)) for x in CAPABILITIES}
    with sqlite3.connect(':memory:') as db:
        try:
            db.execute('CREATE VIRTUAL TABLE t USING fts5(s)')
            fts = True
        except sqlite3.OperationalError:
            fts = False
    return {'platform':platform.system(),'machine':platform.machine(),
            'python':platform.python_version(),'termux':sys.platform in ('linux','android') and Path('/data/data/com.termux/files/usr/bin').exists(),
            'fts5_available':fts,'commands_present':flags,
            'termux_api_app_verified':False,
            'message':'CLI presence does not establish Android app permissions or API health.'}

def _items(store, skip=None):
    skip=skip or set()
    # All graph nodes, including regenerations, not only current_node route.
    for cid, digest, title in store.db.execute('SELECT DISTINCT provider_id,raw_sha256,title FROM conversations'):
        if digest in skip: continue
        raw=store.read_blob(digest)
        if hashlib.sha256(raw).hexdigest()!=digest:
            raise ValueError('CORRUPT_RAW_'+digest[:12])
        convo=json.loads(raw)
        mapping=convo.get('mapping')
        if isinstance(mapping,dict):
            for nid,node in mapping.items():
                if isinstance(node,dict):
                    msg=node.get('message')
                    if isinstance(msg,dict):
                        text=message_text(msg)
                        if text:
                            yield cid,digest,title,str(nid),str((msg.get('author') if isinstance(msg.get('author'),dict) else {}).get('role') or 'unknown'),text
        else:
            # list-form response is not a proven complete conversation graph.
            messages=convo.get('messages')
            if isinstance(messages,list):
                for idx,msg in enumerate(messages):
                    if isinstance(msg,dict):
                        text=message_text(msg)
                        if text: yield cid,digest,title,str(msg.get('id') or idx),str((msg.get('author') if isinstance(msg.get('author'),dict) else {}).get('role') or 'unknown'),text

def index_messages(store):
    if not doctor()['fts5_available']:
        return {'fts5':False,'indexed':0,'reason':'FTS5 missing; search uses slower fallback'}
    db=store.db
    db.execute('CREATE VIRTUAL TABLE IF NOT EXISTS kai_fts USING fts5(provider_id UNINDEXED,raw_sha256 UNINDEXED,title,node_id UNINDEXED,role UNINDEXED,body)')
    db.execute('CREATE TABLE IF NOT EXISTS kai_fts_indexed (raw_sha256 TEXT PRIMARY KEY)')
    db.commit()
    db.execute('BEGIN IMMEDIATE')
    db.execute('CREATE TABLE IF NOT EXISTS kai_fts_version (version INTEGER PRIMARY KEY)')
    if not db.execute('SELECT 1 FROM kai_fts_version WHERE version=2').fetchone():
        db.execute('DELETE FROM kai_fts');db.execute('DELETE FROM kai_fts_indexed');db.execute('INSERT INTO kai_fts_version VALUES(2)')
    done={x[0] for x in db.execute('SELECT raw_sha256 FROM kai_fts_indexed')}
    count=0
    new_revs={row[0] for row in db.execute('SELECT DISTINCT raw_sha256 FROM conversations') if row[0] not in done}
    with db:
        for cid,digest,title,nodeid,role,body in _items(store,skip=done):
            db.execute('INSERT INTO kai_fts(provider_id,raw_sha256,title,node_id,role,body) VALUES (?,?,?,?,?,?)',
                       (cid,digest,str(title or ''),nodeid,role,body))
            count+=1
        # Commit only after indexing all messages, including empty-message revisions.
        for digest in new_revs:
            db.execute('INSERT OR IGNORE INTO kai_fts_indexed(raw_sha256) VALUES (?)',(digest,))
    return {'fts5':True,'messages_newly_indexed':count,'indexed_revisions':db.execute('SELECT COUNT(*) FROM kai_fts_indexed').fetchone()[0]}

def search_messages(store, query, limit=20):
    if not isinstance(query,str) or not query.strip() or len(query)>256: raise ValueError('QUERY_INVALID')
    if not isinstance(limit,int) or limit<1 or limit>100: raise ValueError('LIMIT_INVALID')
    indexed=index_messages(store)
    if indexed['fts5']:
        # Treat the user's search as a literal phrase, not arbitrary FTS syntax.
        phrase='"'+query.strip().replace('"','""')+'"'
        rows=store.db.execute('SELECT provider_id,raw_sha256,title,node_id,role,substr(body,1,600) FROM kai_fts WHERE kai_fts MATCH ? LIMIT ?', (phrase,limit)).fetchall()
    else:
        needle=query.casefold();rows=[]
        for cid,digest,title,nodeid,role,body in _items(store):
            if needle in (str(title)+' '+body).casefold():
                rows.append((cid,digest,title,nodeid,role,body[:600]))
                if len(rows)>=limit: break
    return {'scope':'LOCAL_IMPORTED_RECORDS_ONLY','query':query,'returned':len(rows),
            'fts5_used':indexed['fts5'],
            'results':[dict(zip(('conversation_id','raw_sha256','title','node_id','role','excerpt'),row)) for row in rows]}

def asset_gaps(store):
    refs=store.db.execute('SELECT kind,COUNT(*) FROM asset_refs GROUP BY kind ORDER BY kind').fetchall()
    physical=store.db.execute('SELECT COUNT(*),COALESCE(SUM(byte_size),0) FROM assets').fetchone()
    return {'physical_assets':physical[0],'physical_bytes':physical[1],
            'discovered_references':sum(n for _,n in refs),'by_kind':dict(refs),
            'linked_or_complete':'UNKNOWN_NO_PROVEN_REFERENCE_TO_BINARY_MAP',
            'note':'Never subtract physical count from reference count to certify coverage.'}

def compare_manifests(store, other):
    # No destructive reconciliation. Duplicates by ID are revisions, not errors.
    if not isinstance(other,dict) or not isinstance(other.get('records'),list):
        raise ValueError('OTHER_MANIFEST_UNRECOGNIZED')
    current={}
    for cid,h in store.db.execute('SELECT provider_id,raw_sha256 FROM conversations'):
        current.setdefault(cid,set()).add(h)
    external={}
    for rec in other['records']:
        if isinstance(rec,dict) and isinstance(rec.get('provider_id'),str) and isinstance(rec.get('raw_sha256'),str):
            external.setdefault(rec['provider_id'],set()).add(rec['raw_sha256'])
    common=set(current)&set(external)
    changes=[x for x in common if current[x]!=external[x]]
    return {'scope':'DIFFERENCE_OF_LOCAL_EVIDENCE_NOT_COMPLETE_ACCOUNT',
            'only_local':sorted(set(current)-set(external)),
            'only_external':sorted(set(external)-set(current)),
            'same_ids_different_revision_sets':sorted(changes),
            'matching_ids':len(common)-len(changes),
            'safe_to_delete_source_chat':False}


def scan_zip(path):
    """Non-mutating ZIP triage, bounded member count, no decompression or credential reads."""
    import zipfile
    import stat
    from pathlib import PurePosixPath
    file=Path(path).expanduser().resolve()
    with zipfile.ZipFile(file) as archive:
        entries=archive.infolist()
        count=len(entries)
        if count>200000: raise ValueError('ZIP_MEMBER_COUNT_EXCESSIVE')
        types={}; suspicious=[]; uncompressed=0; duplicates=set();seen=set()
        candidates=0
        for inf in entries:
            name=inf.filename.replace('\\','/')
            pathbits=PurePosixPath(name).parts
            uncompressed+=inf.file_size
            if name in seen: duplicates.add(name)
            seen.add(name)
            suffix=Path(name).suffix.lower()
            types[suffix]=types.get(suffix,0)+1
            if suffix in ('.json','.jsonl'):candidates+=1
            if name.startswith('/') or '..' in pathbits or ':' in name.split('/')[0]:suspicious.append({'kind':'PATH_TRAVERSAL','name':name[:120]})
            if stat.S_ISLNK(inf.external_attr >> 16): suspicious.append({'kind':'ZIP_SYMLINK','name':name[:120]})
            if inf.flag_bits & 0x1: suspicious.append({'kind':'ZIP_ENCRYPTED_MEMBER','name':name[:120]})
            if inf.file_size>0 and inf.file_size/max(inf.compress_size,1)>200:suspicious.append({'kind':'HIGH_COMPRESSION_RATIO','name':name[:120]})
        return {'zip_file_name':file.name,'zip_size_bytes':file.stat().st_size,'members':count,
                'candidate_text_members':candidates,'uncompressed_claimed_bytes':uncompressed,
                'types':types,'duplicate_paths':sorted(duplicates)[:30],
                'suspicious':suspicious[:100],
                'all_bytes_verified':False,'safe_to_extract':not suspicious and not duplicates,
                'note':'Metadata-only. CRC and content integrity NOT verified; never counts as complete export.'}
