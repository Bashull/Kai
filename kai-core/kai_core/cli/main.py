from __future__ import annotations

import argparse
import json

from kai_core.connectors.google_drive import GoogleDriveConnector
from kai_core.models.chi_q import ChiQState, calculate_chi_q, decision_hint
from kai_core.tools.github_search import search_repositories
from kai_core.workflows.compare_alma_kai import compare_alma_kai
from kai_core.workflows.extract_document import process_document
from kai_core.memory.operational_memory import OperationalMemory


def _print(data):
    print(json.dumps(data, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(prog="kai")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("scan-drive")

    read_doc = sub.add_parser("read-doc")
    read_doc.add_argument("file_id")

    extract_doc = sub.add_parser("extract-doc")
    extract_doc.add_argument("file_id")
    extract_doc.add_argument("--target-master", default="KAI_IDENTIDAD_ALMA_ORIGENES_MAESTRO")

    compare = sub.add_parser("compare")
    compare.add_argument("file_id_a")
    compare.add_argument("file_id_b")

    unify = sub.add_parser("unify-topic")
    unify.add_argument("topic")

    research = sub.add_parser("research-github")
    research.add_argument("query")

    sub.add_parser("chiq")
    sub.add_parser("audit")

    args = parser.parse_args()
    connector = GoogleDriveConnector()

    if args.command == "scan-drive":
        _print({"status": "ok", "note": "Usa scanFolder con folderId específico en integración."})
    elif args.command == "read-doc":
        _print(connector.readFileText(args.file_id))
    elif args.command == "extract-doc":
        _print(process_document(args.file_id, args.target_master, connector=connector))
    elif args.command == "compare":
        _print(compare_alma_kai(args.file_id_a, args.file_id_b, connector=connector))
    elif args.command == "unify-topic":
        _print({"status": "pending", "topic": args.topic, "note": "Workflow de unificación temática en siguiente fase."})
    elif args.command == "research-github":
        _print({"query": args.query, "results": search_repositories(args.query, per_page=10)})
    elif args.command == "chiq":
        state = ChiQState(
            coherence=0.72,
            heat=0.30,
            integration=0.64,
            queue=0.45,
            quality=0.78,
            risk=0.25,
            recovery=0.66,
        )
        _print({"chi_q": calculate_chi_q(state), "decision": decision_hint(state)})
    elif args.command == "audit":
        _print({"recent_memory": OperationalMemory().recent(20)})


if __name__ == "__main__":
    main()
