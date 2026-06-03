from pydantic import BaseModel, Field, validator
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class DatasetItemCreate(BaseModel):
    input_text: str
    expected_output: Optional[str] = None
    check_json: bool = False
    required_keywords: List[str] = Field(default_factory=list)
    required_json_fields: List[str] = Field(default_factory=list)

    @validator("input_text")
    def sanitize_input_text(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Input text cannot be empty")
        if len(v) > 2000:
            raise ValueError("Input text too long (max 2000 characters)")
        return v

    @validator("expected_output")
    def sanitize_expected_output(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 5000:
            raise ValueError("Expected output too long (max 5000 characters)")
        return v if v else None

    @validator("required_keywords", "required_json_fields", each_item=True)
    def sanitize_list_items(cls, v):
        if len(v) > 100:
            raise ValueError("Keyword/field too long (max 100 characters)")
        return v.strip()


class DatasetItemResponse(BaseModel):
    id: UUID
    dataset_id: UUID
    input_text: str
    expected_output: Optional[str]
    check_json: bool
    required_keywords: list
    required_json_fields: list
    created_at: datetime

    class Config:
        from_attributes = True


class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    items: List[DatasetItemCreate] = Field(default_factory=list)

    @validator("name")
    def sanitize_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name cannot be empty")
        if len(v) > 200:
            raise ValueError("Name too long (max 200 characters)")
        return v

    @validator("description")
    def sanitize_description(cls, v):
        if v is None:
            return v
        v = v.strip()
        if len(v) > 1000:
            raise ValueError("Description too long (max 1000 characters)")
        return v if v else None

    @validator("items")
    def validate_items(cls, v):
        if len(v) > 500:
            raise ValueError("Too many items (max 500 per dataset)")
        return v


class DatasetResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime
    items: List[DatasetItemResponse] = []

    class Config:
        from_attributes = True


class BenchmarkSuiteCreate(BaseModel):
    name: str
    description: Optional[str] = None
    prompt_id: UUID
    prompt_version_id: Optional[UUID] = None
    dataset_id: UUID
    providers: List[str]
    pass_threshold: float = 0.7
    semantic_similarity_threshold: float = 0.7
    keyword_coverage_threshold: float = 0.6
    json_validity_required: bool = False

    @validator("providers")
    def validate_providers(cls, v):
        allowed = {"gemini", "ollama"}
        for p in v:
            if p not in allowed:
                raise ValueError(f"Unknown provider: {p}")
        if len(v) == 0:
            raise ValueError("At least one provider required")
        return v

    @validator("pass_threshold", "semantic_similarity_threshold", "keyword_coverage_threshold")
    def validate_thresholds(cls, v):
        if not 0.0 <= v <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")
        return v


class BenchmarkSuiteResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    prompt_id: UUID
    prompt_version_id: Optional[UUID]
    dataset_id: UUID
    providers: list
    pass_threshold: float
    semantic_similarity_threshold: float
    keyword_coverage_threshold: float
    json_validity_required: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BenchmarkRunResponse(BaseModel):
    id: UUID
    suite_id: UUID
    status: str
    total_cases: str
    passed_cases: str
    avg_latency_ms: Optional[float]
    avg_score: Optional[float]
    avg_cost: Optional[float]
    results: Optional[list]
    created_at: datetime

    class Config:
        from_attributes = True
