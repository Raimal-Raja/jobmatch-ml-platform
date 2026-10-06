import argparse
import json
import platform
from pathlib import Path
from .retrieval import ROOT, TfidfRetriever, load_jobs
from .evaluation import evaluate


def main():
    parser = argparse.ArgumentParser(description="JobMatch keyword baseline")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    benchmark = sub.add_parser("evaluate")
    benchmark.add_argument("--output", type=Path, default=ROOT / "reports/baseline.json")
    args = parser.parse_args()
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
