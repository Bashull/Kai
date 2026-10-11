from __future__ import annotations
import argparse,json,pathlib,time
from .parsers import parse_line
from .normalize import Normalizer
from .freshness import perception_ages
from .skills import skill_list
from .runtime_probe import inspect_many

def main(argv=None):
 ap=argparse.ArgumentParser(prog="kai-nerve");sub=ap.add_subparsers(dest="cmd",required=True)
 p=sub.add_parser("parse-line");p.add_argument("line");p.add_argument("--transport",default="fixture")
 sub.add_parser("skills")
 p=sub.add_parser("freshness");p.add_argument("status_file");p.add_argument("--session");p.add_argument("--max-age-ms",type=float,default=750)
 p=sub.add_parser("probe-runtime");p.add_argument("services",nargs="+")
 a=ap.parse_args(argv)
 if a.cmd=="skills":print(json.dumps(skill_list(),ensure_ascii=False,indent=2));return 0
 if a.cmd=="parse-line":
  x=parse_line(a.line,transport=a.transport);print(json.dumps(None if x is None else x.__dict__,ensure_ascii=False,indent=2));return 0
 if a.cmd=="probe-runtime":print(json.dumps(inspect_many(a.services),ensure_ascii=False,indent=2));return 0
 if a.cmd=="freshness":
  path=pathlib.Path(a.status_file);p=json.loads(path.read_text());now=time.time()*1000
  file_age=max(0,now-path.stat().st_mtime*1000);src,trans=perception_ages(frame_age_ms=p.get("frame_age_ms"),file_age_ms=file_age)
  from .models import ParsedObservation
  obs=ParsedObservation("perception","frame",p,session_id=a.session,source_seq=p.get("seq"))
  e=Normalizer(a.max_age_ms).normalize(obs,received_wall_ms=now,published_wall_ms=now,
       source_age_ms=src,transport_age_ms=trans,process_ok=p.get("ok") is True)
  print(json.dumps(e.to_dict(),ensure_ascii=False,indent=2));return 0
 return 2
if __name__=="__main__":raise SystemExit(main())
