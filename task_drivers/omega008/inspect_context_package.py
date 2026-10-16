"""Read-only directed checks for context ZIPs; no install or general schema engine.

Reuse the forge's path/JSON/frontmatter checks. The portable manifest checks below
cover the small published1.0.0 shape; they are strict authoring checks. They do not
emulate client recovery from unknown fields or certify OpenAI UI metadata.
"""
import argparse
import hashlib
from pathlib import Path
import re
import stat
import sys
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import bundle_io as b
import build_incremental as inc

SCHEMA='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json'
FIELDS={'$schema','name','version','description','author','homepage','repository','license','keywords','extensions'}


def portable_shape(value):
    if not isinstance(value,dict) or value.get('$schema')!=SCHEMA:
        raise ValueError('Portable manifest requires the supported schema')
    if set(value)-FIELDS:
        raise ValueError('Nonportable root fields: '+','.join(sorted(set(value)-FIELDS)))
    name=value.get('name')
    if (not isinstance(name,str) or not 1<=len(name)<=64
            or not re.fullmatch(r'(?!.*(?:--|\.\.))[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?',name)):
        raise ValueError('Invalid portable plugin name')
    for k in ['version','description','homepage','repository','license']:
        if k in value and not isinstance(value[k],str):raise ValueError('Manifest field must be text: '+k)
    if 'author' in value:
        author=value['author']
        if (not isinstance(author,dict) or set(author)-{'name','email','url'}
                or any(not isinstance(v,str) for v in author.values())):
            raise ValueError('Invalid portable author')
    if 'keywords' in value and (not isinstance(value['keywords'],list) or any(not isinstance(v,str) for v in value['keywords'])):
        raise ValueError('Invalid portable keywords')
    if 'extensions' in value and (not isinstance(value['extensions'],dict) or any(not isinstance(v,dict) for v in value['extensions'].values())):
        raise ValueError('Invalid portable extension object')


def resolve_manifests(portable=None,compatibility=None):
    if portable is not None:
        portable_shape(portable)
        inline=portable.get('extensions',{}).get('com.openai')
        if isinstance(inline,dict):settings,source=inline,'portable-inline'
        elif compatibility is not None:settings,source=compatibility,'codex-fallback'
        else:settings,source={},'none'
        if not isinstance(settings,dict):raise ValueError('Invalid compatibility overlay')
        return {'format':'AGENT_PLUGINS_1.0.0','name':portable['name'],'version':portable.get('version'),
                'openai_settings_source':source,'effective_openai_settings':settings}
    if not isinstance(compatibility,dict) or not isinstance(compatibility.get('name'),str) or not compatibility['name']:
        raise ValueError('A supported manifest is required')
    return {'format':'CODEX_COMPATIBILITY','name':compatibility['name'],'version':compatibility.get('version'),
            'openai_settings_source':'codex-manifest','effective_openai_settings':compatibility}


def inspect(archive):
    archive=Path(archive)
    if not archive.is_file() or archive.is_symlink():raise ValueError('Regular archive required')
    if archive.stat().st_size>=100*1024*1024:raise ValueError('Context ZIP exceeds the authoring size limit')
    with zipfile.ZipFile(archive) as z:
        infos=z.infolist();names=[x.filename for x in infos]
        if len(names)!=len(set(names)):raise ValueError('Duplicate archive member')
        files={};directories=[]
        for info in infos:
            mode=stat.S_IFMT(info.external_attr>>16)
            if mode not in [0,stat.S_IFREG,stat.S_IFDIR]:raise ValueError('Linked or special ZIP member')
            if info.is_dir():
                if mode not in [0,stat.S_IFDIR]:raise ValueError('ZIP directory kind mismatch')
                directories.append(str(b.safe_path(info.filename.rstrip('/'))))
            else:
                if mode==stat.S_IFDIR:raise ValueError('ZIP file kind mismatch')
                files[info.filename]=info
        b._validate_paths(list(files))
        if any(b._path_key(d) in {b._path_key(n) for n in files} for d in directories):raise ValueError('Directory/file conflict')
        if sum(x.file_size for x in files.values())>100*1024*1024:raise ValueError('Context payload exceeds the directed check budget')
        payload={n:z.read(info) for n,info in files.items()}
        portable=b.read_json(payload['plugin.json']) if 'plugin.json' in payload else None
        if 'plugin.json' in payload and not isinstance(portable,dict):
            raise ValueError('Portable root must be an object, not an absent manifest')
        compatibility=b.read_json(payload['.codex-plugin/plugin.json']) if '.codex-plugin/plugin.json' in payload else None
        result=resolve_manifests(portable,compatibility)
        skills=[]
        for n,data in payload.items():
            parts=n.split('/')
            if len(parts)==3 and parts[0]=='skills' and parts[2]=='SKILL.md':
                inc._candidate_header(data,parts[1]);skills.append({'name':parts[1],'path':n,'sha256':b.sha(data)})
        if not skills:raise ValueError('No immediate context skill discovered')
        result.update(status='DIRECTED_CHECKS_PASS',archive_bytes=archive.stat().st_size,
                      archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),skills=sorted(skills,key=lambda x:x['path']),
                      files={n:inc.record(d) for n,d in sorted(payload.items())},
                      boundaries=['No general JSON Schema engine','No full OpenAI extension schema check','No semantic truth or complete Markdown closure certification','No installer or client execution'],
                      active_installation=False,source_writes=False)
        return result


if __name__=='__main__':
    import json
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('archive',type=Path);a=p.parse_args()
    print(json.dumps(inspect(a.archive),ensure_ascii=False,indent=2))
