from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from fastapi import status
from datetime import datetime

from app.database import get_db
from app.models.quiz import Quiz, QuizQuestion, QuizOption, QuizAttempt, QuizStatus
from app.auth.dependencies import get_current_admin
from app.models.user import User
from app.utils.audit import log_audit

router = APIRouter(prefix="/admin/quizzes", tags=["Admin - Quizzes"])


class QuizCreate(BaseModel):
    domain_id: int
    title: str
    description: Optional[str] = None
    time_limit_minutes: Optional[int] = None
    max_attempts: int = 1
    passing_score: float = 60.0
    total_marks: float = 100.0
    due_date: Optional[datetime] = None
    show_answers: bool = False
    show_explanations: bool = False


class QuestionCreate(BaseModel):
    question_text: str
    question_type: str = "single_choice"
    marks: float = 1.0
    explanation: Optional[str] = None
    order_index: int = 0
    options: List[dict]  # [{option_text, is_correct}]


@router.get("")
async def list_quizzes(
    domain_id: Optional[int] = Query(None),
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    query = db.query(Quiz)
    if domain_id:
        query = query.filter(Quiz.domain_id == domain_id)
    return [_format_quiz(q) for q in query.order_by(Quiz.created_at.desc()).all()]


@router.post("", status_code=201)
async def create_quiz(
    payload: QuizCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = Quiz(**payload.dict(), created_by=admin.id)
    db.add(quiz)
    db.commit()
    db.refresh(quiz)
    log_audit(db, "create_quiz", admin.id, admin.email, "quiz", quiz.id)
    return _format_quiz(quiz)


@router.get("/{quiz_id}")
async def get_quiz(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_404(quiz_id, db)
    result = _format_quiz(quiz)
    result["questions"] = [_format_question(q, include_correct=True) for q in quiz.questions]
    return result


@router.put("/{quiz_id}")
async def update_quiz(
    quiz_id: int,
    payload: QuizCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_404(quiz_id, db)
    for k, v in payload.dict(exclude_unset=True).items():
        setattr(quiz, k, v)
    db.commit()
    return _format_quiz(quiz)


@router.patch("/{quiz_id}/publish")
async def publish_quiz(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_404(quiz_id, db)
    quiz.is_published = True
    quiz.status = QuizStatus.published
    db.commit()
    return {"message": "Quiz published"}


@router.patch("/{quiz_id}/unpublish")
async def unpublish_quiz(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_404(quiz_id, db)
    quiz.is_published = False
    quiz.status = QuizStatus.draft
    db.commit()
    return {"message": "Quiz unpublished"}


def _validate_question_payload(payload: QuestionCreate):
    if payload.question_type not in {"single_choice", "multiple_choice"}:
        raise HTTPException(status_code=400, detail="Question type must be single_choice or multiple_choice")
    if not payload.question_text.strip():
        raise HTTPException(status_code=400, detail="Question text is required")
    if payload.marks <= 0:
        raise HTTPException(status_code=400, detail="Question marks must be greater than zero")
    if len(payload.options) < 2:
        raise HTTPException(status_code=400, detail="At least two options are required")
    correct_count = sum(1 for o in payload.options if o.get("is_correct", False))
    if correct_count < 1:
        raise HTTPException(status_code=400, detail="Select at least one correct answer")
    if payload.question_type == "single_choice" and correct_count != 1:
        raise HTTPException(status_code=400, detail="Single-choice questions must have exactly one correct answer")
    if any(not str(o.get("option_text", "")).strip() for o in payload.options):
        raise HTTPException(status_code=400, detail="Every option must have text")

def _sync_total_marks(quiz: Quiz):
    quiz.total_marks = sum(float(q.marks or 0) for q in quiz.questions)

@router.post("/{quiz_id}/questions", status_code=201)
async def add_question(
    quiz_id: int,
    payload: QuestionCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_404(quiz_id, db)
    _validate_question_payload(payload)
    question = QuizQuestion(
        quiz_id=quiz_id,
        question_text=payload.question_text,
        question_type=payload.question_type,
        marks=payload.marks,
        explanation=payload.explanation,
        order_index=payload.order_index,
    )
    db.add(question)
    db.flush()

    for i, opt in enumerate(payload.options):
        option = QuizOption(
            question_id=question.id,
            option_text=opt["option_text"],
            is_correct=opt.get("is_correct", False),
            order_index=i,
        )
        db.add(option)

    db.flush()
    _sync_total_marks(quiz)
    db.commit()
    db.refresh(question)
    return _format_question(question, include_correct=True)


@router.put("/{quiz_id}/questions/{question_id}")
async def update_question(
    quiz_id: int,
    question_id: int,
    payload: QuestionCreate,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(QuizQuestion).filter(QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    _validate_question_payload(payload)

    q.question_text = payload.question_text
    q.question_type = payload.question_type
    q.marks = payload.marks
    q.explanation = payload.explanation
    q.order_index = payload.order_index

    # Replace options
    for opt in q.options:
        db.delete(opt)
    db.flush()

    for i, opt in enumerate(payload.options):
        option = QuizOption(question_id=q.id, option_text=opt["option_text"],
                            is_correct=opt.get("is_correct", False), order_index=i)
        db.add(option)

    db.flush()
    _sync_total_marks(q.quiz)
    db.commit()
    db.refresh(q)
    return _format_question(q, include_correct=True)


@router.delete("/{quiz_id}/questions/{question_id}")
async def delete_question(
    quiz_id: int,
    question_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    q = db.query(QuizQuestion).filter(QuizQuestion.id == question_id, QuizQuestion.quiz_id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Question not found")
    quiz = q.quiz
    db.delete(q)
    db.flush()
    _sync_total_marks(quiz)
    db.commit()
    return {"message": "Question deleted"}


@router.get("/{quiz_id}/attempts")
async def get_quiz_attempts(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    attempts = db.query(QuizAttempt).filter(QuizAttempt.quiz_id == quiz_id).all()
    return [_format_attempt(a) for a in attempts]


@router.delete("/{quiz_id}")
async def delete_quiz(
    quiz_id: int,
    admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_404(quiz_id, db)
    db.delete(quiz)
    db.commit()
    return {"message": "Quiz deleted"}


def _get_quiz_or_404(quiz_id: int, db: Session) -> Quiz:
    q = db.query(Quiz).filter(Quiz.id == quiz_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quiz not found")
    return q


def _format_quiz(q: Quiz) -> dict:
    return {
        "id": q.id, "domain_id": q.domain_id, "title": q.title,
        "description": q.description, "time_limit_minutes": q.time_limit_minutes,
        "max_attempts": q.max_attempts, "passing_score": float(q.passing_score),
        "total_marks": float(q.total_marks), "due_date": q.due_date, "is_published": q.is_published,
        "show_answers": q.show_answers, "show_explanations": q.show_explanations,
        "status": q.status, "question_count": len(q.questions),
        "created_at": q.created_at,
    }


def _format_question(q: QuizQuestion, include_correct: bool = False) -> dict:
    return {
        "id": q.id, "question_text": q.question_text, "question_type": q.question_type,
        "marks": float(q.marks), "explanation": q.explanation, "order_index": q.order_index,
        "options": [
            {"id": o.id, "option_text": o.option_text,
             **({"is_correct": o.is_correct} if include_correct else {}),
             "order_index": o.order_index}
            for o in q.options
        ],
    }


def _format_attempt(a: QuizAttempt) -> dict:
    return {
        "id": a.id, "quiz_id": a.quiz_id, "student_id": a.student_id,
        "attempt_number": a.attempt_number, "started_at": a.started_at,
        "submitted_at": a.submitted_at, "score": float(a.score) if a.score else None,
        "percentage": float(a.percentage) if a.percentage else None,
        "is_passed": a.is_passed, "status": a.status,
    }
