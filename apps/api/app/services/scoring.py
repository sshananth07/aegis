import json 
import re
import httpx
import numpy as np
import hashlib
import structlog 
from app.core.config import settings
from app.core.cache import cache_get, cache_set
from dataclasses import dataclass 
from enum import Enum
from typing import Optional 

logger = structlog.get_logger()

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"

def get_embedding(text: str) -> Optional[list]:
    cache_key = f"embedding:{hashlib.md5(text.encode()).hexdigest()}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    api_key = settings.gemini_api_key

    if api_key:
        try:
            with httpx.Client() as client:
                res = client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:embedContent",
                    headers={"x-goog-api-key": api_key},
                    json={
                        "model": f"models/{GEMINI_EMBEDDING_MODEL}",
                        "content": {"parts": [{"text": text}]}
                    },
                    timeout=30.0
                )
                res.raise_for_status()
                result = res.json()["embedding"]["values"]
                if result:
                    cache_set(cache_key, result, ttl_seconds=3600)
                return result
        except Exception as e:
            logger.warning("gemini_embedding_failed", error=str(e))

    if not settings.ollama_enabled:
        return None

    try:
        with httpx.Client() as client:
            res = client.post(
                f"{settings.ollama_host}/api/embed",
                json={
                    "model": settings.ollama_embedding_model,
                    "input": text,
                },
                timeout=30.0
            )
            res.raise_for_status()
            data = res.json()
            if "embeddings" in data:
                embeddings = data["embeddings"]
                result = embeddings[0] if embeddings else None
            else:
                result = data.get("embedding")
                
            if result:
                cache_set(cache_key, result, ttl_seconds=3600)
            return result
    except Exception as e:
        logger.warning("ollama_embedding_failed", error=str(e))

    return None 


class FailureReason(str, Enum):
    LOW_SEMANTIC_SIMILARITY = "low_semantic_similarity"
    INVALID_JSON = "invalid_json"
    MISSING_REQUIRED_FIELDS = "missing_required_fields"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_ERROR = "provider_error"
    RETRY_EXHAUSTED = "retry_exhausted"
    DIVERGENCE_DETECTED = "divergence_detected"
    POLICY_VIOLATION = "policy_violation"
    LOW_KEYWORD_COVERAGE = "low_keyword_coverage"


@dataclass 
class ScoreResult:
    overall: float 
    exact_match: Optional[float]
    json_validity: Optional[float]
    semantic_similarity: Optional[float]
    structure_score: float
    keyword_coverage: float
    policy_compliance: float
    validation_passed: bool
    failure_reasons: list[str]
    details: dict 

def normalize_text(value: str) -> str:
    normalized = value.strip()
    if len(normalized) >= 2 and normalized[0] == normalized[-1] and normalized[0] in ("'", '"'):
        normalized = normalized[1:-1].strip()
    return re.sub(r"\s+", " ", normalized).lower()


def score_exact_match(response: str, expected: str) -> float: 
    return 1.0 if normalize_text(response) == normalize_text(expected) else 0.0

def score_json_validity(response: str) -> float: 
    # extract JSON from response if wrapped in markdown 
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response)
    if json_match: 
        candidate = json_match.group(1).strip()
    else:
        candidate = response.strip()
    
    try: 
        json.loads(candidate)
        return 1.0 
    except json.JSONDecodeError:
        return 0.0


def parse_json_response(response: str) -> Optional[dict]:
    json_match = re.search(r"```json\s*(\{.*?\})\s*```", response, re.DOTALL)
    candidate = json_match.group(1).strip() if json_match else response.strip()

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None

def score_semantic_similarity(response: str, expected: str) -> float: 
    try:
        emb1 = get_embedding(response)
        emb2 = get_embedding(expected)

        if emb1 is None or emb2 is None:
            return 0.0

        a = np.array(emb1)
        b = np.array(emb2)
        similarity = float(
            np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        )
        return max(0.0, similarity)
    except Exception as e: 
        logger.warning("semantic_similarity_failed", error=str(e))
        return 0.0


def score_keyword_coverage(response: str, required_keywords: list[str]) -> float:
    if not required_keywords:
        return 1.0

    normalized_response = normalize_text(response)
    matched = sum(
        1 for keyword in required_keywords
        if normalize_text(keyword) in normalized_response
    )
    return matched / len(required_keywords)


def score_structure(
    response: str,
    require_json: bool,
    required_json_fields: list[str],
) -> tuple[float, Optional[float], list[str], list[str]]:
    failure_reasons = []
    missing_fields = []

    if not require_json and not required_json_fields:
        return 1.0, None, missing_fields, failure_reasons

    parsed = parse_json_response(response)
    if parsed is None:
        failure_reasons.append(FailureReason.INVALID_JSON.value)
        return 0.0, 0.0, required_json_fields, failure_reasons

    if not required_json_fields:
        return 1.0, 1.0, missing_fields, failure_reasons

    normalized_fields = [str(field) for field in required_json_fields]
    missing_fields = [field for field in normalized_fields if field not in parsed]
    present_count = len(normalized_fields) - len(missing_fields)
    structure_score = present_count / len(normalized_fields)

    if missing_fields:
        failure_reasons.extend([
            FailureReason.MISSING_REQUIRED_FIELDS.value,
            FailureReason.SCHEMA_VALIDATION_FAILED.value,
        ])

    return structure_score, 1.0, missing_fields, failure_reasons

def compute_score(
        response: str,
        expected_output: Optional[str] = None,
        check_json: bool = False,
        required_keywords: Optional[list[str]] = None,
        required_json_fields: Optional[list[str]] = None,
        require_json: bool = False,
        semantic_similarity_threshold: float = 0.7,
        keyword_coverage_threshold: float = 0.6,
) -> ScoreResult:
    required_keywords = required_keywords or []
    required_json_fields = required_json_fields or []
    details = {}
    failure_reasons = []

    structure_score, json_score, missing_fields, structure_failures = score_structure(
        response=response,
        require_json=check_json or require_json,
        required_json_fields=required_json_fields,
    )
    failure_reasons.extend(structure_failures)
    details["json_validity"] = json_score
    details["structure_score"] = structure_score
    details["missing_required_fields"] = missing_fields
    
    # Text quality check. Exact match is a perfect text score; otherwise use
    # semantic similarity for open-ended expected outputs.
    semantic_similarity = None
    if expected_output:
        exact = score_exact_match(response, expected_output)
        details["exact_match"] = exact
        semantic = score_semantic_similarity(response, expected_output)
        details["semantic_similarity"] = semantic
        semantic_similarity = semantic
        semantic_component = max(exact, semantic)
        if semantic_component < semantic_similarity_threshold:
            failure_reasons.append(FailureReason.LOW_SEMANTIC_SIMILARITY.value)
    else:
        details["exact_match"] = None
        details["semantic_similarity"] = None
        semantic_component = 0.5

    keyword_coverage = score_keyword_coverage(response, required_keywords)
    details["keyword_coverage"] = keyword_coverage
    details["required_keywords"] = required_keywords

    if required_keywords and keyword_coverage < keyword_coverage_threshold:
        failure_reasons.append(FailureReason.LOW_KEYWORD_COVERAGE.value)

    policy_compliance = 1.0
    details["policy_compliance"] = policy_compliance
    
    if semantic_similarity is not None:
        final_score = (
            semantic_component * 0.7 +
            structure_score * 0.1 +
            keyword_coverage * 0.1 +
            policy_compliance * 0.1
        )
    else:
        final_score = (
            structure_score * 0.4 +
            keyword_coverage * 0.4 +
            policy_compliance * 0.2
        )
        
    details["final_score"] = final_score
    details["failure_reasons"] = failure_reasons
    validation_passed = not failure_reasons

    logger.info("scoring_completed",
        overall=final_score,
        checks=list(details.keys())
    )

    return ScoreResult(
        overall=final_score,
        exact_match=details["exact_match"],
        json_validity=details["json_validity"],
        semantic_similarity=details["semantic_similarity"],
        structure_score=structure_score,
        keyword_coverage=keyword_coverage,
        policy_compliance=policy_compliance,
        validation_passed=validation_passed,
        failure_reasons=failure_reasons,
        details=details 
    )
