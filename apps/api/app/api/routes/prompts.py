import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.prompt import Prompt, PromptVersion
from app.schemas.prompt import (
    PromptCreate, PromptVersionCreate,
    PromptResponse, PromptVersionResponse,
    PlaygroundRequest
)
from app.schemas.evaluation import EvaluationResponse
from app.services.eval_service import run_evaluation
from app.core.auth import get_user_id

router = APIRouter(prefix="/prompts", tags=["prompts"])

@router.post("/", response_model=PromptResponse)
def create_prompt(
    data: PromptCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    prompt = Prompt(
        name=data.name,
        description=data.description,
        created_by=uuid.UUID(user_id)
    )
    db.add(prompt)
    db.commit()
    db.refresh(prompt)
    return prompt

@router.get("/", response_model=list[PromptResponse])
def list_prompts(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    return db.query(Prompt).filter(
        Prompt.created_by == uuid.UUID(user_id)
    ).all()

@router.post("/{prompt_id}/versions", response_model=PromptVersionResponse)
def create_version(
    prompt_id: uuid.UUID,
    data: PromptVersionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.created_by == uuid.UUID(user_id)
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")

    last = db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id
    ).order_by(PromptVersion.version.desc()).first()

    version_num = (last.version + 1) if last else 1
    version = PromptVersion(
        prompt_id=prompt_id,
        version=version_num,
        template=data.template
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version

@router.get("/{prompt_id}/versions", response_model=list[PromptVersionResponse])
def list_versions(
    prompt_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    prompt = db.query(Prompt).filter(
        Prompt.id == prompt_id,
        Prompt.created_by == uuid.UUID(user_id)
    ).first()
    if not prompt:
        raise HTTPException(status_code=404, detail="Prompt not found")
    return db.query(PromptVersion).filter(
        PromptVersion.prompt_id == prompt_id
    ).all()

@router.post("/playground", response_model=EvaluationResponse)
async def playground(
    data: PlaygroundRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    temp_prompt = Prompt(
        name="Playground",
        description="Ad-hoc playground evaluation",
        created_by=uuid.UUID(user_id)
    )
    db.add(temp_prompt)
    db.commit()
    db.refresh(temp_prompt)

    temp_version = PromptVersion(
        prompt_id=temp_prompt.id,
        version=1,
        template=data.prompt
    )
    db.add(temp_version)
    db.commit()
    db.refresh(temp_version)

    evaluation = await run_evaluation(
        db=db,
        prompt_version_id=temp_version.id,
        provider_name=data.provider,
        user_id=uuid.UUID(user_id),
        expected_output=data.expected_output,
        check_json=data.check_json,
    )
    return evaluation
