import uuid
import structlog
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.review import Review
from app.models.evaluation import Evaluation, Trace
from app.schemas.review import ReviewAction, ReviewResponse
from app.core.enums import EvaluationStatus
from app.core.auth import get_user_id

logger = structlog.get_logger()

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.get("/queue", response_model=list[ReviewResponse])
def get_review_queue(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    # Return all evaluations flagged for review that have no review yet
    flagged = db.query(Evaluation).filter(
        Evaluation.status == EvaluationStatus.review_required,
        Evaluation.created_by == uuid.UUID(user_id)
    ).all()

    queue = []
    for evaluation in flagged:
        existing = db.query(Review).filter(
            Review.evaluation_id == evaluation.id
        ).first()
        if not existing:
            # Auto-create a pending review entry
            review = Review(
                evaluation_id=evaluation.id,
                reviewer_id=uuid.UUID(user_id),
                status="pending"
            )
            db.add(review)
            db.commit()
            db.refresh(review)
            queue.append(review)
        else:
            if existing.status == "pending":
                queue.append(existing)

    return queue

@router.post("/{review_id}", response_model=ReviewResponse)
def submit_review(
    review_id: uuid.UUID,
    action: ReviewAction,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    if action.status not in ("approved", "rejected"):
        raise HTTPException(
            status_code=400,
            detail="Status must be 'approved' or 'rejected'"
        )

    review = db.query(Review).filter(Review.id == review_id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")

    if review.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"Review already {review.status}"
        )

    # Update review
    review.status = action.status
    review.comment = action.comment
    review.reviewer_id = uuid.UUID(user_id)
    db.commit()

    # Update evaluation status based on review decision
    evaluation = db.query(Evaluation).filter(
        Evaluation.id == review.evaluation_id
    ).first()

    if evaluation:
        if action.status == "approved":
            evaluation.status = EvaluationStatus.completed
        else:
            evaluation.status = EvaluationStatus.failed

        # Log trace
        trace = Trace(
            evaluation_id=evaluation.id,
            event_type="review_completed",
            provider=evaluation.provider,
            metadata_={
                "review_status": action.status,
                "comment": action.comment,
                "reviewer_id": user_id
            }
        )
        db.add(trace)
        db.commit()

        logger.info("review_completed",
            evaluation_id=str(evaluation.id),
            review_status=action.status
        )

    db.refresh(review)
    return review

@router.get("/{evaluation_id}/review", response_model=ReviewResponse)
def get_review(
    evaluation_id: uuid.UUID,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_user_id)
):
    review = db.query(Review).filter(
        Review.evaluation_id == evaluation_id
    ).first()
    if not review:
        raise HTTPException(status_code=404, detail="No review found")
    return review