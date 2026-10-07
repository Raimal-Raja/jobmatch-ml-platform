"""Optional local experiment logging; reports remain the source of record."""
from pathlib import Path


def log_comparison(report, output, tracking_directory):
    try:
        import mlflow
    except ImportError as exc:
        raise ValueError('Install tracking support with pip install -e ".[tracking]"') from exc
    directory = Path(tracking_directory).resolve()
    directory.mkdir(parents=True, exist_ok=True)
    mlflow.set_tracking_uri(f"sqlite:///{directory / 'experiments.db'}")
    mlflow.set_experiment("jobmatch-retrieval")
    with mlflow.start_run():
        mlflow.log_param("fixture_sha256", report["fixture_sha256"])
        for result in report["results"]:
            prefix = result["approach"]
            for key in ("ndcg_at_10", "precision_at_5", "p95_response_ms", "paid_api_cost_usd_per_search"):
                mlflow.log_metric(f"{prefix}.{key}", result[key])
            mlflow.log_param(f"{prefix}.label_status", result["label_status"])
        mlflow.log_artifact(str(output))
