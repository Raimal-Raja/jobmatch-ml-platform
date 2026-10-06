import argparse
import json
import platform
from pathlib import Path
from .retrieval import ROOT, TfidfRetriever, load_jobs
from .evaluation import evaluate
from .profiles import ProfileStore


def main():
    parser = argparse.ArgumentParser(description="JobMatch keyword baseline")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    benchmark = sub.add_parser("evaluate")
    benchmark.add_argument("--output", type=Path, default=ROOT / "reports/baseline.json")
    resume = sub.add_parser("resume", help="Import PDF and print a draft profile")
    resume.add_argument("pdf", type=Path)
    profile = sub.add_parser("profile")
    profile.add_argument("action", choices=("show", "update", "delete", "search"))
    profile.add_argument("id")
    profile.add_argument("--corrections", type=Path)
    args = parser.parse_args()
    store = ProfileStore()
    if args.command in ("resume", "profile"):
        try:
            if args.command == "resume":
                result = store.create(args.pdf)
            elif args.action == "show":
                result = store.get(args.id)
            elif args.action == "update":
                if args.corrections is None:
                    raise ValueError("update requires --corrections JSON file")
                result = store.update(args.id, json.loads(args.corrections.read_text(encoding="utf-8")))
            elif args.action == "search":
                result = TfidfRetriever(load_jobs()).search(store.search_text(args.id), 5)
            else:
                store.delete(args.id)
                result = {"deleted": args.id}
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, indent=2))
        return
    jobs = load_jobs()
    if args.command == "search":
        print(json.dumps(TfidfRetriever(jobs).search(args.query, args.limit), indent=2))
    else:
        fixture = json.loads((ROOT / "data/evaluation.json").read_text(encoding="utf-8"))
        report = evaluate(jobs, fixture["profiles"], fixture["judgments"])
        report["environment"] = {"python": platform.python_version(), "platform": platform.platform()}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
