"""Capture explicitly requested auxiliary text/code as inert bytes, never execute it."""
import argparse,base64,hashlib,json,os,pathlib,re,stat,zipfile
from capture_skills import read_regular,TOKEN,PEM,digest,json_bytes,write_new


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--request',required=True);ap.add_argument('--output',required=True);ap.add_argument('--stop-file');a=ap.parse_args()
    def check():
        if a.stop_file and pathlib.Path(a.stop_file).exists():raise RuntimeError('STOP requested')
    check()
    request=json.loads(pathlib.Path(a.request).read_text(encoding='utf8'));out=pathlib.Path(a.output).absolute()
    if out.exists():raise ValueError('New isolated output required')
    paths=list(request['files']);inventory=[];blocked=[]
    skip={'.git','node_modules','.venv','venv','__pycache__','keys','secrets','credentials','auth','cache','logs','state'}
    extensions={'.py','.js','.mjs','.cjs','.ps1','.cmd','.bat','.sh','.ts','.md','.txt','.toml'}
    for root_text in request.get('code_roots',[]):
        check()
        root=pathlib.Path(root_text)
        if '..' in root.parts or root.is_symlink() or getattr(root,'is_junction',lambda:False)():raise ValueError('Unsafe inventory root')
        if not root.is_dir():inventory.append({'root':str(root),'state':'NOT_FOUND'});continue
        for directory,dirs,files in os.walk(root,followlinks=False):
            base=pathlib.Path(directory);depth=len(base.relative_to(root).parts)
            check()
            dirs[:]=sorted(n for n in dirs if n.lower() not in skip and not (base/n).is_symlink() and not getattr(base/n,'is_junction',lambda:False)() and depth<3)
            for name in sorted(files):
                p=base/name
                inventory.append({'path':str(p),'bytes':p.lstat().st_size,'symlink':p.is_symlink()})
                if p.suffix.lower() in extensions or name in ('LICENSE','COPYING','package.json','package-lock.json'):
                    paths.append(str(p))
    check();out.mkdir(parents=True)
    records=[]
    for text in dict.fromkeys(paths):
        check()
        p=pathlib.Path(text).absolute();row={'requested_path':text,'state':'BLOCKED'}
        try:
            # node_modules is normally pruned for size. An operator may name one
            # exact package root for source inspection; secret exclusions remain.
            explicit_package=any(p.is_relative_to(pathlib.Path(x).absolute())
                                 for x in request.get('explicit_package_roots',[]))
            excluded=skip-{'node_modules'} if explicit_package else skip
            if '..' in p.parts or any(part.lower() in excluded for part in p.parts) or p.name.startswith('.env'):
                raise ValueError('Excluded path')
            if p.is_symlink():
                row['symlink_target']=os.readlink(p);resolved=p.resolve(strict=True)
                if not any(resolved.is_relative_to(pathlib.Path(x)) for x in request.get('resolved_target_roots',[])):
                    raise ValueError('Symlink target outside explicit allowed roots')
                p=resolved;row['resolved_target']=str(p)
            data=read_regular(p)
            if TOKEN.search(data) or PEM.search(data):raise ValueError('Credential pattern; values withheld')
            data.decode('utf8')
            sha=digest(data);obj='objects/'+sha+'/'+p.name
            write_new(out/obj,data);row.update(state='CAPTURED',actual_path=str(p),object_path=obj,bytes=len(data),sha256=sha)
        except Exception as e:row['error']=type(e).__name__+': '+str(e)
        records.append(row)
    manifest={'format':'kai.resources.capture/1','scope':'Explicit code/text sources only; no execution; binary/secret locations excluded','rows':records,'inventory':inventory}
    check();write_new(out/'RESOURCE_MANIFEST.json',json_bytes(manifest))
    archive=out.with_name(out.name+'.zip')
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
        for p in sorted(out.rglob('*')):
            check()
            if p.is_file():
                info=zipfile.ZipInfo(p.relative_to(out).as_posix(),date_time=(2026,10,15,0,0,0));info.external_attr=(stat.S_IFREG|0o644)<<16;info.compress_type=zipfile.ZIP_DEFLATED;z.writestr(info,p.read_bytes())
    with zipfile.ZipFile(archive) as z:assert z.testzip() is None
    check();raw=archive.read_bytes();enc=base64.b64encode(raw).decode();transport=out.with_name(out.name+'.b64')
    write_new(transport,('\n'.join(enc[i:i+1024] for i in range(0,len(enc),1024))+'\n').encode())
    check();print(json.dumps({'archive':str(archive),'bytes':len(raw),'sha256':digest(raw),'rows':len(records),'captured':sum(r['state']=='CAPTURED' for r in records),'inventory_entries':len(inventory),'transport':str(transport),'lines':(len(enc)+1023)//1024}))


if __name__=='__main__':main()
