import uuid
import asyncio
import structlog
from sqlalchemy.orm import Session
from app.models.evaluation import EvaluationGroup
from app.models.benchmark import BenchmarkSuite, BenchmarkRun, DatasetItem
from app.models.prompt import PromptVersion
from app.providers.router import ProviderRouter
from app.services.scoring import FailureReason, compute_score
from app.services.comparison_service import compute_comparison, ProviderResult
from app.core.enums import BenchmarkRunStatus, EvaluationStatus
from app.services.webhook_service import trigger_webhook

logger = structlog.get_logger()

INPUT_PLACEHOLDERS = ("{input}", "{{input}}", "{{ input }}")

# Maximum time (seconds) allowed for all providers to respond for a single item
ITEM_TIMEOUT_SECONDS = 120


def build_benchmark_prompt(template: str, input_text: str) -> str:
    stripped_template = template.strip()

    for placeholder in INPUT_PLACEHOLDERS:
        if placeholder in stripped_template:
            return stripped_template.replace(placeholder, input_text)

    return (
        f"{stripped_template}\n\n"
        "Benchmark case instructions:\n"
        "- Respond only to the customer's actual issue below.\n"
        "- Do not reuse details from examples unless they match this issue.\n"
        "- Keep the response concise.\n\n"
        f"Customer issue:\n{input_text}"
    )


async def _run_single_provider(
    prompt: str,
    provider_name: str,
    expected_output: str,
    check_json: bool,
    pass_threshold: float,
    required_keywords: list,
    required_json_fields: list,
    semantic_similarity_threshold: float,
    keyword_coverage_threshold: float,
    require_json: bool,
) -> dict:
    try:
        router = ProviderRouter(provider_name)
        result, events = await router.route(prompt)

        score_result = compute_score(
            response=result.content,
            expected_output=expected_output,
            check_json=check_json,
            required_keywords=required_keywords,
            required_json_fields=required_json_fields,
            require_json=require_json,
            semantic_similarity_threshold=semantic_similarity_threshold,
            keyword_coverage_threshold=keyword_coverage_threshold,
        )

        passed = (
            score_result.overall >= pass_threshold
            and score_result.validation_passed
        )

        return {
            "provider": result.provider,
            "response": result.content,
            "score": score_result.overall,
            "score_details": score_result.details,
            "failure_reasons": score_result.failure_reasons,
            "latency_ms": result.latency_ms,
            "token_usage": result.token_usage,
            "cost": result.cost,
            "passed": passed,
            "events": events,
            "error": None
        }

    except Exception as e:
        failure_reason = FailureReason.PROVIDER_ERROR.value
        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
            failure_reason = FailureReason.PROVIDER_TIMEOUT.value

        logger.error("provider_execution_failed",
            provider=provider_name, error=str(e))
        return {
            "provider": provider_name,
            "response": None,
            "score": 0.0,
            "score_details": {},
            "failure_reasons": [failure_reason],
            "latency_ms": 0,
            "token_usage": 0,
            "cost": 0.0,
            "passed": False,
            "events": [],
            "error": str(e)
        }


def _make_timeout_result(provider_name: str) -> dict:
    return {
        "provider": provider_name,
        "response": None,
        "score": 0.0,
        "score_details": {},
        "failure_reasons": [FailureReason.PROVIDER_TIMEOUT.value],
        "latency_ms": ITEM_TIMEOUT_SECONDS * 1000,
        "token_usage": 0,
        "cost": 0.0,
        "passed": False,
        "events": [],
        "error": "Benchmark item timed out"
    }


async def run_benchmark(
    db: Session,
    suite_id: uuid.UUID,
    user_id: uuid.UUID
) -> BenchmarkRun:

    suite = db.query(BenchmarkSuite).filter(
        BenchmarkSuite.id == suite_id
    ).first()

    if not suite:
        raise ValueError("Benchmark suite not found")

    # Use pinned prompt version when present; fall back for older suites
    if suite.prompt_version_id:
        prompt_version = db.query(PromptVersion).filter(
            PromptVersion.id == suite.prompt_version_id,
            PromptVersion.prompt_id == suite.prompt_id,
        ).first()
    else:
        prompt_version = db.query(PromptVersion).filter(
            PromptVersion.prompt_id == suite.prompt_id
        ).order_by(PromptVersion.version.desc()).first()

    if not prompt_version:
        raise ValueError("No prompt versions found")

    items = db.query(DatasetItem).filter(
        DatasetItem.dataset_id == suite.dataset_id
    ).all()

    if not items:
        raise ValueError("Dataset has no items")

    run = BenchmarkRun(
        suite_id=suite_id,
        status=BenchmarkRunStatus.running,
        total_cases=str(len(items) * len(suite.providers)),
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    logger.info("benchmark_started",
        suite_id=str(suite_id),
        prompt_version_id=str(prompt_version.id),
        total_cases=run.total_cases,
        providers=suite.providers
    )

    all_results = []
    total_latency = 0
    total_score = 0
    total_cost = 0
    passed = 0
    count = 0

    try:
        for item in items:
            full_prompt = build_benchmark_prompt(
                prompt_version.template,
                item.input_text,
            )

            group = EvaluationGroup(
                benchmark_run_id=run.id,
                dataset_item_id=item.id,
                prompt_version_id=prompt_version.id,
            )
            db.add(group)
            db.commit()
            db.refresh(group)

            provider_tasks = [
                _run_single_provider(
                    prompt=full_prompt,
                    provider_name=provider,
                    expected_output=item.expected_output,
                    check_json=item.check_json,
                    pass_threshold=suite.pass_threshold,
                    required_keywords=getattr(item, "required_keywords", None) or [],
                    required_json_fields=getattr(item, "required_json_fields", None) or [],
                    semantic_similarity_threshold=suite.semantic_similarity_threshold or 0.5,
                    keyword_coverage_threshold=suite.keyword_coverage_threshold or 0.5,
                    require_json=suite.json_validity_required or False,
                )
                for provider in suite.providers
            ]

            # Run all providers concurrently with a timeout ceiling
            try:
                provider_results = await asyncio.wait_for(
                    asyncio.gather(*provider_tasks),
                    timeout=ITEM_TIMEOUT_SECONDS
                )
            except asyncio.TimeoutError:
                logger.error("benchmark_item_timeout",
                    item=item.input_text[:100],
                    suite_id=str(suite_id)
                )
                provider_results = [
                    _make_timeout_result(p) for p in suite.providers
                ]

            # Compute comparison if multiple providers
            if len(provider_results) > 1:
                comparison_inputs = [
                    ProviderResult(
                        provider=r["provider"],
                        score=r["score"],
                        latency_ms=r["latency_ms"],
                        cost=r["cost"],
                        response=r["response"] or "",
                        passed=r["passed"]
                    )
                    for r in provider_results
                ]
                comparison = compute_comparison(comparison_inputs)

                group.divergence_score = comparison.divergence_score
                group.divergence_detected = comparison.divergence_detected
                group.review_required = comparison.review_required
                db.commit()
            else:
                comparison = None

            for r in provider_results:
                result_entry = {
                    "evaluation_group_id": str(group.id),
                    "provider": r["provider"],
                    "input": item.input_text,
                    "response": r["response"],
                    "score": r["score"],
                    "score_details": r["score_details"],
                    "failure_reasons": r["failure_reasons"],
                    "latency_ms": r["latency_ms"],
                    "token_usage": r["token_usage"],
                    "cost": r["cost"],
                    "passed": r["passed"],
                    "error": r["error"],
                }

                if comparison and len(provider_results) > 1:
                    result_entry["divergence_score"] = comparison.divergence_score
                    result_entry["divergence_detected"] = comparison.divergence_detected
                    result_entry["rankings"] = comparison.rankings

                all_results.append(result_entry)

                total_latency += r["latency_ms"]
                total_score += r["score"]
                total_cost += r["cost"]
                if r["passed"]:
                    passed += 1
                count += 1

                logger.info("benchmark_case_completed",
                    provider=r["provider"],
                    score=r["score"],
                    passed=r["passed"]
                )

        # Determine final status
        if passed == 0:
            final_status = BenchmarkRunStatus.failed
        elif passed < count:
            final_status = BenchmarkRunStatus.partially_completed
        else:
            final_status = BenchmarkRunStatus.completed

        run.status = final_status
        run.passed_cases = str(passed)
        run.avg_latency_ms = total_latency / count if count else 0
        run.avg_score = total_score / count if count else 0
        run.avg_cost = total_cost / count if count else 0
        run.results = all_results
        db.commit()
        db.refresh(run)

        trigger_webhook(db, user_id, "benchmark.completed", {
            "run_id": str(run.id),
            "status": str(final_status),
        })

        logger.info("benchmark_completed",
            run_id=str(run.id),
            avg_score=run.avg_score,
            pass_rate=f"{passed}/{count}",
            providers=suite.providers
        )

    except Exception as e:
        run.status = BenchmarkRunStatus.failed
        db.commit()
        logger.error("benchmark_failed", error=str(e))
        raise

    return run