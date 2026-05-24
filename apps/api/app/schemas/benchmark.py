from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional, List

class DatasetItemCreate(BaseModel):
    input_text: str
    expected_output: Optional[str] = None
    check_json: bool = False
    required_keywords: List[str] = Field(default_factory=list)
    required_json_fields: List[str] = Field(default_factory=list)

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
