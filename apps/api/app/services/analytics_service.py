import structlog
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from app.models.evaluation import Evaluation, Trace
from app.models.benchmark import BenchmarkRun
from app.core.enums import EvaluationStatus
from app.core.cache import cache_get, cache_set

logger = structlog.get_logger()


# ── Failure Overview ──────────────────────────────────────────────

def get_failure_overview(db: Session, user_id: str) -> dict:
    cache_key = f"analytics:failure_overview:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id
    ).all()

    total = len(evals)
    failed = [e for e in evals if e.status in (
        EvaluationStatus.failed,
        EvaluationStatus.review_required
    )]
    failure_rate = len(failed) / total if total else 0

    # Count failure reasons across all evaluations
    reason_counts: dict[str, int] = {}
    for e in evals:
        if e.score_details and "failure_reasons" in e.score_details:
            for reason in e.score_details["failure_reasons"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    top_reason = max(reason_counts, key=reason_counts.get) if reason_counts else None

    # Regression alerts count
    regressions = get_regressions(db, user_id)
    high_regressions = [r for r in regressions if r["severity"] in ("high", "critical")]

    result = {
        "total_evaluations": total,
        "total_failures": len(failed),
        "failure_rate": round(failure_rate, 4),
        "top_failure_reason": top_reason,
        "regression_alerts": len(high_regressions),
    }

    cache_set(cache_key, result, ttl_seconds=60)
    return result


# ── Failure Timeseries ────────────────────────────────────────────

def get_failure_timeseries(
    db: Session,
    user_id: str,
    days: int = 14
) -> list[dict]:
    cache_key = f"analytics:failure_timeseries:{user_id}:{days}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    since = datetime.utcnow() - timedelta(days=days)
    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id,
        Evaluation.created_at >= since
    ).all()

    # Group by date
    buckets: dict[str, dict] = {}
    for e in evals:
        date_str = e.created_at.strftime("%Y-%m-%d")
        if date_str not in buckets:
            buckets[date_str] = {"total": 0, "failed": 0}
        buckets[date_str]["total"] += 1
        if e.status in (EvaluationStatus.failed, EvaluationStatus.review_required):
            buckets[date_str]["failed"] += 1

    result = [
        {
            "date": date,
            "total": data["total"],
            "failed": data["failed"],
            "failure_rate": round(
                data["failed"] / data["total"], 4
            ) if data["total"] else 0,
            "pass_rate": round(
                1 - (data["failed"] / data["total"]), 4
            ) if data["total"] else 1,
        }
        for date, data in sorted(buckets.items())
    ]

    cache_set(cache_key, result, ttl_seconds=300)
    return result


# ── Failure By Reason ─────────────────────────────────────────────

def get_failures_by_reason(db: Session, user_id: str) -> list[dict]:
    cache_key = f"analytics:failures_by_reason:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id
    ).all()

    reason_counts: dict[str, int] = {}
    for e in evals:
        if e.score_details and "failure_reasons" in e.score_details:
            for reason in e.score_details["failure_reasons"]:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

    result = [
        {"failure_reason": reason, "count": count}
        for reason, count in sorted(
            reason_counts.items(), key=lambda x: x[1], reverse=True
        )
    ]

    cache_set(cache_key, result, ttl_seconds=60)
    return result


# ── Provider Stability ────────────────────────────────────────────

def get_provider_stability(db: Session, user_id: str) -> list[dict]:
    cache_key = f"analytics:provider_stability:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id
    ).all()

    provider_data: dict[str, dict] = {}
    for e in evals:
        p = e.provider
        if p not in provider_data:
            provider_data[p] = {
                "total": 0,
                "failed": 0,
                "timeouts": 0,
                "latencies": [],
                "scores": [],
                "costs": [],
            }
        d = provider_data[p]
        d["total"] += 1
        if e.status in (EvaluationStatus.failed, EvaluationStatus.review_required):
            d["failed"] += 1
        if e.latency_ms:
            d["latencies"].append(e.latency_ms)
        if e.score is not None:
            d["scores"].append(e.score)
        if e.cost:
            d["costs"].append(e.cost)

    result = []
    for provider, d in provider_data.items():
        total = d["total"]
        failure_rate = d["failed"] / total if total else 0
        avg_latency = sum(d["latencies"]) / len(d["latencies"]) if d["latencies"] else 0
        avg_score = sum(d["scores"]) / len(d["scores"]) if d["scores"] else 0
        avg_cost = sum(d["costs"]) / len(d["costs"]) if d["costs"] else 0
        efficiency = round(avg_score / avg_cost, 2) if avg_cost > 0 else None

        result.append({
            "provider": provider,
            "total_evaluations": total,
            "failure_rate": round(failure_rate, 4),
            "avg_latency_ms": round(avg_latency),
            "avg_score": round(avg_score, 4),
            "avg_cost": round(avg_cost, 6),
            "cost_efficiency_score": efficiency,
        })

    result.sort(key=lambda x: x["failure_rate"])
    cache_set(cache_key, result, ttl_seconds=60)
    return result


# ── Cost Overview ─────────────────────────────────────────────────

def get_cost_overview(db: Session, user_id: str) -> dict:
    cache_key = f"analytics:cost_overview:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id
    ).all()

    total_cost = sum(e.cost for e in evals if e.cost)
    total = len(evals)
    avg_cost = total_cost / total if total else 0

    provider_costs: dict[str, list] = {}
    for e in evals:
        if e.cost:
            if e.provider not in provider_costs:
                provider_costs[e.provider] = []
            provider_costs[e.provider].append(e.cost)

    most_expensive = max(
        provider_costs,
        key=lambda p: sum(provider_costs[p])
    ) if provider_costs else None

    result = {
        "total_cost": round(total_cost, 6),
        "avg_cost_per_eval": round(avg_cost, 6),
        "most_expensive_provider": most_expensive,
    }

    cache_set(cache_key, result, ttl_seconds=60)
    return result


def get_cost_by_provider(db: Session, user_id: str) -> list[dict]:
    cache_key = f"analytics:cost_by_provider:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id
    ).all()

    provider_data: dict[str, dict] = {}
    for e in evals:
        p = e.provider
        if p not in provider_data:
            provider_data[p] = {"costs": [], "scores": []}
        if e.cost:
            provider_data[p]["costs"].append(e.cost)
        if e.score is not None:
            provider_data[p]["scores"].append(e.score)

    result = []
    for provider, d in provider_data.items():
        total_cost = sum(d["costs"])
        avg_cost = total_cost / len(d["costs"]) if d["costs"] else 0
        avg_score = sum(d["scores"]) / len(d["scores"]) if d["scores"] else 0
        efficiency = round(avg_score / avg_cost, 2) if avg_cost > 0 else None

        result.append({
            "provider": provider,
            "total_cost": round(total_cost, 6),
            "avg_cost": round(avg_cost, 6),
            "cost_efficiency_score": efficiency,
        })

    result.sort(key=lambda x: x["total_cost"], reverse=True)
    cache_set(cache_key, result, ttl_seconds=60)
    return result


def get_cost_timeseries(db: Session, user_id: str, days: int = 14) -> list[dict]:
    cache_key = f"analytics:cost_timeseries:{user_id}:{days}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    since = datetime.utcnow() - timedelta(days=days)
    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id,
        Evaluation.created_at >= since,
        Evaluation.cost.isnot(None)
    ).all()

    buckets: dict[str, float] = {}
    for e in evals:
        date_str = e.created_at.strftime("%Y-%m-%d")
        buckets[date_str] = buckets.get(date_str, 0) + (e.cost or 0)

    result = [
        {"date": date, "cost": round(cost, 6)}
        for date, cost in sorted(buckets.items())
    ]

    cache_set(cache_key, result, ttl_seconds=300)
    return result


# ── Regression Detection ──────────────────────────────────────────

def get_regressions(db: Session, user_id: str) -> list[dict]:
    cache_key = f"analytics:regressions:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    now = datetime.utcnow()
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    evals = db.query(Evaluation).filter(
        Evaluation.created_by == user_id,
        Evaluation.created_at >= previous_start
    ).all()

    current_evals = [e for e in evals if e.created_at >= current_start]
    previous_evals = [e for e in evals if e.created_at < current_start]

    regressions = []

    # Provider-level regression detection
    providers = set(e.provider for e in evals)
    for provider in providers:
        curr = [e for e in current_evals if e.provider == provider]
        prev = [e for e in previous_evals if e.provider == provider]

        if len(curr) < 2 or len(prev) < 2:
            continue

        # Pass rate regression
        curr_pass = sum(
            1 for e in curr
            if e.status == EvaluationStatus.completed
        ) / len(curr)
        prev_pass = sum(
            1 for e in prev
            if e.status == EvaluationStatus.completed
        ) / len(prev)

        if prev_pass > 0:
            change = (curr_pass - prev_pass) / prev_pass
            if change <= -0.15:
                regressions.append({
                    "entity_type": "provider",
                    "entity_id": provider,
                    "metric": "pass_rate",
                    "previous": round(prev_pass, 4),
                    "current": round(curr_pass, 4),
                    "change_percent": round(change * 100, 1),
                    "severity": "critical" if change <= -0.30 else "high",
                })

        # Latency regression
        curr_latencies = [e.latency_ms for e in curr if e.latency_ms]
        prev_latencies = [e.latency_ms for e in prev if e.latency_ms]

        if curr_latencies and prev_latencies:
            curr_avg_lat = sum(curr_latencies) / len(curr_latencies)
            prev_avg_lat = sum(prev_latencies) / len(prev_latencies)
            lat_change = (curr_avg_lat - prev_avg_lat) / prev_avg_lat

            if lat_change >= 0.25:
                regressions.append({
                    "entity_type": "provider",
                    "entity_id": provider,
                    "metric": "latency",
                    "previous": round(prev_avg_lat),
                    "current": round(curr_avg_lat),
                    "change_percent": round(lat_change * 100, 1),
                    "severity": "critical" if lat_change >= 0.50 else "high",
                })

        # Score regression
        curr_scores = [e.score for e in curr if e.score is not None]
        prev_scores = [e.score for e in prev if e.score is not None]

        if curr_scores and prev_scores:
            curr_avg_score = sum(curr_scores) / len(curr_scores)
            prev_avg_score = sum(prev_scores) / len(prev_scores)
            score_change = (curr_avg_score - prev_avg_score) / prev_avg_score

            if score_change <= -0.15:
                regressions.append({
                    "entity_type": "provider",
                    "entity_id": provider,
                    "metric": "avg_score",
                    "previous": round(prev_avg_score, 4),
                    "current": round(curr_avg_score, 4),
                    "change_percent": round(score_change * 100, 1),
                    "severity": "critical" if score_change <= -0.30 else "high",
                })

    regressions.sort(key=lambda x: abs(x["change_percent"]), reverse=True)
    cache_set(cache_key, regressions, ttl_seconds=300)
    return regressions


# ── Benchmark Analytics ───────────────────────────────────────────

def get_benchmark_stability(db: Session, user_id: str) -> list[dict]:
    cache_key = f"analytics:benchmark_stability:{user_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    from app.models.benchmark import BenchmarkSuite, BenchmarkRun
    import math

    suites = db.query(BenchmarkSuite).filter(
        BenchmarkSuite.created_by == user_id
    ).all()

    result = []
    for suite in suites:
        runs = db.query(BenchmarkRun).filter(
            BenchmarkRun.suite_id == suite.id,
            BenchmarkRun.status == "completed"
        ).order_by(BenchmarkRun.created_at.desc()).limit(10).all()

        if not runs:
            continue

        pass_rates = []
        for run in runs:
            total = int(run.total_cases or 0)
            passed = int(run.passed_cases or 0)
            if total > 0:
                pass_rates.append(passed / total)

        if not pass_rates:
            continue

        avg_pass_rate = sum(pass_rates) / len(pass_rates)

        # Standard deviation
        if len(pass_rates) > 1:
            variance = sum((x - avg_pass_rate) ** 2 for x in pass_rates) / len(pass_rates)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        # Stability classification
        if std_dev < 0.05:
            stability = "stable"
        elif std_dev < 0.15:
            stability = "variable"
        else:
            stability = "unstable"

        # Trend — compare last run to average
        trend = None
        if len(pass_rates) >= 2:
            latest = pass_rates[0]
            previous_avg = sum(pass_rates[1:]) / len(pass_rates[1:])
            if latest > previous_avg + 0.05:
                trend = "improving"
            elif latest < previous_avg - 0.05:
                trend = "degrading"
            else:
                trend = "stable"

        result.append({
            "suite_id": str(suite.id),
            "suite_name": suite.name,
            "total_runs": len(runs),
            "avg_pass_rate": round(avg_pass_rate, 4),
            "std_deviation": round(std_dev, 4),
            "stability": stability,
            "trend": trend,
            "latest_pass_rate": round(pass_rates[0], 4) if pass_rates else None,
        })

    result.sort(key=lambda x: x["std_deviation"], reverse=True)
    cache_set(cache_key, result, ttl_seconds=300)
    return result


def get_benchmark_history(
    db: Session,
    user_id: str,
    suite_id: str = None
) -> list[dict]:
    cache_key = f"analytics:benchmark_history:{user_id}:{suite_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    from app.models.benchmark import BenchmarkSuite, BenchmarkRun

    query = db.query(BenchmarkRun).join(
        BenchmarkSuite,
        BenchmarkRun.suite_id == BenchmarkSuite.id
    ).filter(
        BenchmarkSuite.created_by == user_id,
        BenchmarkRun.status == "completed"
    )

    if suite_id:
        query = query.filter(BenchmarkRun.suite_id == suite_id)

    runs = query.order_by(BenchmarkRun.created_at.asc()).limit(50).all()

    result = []
    for run in runs:
        total = int(run.total_cases or 0)
        passed = int(run.passed_cases or 0)
        result.append({
            "run_id": str(run.id),
            "suite_id": str(run.suite_id),
            "date": run.created_at.strftime("%Y-%m-%d"),
            "pass_rate": round(passed / total, 4) if total else 0,
            "avg_score": round(run.avg_score, 4) if run.avg_score else 0,
            "avg_latency_ms": round(run.avg_latency_ms) if run.avg_latency_ms else 0,
            "total_cases": total,
            "passed_cases": passed,
        })

    cache_set(cache_key, result, ttl_seconds=300)
    return result
