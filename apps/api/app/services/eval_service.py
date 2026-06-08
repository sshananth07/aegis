import uuid
import structlog
from sqlalchemy.orm import Session
from app.models.evaluation import Evaluation, Trace
from app.models.prompt import PromptVersion
from app.providers.router import ProviderRouter
from app.services.scoring import compute_score
from app.services.webhook_service import trigger_webhook
from app.core.enums import EvaluationStatus
from app.core.cache import cache_clear_prefix

logger = structlog.get_logger()

async def run_evaluation(
    db: Session,
    prompt_version_id: uuid.UUID,
    provider_name: str,
    user_id: uuid.UUID,
    expected_output: str = None,
    check_json: bool = False,
) -> Evaluation:

    prompt_version = db.query(PromptVersion).filter(
        PromptVersion.id == prompt_version_id
    ).first()

    if not prompt_version:
        raise ValueError("Prompt version not found")

    evaluation = Evaluation(
        prompt_version_id=prompt_version_id,
        provider=provider_name,
        status=EvaluationStatus.queued,
        created_by=user_id
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    def log_trace(event_type: str, provider: str, latency_ms=None, metadata=None):
        trace = Trace(
            evaluation_id=evaluation.id,
            event_type=event_type,
            provider=provider,
            latency_ms=latency_ms,
            metadata_=metadata or {}
        )
        db.add(trace)
        db.commit()

    log_trace("evaluation_created", provider_name)

    # Transition to running
    evaluation.status = EvaluationStatus.running
    db.commit()

    try:
        router = ProviderRouter(provider_name)
        result, events = await router.route(prompt_version.template)

        for event in events:
            log_trace(
                event_type=event["event_type"],
                provider=event["provider"],
                latency_ms=event.get("latency_ms"),
                metadata={k: v for k, v in event.items()
                          if k not in ("event_type", "provider", "latency_ms")}
            )

        score_result = compute_score(
            response=result.content,
            expected_output=expected_output,
            check_json=check_json,
        )

        log_trace("scoring_completed", result.provider,
                  metadata=score_result.details)

        # Check if review required
        final_status = EvaluationStatus.completed
        score_details = score_result.details 
        semantic_sim = score_details.get("semantic_similarity") if score_details else None 
        low_semantic = semantic_sim is not None and semantic_sim < 0.3

        if score_result.overall < 0.5 or low_semantic:
            final_status = EvaluationStatus.review_required
            log_trace("review_triggered", result.provider,
                      metadata={
                          "reason": "low_score" if not low_semantic else "low_semantic_similarity",
                          "score": score_result.overall,
                          "semantic_similarity": semantic_sim
                        })

        evaluation.response = result.content
        evaluation.status = final_status
        evaluation.latency_ms = result.latency_ms
        evaluation.token_usage = result.token_usage
        evaluation.token_usage_estimated = result.token_usage_estimated
        evaluation.cost = result.cost
        evaluation.provider = result.provider
        evaluation.score = score_result.overall
        evaluation.score_details = score_result.details
        db.commit()
        db.refresh(evaluation)

        cache_clear_prefix("metrics:")
        cache_clear_prefix("analytics:")

        logger.info("evaluation_completed",
            evaluation_id=str(evaluation.id),
            provider=result.provider,
            status=final_status,
            score=score_result.overall,
        )

        logger.info("debug_score", overall=score_result.overall, details=score_result.details)

        trigger_webhook(db, evaluation.created_by, "evaluation.completed", {
            "evaluation_id": str(evaluation.id),
            "status": evaluation.status,
            "score": evaluation.score,
            "provider": evaluation.provider,
        })

    except Exception as e:
        evaluation.status = EvaluationStatus.failed
        db.commit()
        cache_clear_prefix("metrics:")
        cache_clear_prefix("analytics:")
        log_trace("evaluation_failed", provider_name,
                  metadata={"error": str(e)})
        logger.error("evaluation_failed", error=str(e))

        trigger_webhook(db, evaluation.created_by, "evaluation.completed", {
            "evaluation_id": str(evaluation.id),
            "status": EvaluationStatus.failed,
            "score": None,
            "provider": provider_name,
        })

        raise

    return evaluation