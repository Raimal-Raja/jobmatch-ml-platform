import argparse
import json
import platform
from pathlib import Path
from .retrieval import ROOT, TfidfRetriever, load_jobs
from .evaluation import evaluate, compare
from .semantic import make_retriever
from .profiles import ProfileStore
from .constraints import apply_constraints


def main():
    parser = argparse.ArgumentParser(description="JobMatch retrieval and résumé profiles")
    sub = parser.add_subparsers(dest="command", required=True)
    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=5)
    search.add_argument("--approach", choices=("tfidf", "semantic", "reranked"), default="tfidf")
    search.add_argument("--context", type=Path, help="JSON with confirmed skills and explicit preferences")
    search.add_argument("--offline", action="store_true", help="Use cached model files only")
    benchmark = sub.add_parser("evaluate")
    benchmark.add_argument("--output", type=Path, default=ROOT / "reports/baseline.json")
    benchmark.add_argument("--fixture", type=Path, default=ROOT / "data/evaluation.json")
    ingestion = sub.add_parser("ingest", help="Import explicitly permitted manual job JSON")
    ingestion.add_argument("file", type=Path)
    ingestion.add_argument("--output", type=Path, default=ROOT / "private_data/jobs.json")
    pg_index = sub.add_parser("index-postgres", help="Index a catalog with the fixed semantic model")
    pg_index.add_argument("--jobs", type=Path, default=ROOT / "data/jobs.json")
    pg_index.add_argument("--offline", action="store_true")
    comparison = sub.add_parser("compare", help="Benchmark TF-IDF and semantic retrieval on identical labels")
    comparison.add_argument("--output", type=Path, default=ROOT / "reports/comparison.json")
    comparison.add_argument("--repeats", type=int, default=100)
    comparison.add_argument("--offline", action="store_true")
    comparison.add_argument("--fixture", type=Path, default=ROOT / "data/evaluation.json")
    comparison.add_argument("--mlflow-dir", type=Path)
    for name in ("review-export", "review-apply"):
        review = sub.add_parser(name)
        review.add_argument("file", type=Path)
        if name == "review-apply":
            review.add_argument("--output", type=Path, default=ROOT / "private_data/evaluation_reviewed.json")
    resume = sub.add_parser("resume", help="Import PDF and print a draft profile")
    resume.add_argument("pdf", type=Path)
    profile = sub.add_parser("profile")
    profile.add_argument("action", choices=("show", "update", "delete", "search"))
    profile.add_argument("id")
    profile.add_argument("--corrections", type=Path)
    profile.add_argument("--approach", choices=("tfidf", "semantic", "reranked"), default="tfidf")
    profile.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.command in ("review-export", "review-apply"):
        from .review import export_review, apply_review
        fixture = json.loads((ROOT / "data/evaluation.json").read_text(encoding="utf-8"))
        try:
            result = (export_review(load_jobs(), fixture, args.file) if args.command == "review-export"
                      else apply_review(load_jobs(), fixture, args.file, args.output))
            print(json.dumps(result, indent=2))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        return
    if args.command == "index-postgres":
        from .postgres import PgvectorStore
        from .semantic import SemanticRetriever
        try:
            catalog = load_jobs(args.jobs)
            encoder = SemanticRetriever(catalog, offline=args.offline)
            print(json.dumps(PgvectorStore().upsert(catalog, encoder.vectors), indent=2))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        return
    if args.command == "ingest":
        from .ingestion import ingest
        try:
            print(json.dumps(ingest(args.file, args.output), indent=2))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        return
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
                confirmed_text = store.search_text(args.id)
                result = make_retriever(load_jobs(), args.approach, args.offline).search(confirmed_text, 5)
            else:
                store.delete(args.id)
                result = {"deleted": args.id}
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        print(json.dumps(result, indent=2))
        return
    jobs = load_jobs()
    if args.command == "search":
        try:
            retriever = make_retriever(jobs, args.approach, args.offline)
            results = retriever.search(args.query, min(len(jobs), 20) if args.context else args.limit)
            if args.context:
                results = apply_constraints(results, json.loads(args.context.read_text(encoding="utf-8")))[:args.limit]
            print(json.dumps(results, indent=2))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
    else:
        fixture = json.loads(args.fixture.read_text(encoding="utf-8"))
        label_status = fixture.get("review_status", "provisional_not_human_reviewed")
        try:
            report = (compare(jobs, fixture["profiles"], fixture["judgments"], args.repeats, args.offline, label_status)
                      if args.command == "compare" else evaluate(jobs, fixture["profiles"], fixture["judgments"], label_status=label_status))
        except (ValueError, OSError) as exc:
            parser.error(str(exc))
        report["environment"] = {"python": platform.python_version(), "platform": platform.platform()}
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if args.command == "compare" and args.mlflow_dir:
            from .tracking import log_comparison
            try:
                log_comparison(report, args.output, args.mlflow_dir)
            except ValueError as exc:
                parser.error(str(exc))
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
