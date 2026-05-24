from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class PromptCreate(BaseModel):
    name: str
    description: Optional[str] = None

class PromptVersionCreate(BaseModel):
    template: str

class PromptVersionResponse(BaseModel):
    id: UUID
    prompt_id: UUID
    version: int
    template: str
    created_at: datetime

    class Config:
        from_attributes = True

class PromptResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class PlaygroundRequest(BaseModel):
    prompt: str 
    provider: str = "gemini"
    expected_output: Optional[str] = None 
    check_json: bool = False
