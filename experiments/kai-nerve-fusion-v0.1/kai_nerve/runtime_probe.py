from __future__ import annotations
import os,pathlib,subprocess
SERVICE_ROOT=pathlib.Path("/data/data/com.termux/files/usr/var/service")
def inspect_service(name):
 root=SERVICE_ROOT/name;out={"service":name,"run_path":str(root/"run"),"exists":root.exists()}
 if not root.exists():return out
 try:out["run_script"]=(root/"run").read_text()
 except Exception as e:out["run_script_error"]=str(e)
 try:
  s=subprocess.check_output(["sv","status",str(root)],text=True,stderr=subprocess.STDOUT,timeout=2).strip()
  out["sv_status"]=s
  if "(pid " in s:
   pid=int(s.split("(pid ",1)[1].split(")",1)[0]);out["pid"]=pid;proc=pathlib.Path("/proc")/str(pid)
   try:out["cmdline"]=(proc/"cmdline").read_bytes().replace(b"\0",b" ").decode().strip()
   except Exception:pass
   try:out["cwd"]=os.readlink(proc/"cwd")
   except Exception:pass
 except Exception as e:out["sv_error"]=str(e)
 return out
def inspect_many(names):return {n:inspect_service(n) for n in names}
