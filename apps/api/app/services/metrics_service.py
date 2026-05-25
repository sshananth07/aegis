import structlog
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.evaluation import Evaluation
from app.models.benchmark import BenchmarkRun
from app.models.metrics import ProviderMetricsHourly, ProviderMetricsDaily
from app.models.review import Review
from app.core.enums import EvaluationStatus
from app.core.cache import cache_get, cache_set

logger = structlog.get_logger()

def compute_hourly_metrics(db: Session, provider: str) -> ProviderMetricsHourly:
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    evals = db.query(Evaluation).filter(
        Evaluation.provider == provider,
        Evaluation.created_at >= one_hour_ago
    ).all()

    if not evals:
        return None

    total = len(evals)
    successful = [e for e in evals if e.status == EvaluationStatus.completed]
    failed = [e for e in evals if e.status == EvaluationStatus.failed]
    fallbacks = [e for e in evals if e.provider != provider]

    latencies = [e.latency_ms for e in evals if e.latency_ms]
    costs = [e.cost for e in evals if e.cost]

    metrics = ProviderMetricsHourly(
        provider=provider,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
        success_rate=len(successful) / total if total else 0,
        avg_cost=sum(costs) / len(costs) if costs else 0,
        fallback_rate=len(fallbacks) / total if total else 0,
        total_evaluations=total,
        timestamp=datetime.utcnow()
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)

    logger.info("hourly_metrics_computed",
        provider=provider,
        total=total,
        success_rate=metrics.success_rate
    )
    return metrics


def compute_daily_metrics(db: Session, provider: str) -> ProviderMetricsDaily:
    one_day_ago = datetime.utcnow() - timedelta(days=1)

    evals = db.query(Evaluation).filter(
        Evaluation.provider == provider,
        Evaluation.created_at >= one_day_ago
    ).all()

    if not evals:
        return None

    total = len(evals)
    scores = [e.score for e in evals if e.score is not None]
    latencies = sorted([e.latency_ms for e in evals if e.latency_ms])
    costs = [e.cost for e in evals if e.cost]
    passed = [e for e in evals if e.score and e.score >= 0.5]

    # p95 latency
    p95_latency = None
    if latencies:
        idx = int(len(latencies) * 0.95)
        p95_latency = latencies[min(idx, len(latencies) - 1)]

    metrics = ProviderMetricsDaily(
        provider=provider,
        pass_rate=len(passed) / total if total else 0,
        p95_latency_ms=p95_latency,
        avg_cost=sum(costs) / len(costs) if costs else 0,
        avg_score=sum(scores) / len(scores) if scores else 0,
        total_evaluations=total,
        timestamp=datetime.utcnow()
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)

    logger.info("daily_metrics_computed",
        provider=provider,
        total=total,
        avg_score=metrics.avg_score,
        p95_latency=p95_latency
    )
    return metrics


def get_provider_summary(db: Session) -> dict:
    cache_key = "metrics:provider_summary"
    cached = cache_get(cache_key)
    if cached:
        logger.info("cache_hit", key=cache_key)
        return cached

    providers = db.query(Evaluation.provider).distinct().all()
    providers = [p[0] for p in providers]

    summary = {}
    for provider in providers:
        evals = db.query(Evaluation).filter(
            Evaluation.provider == provider
        ).all()

        total = len(evals)
        if total == 0:
            continue

        scores = [e.score for e in evals if e.score is not None]
        latencies = sorted([e.latency_ms for e in evals if e.latency_ms])
        costs = [e.cost for e in evals if e.cost]
        successful = [e for e in evals if e.status == EvaluationStatus.completed]

        p95 = None
        if latencies:
            idx = int(len(latencies) * 0.95)
            p95 = latencies[min(idx, len(latencies) - 1)]

        summary[provider] = {
            "total_evaluations": total,
            "success_rate": len(successful) / total,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "avg_latency_ms": sum(latencies) / len(latencies) if latencies else 0,
            "p95_latency_ms": p95,
            "avg_cost": sum(costs) / len(costs) if costs else 0,
        }

    cache_set(cache_key, summary, ttl_seconds=300)
    return summary


def get_platform_overview(db: Session) -> dict:
    evaluations = db.query(Evaluation).all()
    benchmark_runs = db.query(BenchmarkRun).order_by(
        BenchmarkRun.created_at.desc()
    ).all()
    reviews = db.query(Review).all()

    evaluation_statuses: dict[str, int] = {}
    provider_costs: dict[str, float] = {}
    failure_reasons: dict[str, int] = {}

    total_cost = 0.0
    for evaluation in evaluations:
        status = str(evaluation.status)
        evaluation_statuses[status] = evaluation_statuses.get(status, 0) + 1

        cost = evaluation.cost or 0.0
        total_cost += cost
        provider_costs[evaluation.provider] = (
            provider_costs.get(evaluation.provider, 0.0) + cost
        )

        score_details = evaluation.score_details or {}
        for reason in score_details.get("failure_reasons") or []:
            failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    benchmark_statuses: dict[str, int] = {}
    benchmark_total_cases = 0
    benchmark_passed_cases = 0
    benchmark_failures: dict[str, int] = {}

    for run in benchmark_runs:
        status = str(run.status)
        benchmark_statuses[status] = benchmark_statuses.get(status, 0) + 1
        benchmark_total_cases += int(run.total_cases or 0)
        benchmark_passed_cases += int(run.passed_cases or 0)

        for result in run.results or []:
            for reason in result.get("failure_reasons") or []:
                benchmark_failures[reason] = benchmark_failures.get(reason, 0) + 1
                failure_reasons[reason] = failure_reasons.get(reason, 0) + 1

    review_statuses: dict[str, int] = {}
    for review in reviews:
        review_statuses[review.status] = review_statuses.get(review.status, 0) + 1

    recent_benchmark_runs = [
        {
            "id": str(run.id),
            "status": run.status,
            "total_cases": int(run.total_cases or 0),
            "passed_cases": int(run.passed_cases or 0),
            "avg_score": run.avg_score or 0,
            "avg_latency_ms": run.avg_latency_ms or 0,
            "avg_cost": run.avg_cost or 0,
            "created_at": run.created_at.isoformat(),
        }
        for run in benchmark_runs[:5]
    ]

    failed_or_review_required = [
        {
            "id": str(evaluation.id),
            "provider": evaluation.provider,
            "status": evaluation.status,
            "score": evaluation.score,
            "failure_reasons": (evaluation.score_details or {}).get(
                "failure_reasons"
            ) or [],
            "created_at": evaluation.created_at.isoformat(),
        }
        for evaluation in sorted(
            evaluations,
            key=lambda item: item.created_at,
            reverse=True,
        )
        if evaluation.status in (
            EvaluationStatus.failed,
            EvaluationStatus.review_required,
        )
    ]

    return {
        "benchmarks": {
            "total_runs": len(benchmark_runs),
            "status_counts": benchmark_statuses,
            "total_cases": benchmark_total_cases,
            "passed_cases": benchmark_passed_cases,
            "pass_rate": (
                benchmark_passed_cases / benchmark_total_cases
                if benchmark_total_cases
                else 0
            ),
            "recent_runs": recent_benchmark_runs,
        },
        "costs": {
            "total_cost": total_cost,
            "by_provider": provider_costs,
        },
        "failures": {
            "total_failed_or_review_required": len(failed_or_review_required),
            "reason_counts": failure_reasons,
            "benchmark_reason_counts": benchmark_failures,
            "recent": failed_or_review_required[:5],
        },
        "reviews": {
            "total_reviews": len(reviews),
            "status_counts": review_statuses,
        },
        "evaluations": {
            "total_evaluations": len(evaluations),
            "status_counts": evaluation_statuses,
        },
    }
