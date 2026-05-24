import structlog 
from typing import List 
from dataclasses import dataclass
import numpy as np
from app.services.scoring import get_embedding

logger = structlog.get_logger()

DIVERGENCE_THRESHOLD = 0.6

@dataclass 
class ProviderResult: 
    provider: str 
    score: float 
    latency_ms: int 
    cost: float 
    response: str 
    passed: bool 

@dataclass 
class ComparisonResult: 
    provider_results: List[ProviderResult]
    divergence_score: float
    divergence_detected: bool
    review_required: bool
    best_provider: str 
    rankings: List[dict]
    summary: dict 

def compute_comparison(results: List[ProviderResult]) -> ComparisonResult:
    if not results: 
        raise ValueError("No results to compare")
    
    if len(results) == 1: 
        r = results[0]
        return ComparisonResult(
            provider_results=results,
            divergence_score=0.0,
            divergence_detected=False,
            review_required=False,
            best_provider=r.provider,
            rankings=[{
                "provider": r.provider,
                "score": r.score,
                "latency_ms": r.latency_ms,
                "cost": r.cost,
                "passed": r.passed,
                "rank": 1
            }],
            summary={
                "total_providers": 1,
                "passed_providers": 1 if r.passed else 0,
                "avg_score": r.score,
                "avg_latency_ms": r.latency_ms,
                "avg_cost": r.cost, 
            }
        )
    
    # compute divergence using semantic similarity between responses
    divergence_score = _compute_divergence(results)
    divergence_detected = divergence_score >= DIVERGENCE_THRESHOLD

    # rank providers by score 
    ranked = sorted(results, key=lambda x: x.score, reverse=True)
    rankings = [
        {
            "provider": r.provider,
            "score": r.score,
            "latency_ms": r.latency_ms,
            "cost": r.cost,
            "passed": r.passed,
            "rank": i + 1
        }
        for i, r in enumerate(ranked)
    ]

    best_provider = ranked[0].provider
    passed_count = sum(1 for r in results if r.passed)
    avg_score = sum(r.score for r in results) / len(results)
    avg_latency = sum(r.latency_ms for r in results) / len(results)
    avg_cost = sum(r.cost for r in results) / len(results)

    review_required = divergence_detected or passed_count == 0

    logger.info("comparison_computed",
        providers=[r.provider for r in results],
        divergence_score=divergence_score,
        divergence_detected=divergence_detected,
        best_provider=best_provider,
    )

    return ComparisonResult(
        provider_results=results,
        divergence_score=divergence_score,
        divergence_detected=divergence_detected,
        review_required=review_required,
        best_provider=best_provider,
        rankings=rankings,
        summary={
            "total_providers": len(results),
            "passed_providers": passed_count,
            "avg_score": avg_score,
            "avg_latency_ms": avg_latency,
            "avg_cost": avg_cost,
        }
    )

def _compute_divergence(results: List[ProviderResult]) -> float:
    try:
        responses = [r.response for r in results if r.response]

        if len(responses) < 2:
            return 0.0
        
        embeddings = [get_embedding(response) for response in responses]
        embeddings = [embedding for embedding in embeddings if embedding is not None]

        if len(embeddings) < 2:
            return 0.0

        similarities = []
        for i in range(len(embeddings)):
            for j in range(i + 1, len(embeddings)):
                a = np.array(embeddings[i])
                b = np.array(embeddings[j])
                similarity = float(
                    np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
                )
                similarities.append(max(0.0, similarity))
        
        avg_similarity = sum(similarities) / len(similarities)
        return 1.0 - avg_similarity
    
    except Exception as e:
        logger.error("divergence_computation_failed", error=str(e))
        return 0.0
