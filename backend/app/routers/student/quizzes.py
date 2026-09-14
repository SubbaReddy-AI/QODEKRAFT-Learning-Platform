from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app.database import get_db
from app.models.quiz import Quiz, QuizQuestion, QuizOption, QuizAttempt, QuizAnswer, AttemptStatus
from app.models.domain import StudentDomain
from app.auth.dependencies import get_current_approved_student, verify_student_domain_access
from app.models.user import User
from app.utils.audit import create_notification

quiz_router = APIRouter(prefix="/student/quizzes", tags=["Student - Quizzes"])


@quiz_router.get("")
async def list_quizzes(
    domain_id: int = Query(...),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    if not verify_student_domain_access(student, domain_id, db):
        raise HTTPException(status_code=403, detail="No access to this domain")

    quizzes = db.query(Quiz).filter(
        Quiz.domain_id == domain_id,
        Quiz.is_published == True,
    ).all()

    result = []
    for quiz in quizzes:
        attempts = db.query(QuizAttempt).filter(
            QuizAttempt.quiz_id == quiz.id,
            QuizAttempt.student_id == student.id,
        ).all()
        best = max((a.percentage for a in attempts if a.percentage), default=None)
        result.append({
            "id": quiz.id, "title": quiz.title, "description": quiz.description,
            "time_limit_minutes": quiz.time_limit_minutes,
            "max_attempts": quiz.max_attempts,
            "passing_score": float(quiz.passing_score),
            "total_marks": float(quiz.total_marks),
            "due_date": quiz.due_date,
            "attempt_count": len(attempts),
            "best_percentage": float(best) if best else None,
            "can_attempt": len(attempts) < quiz.max_attempts,
        })
    return result


@quiz_router.post("/{quiz_id}/start")
async def start_quiz(
    quiz_id: int,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_403(quiz_id, student, db)
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student.id
    ).count()

    if attempts >= quiz.max_attempts:
        raise HTTPException(status_code=400, detail="Maximum attempt limit reached")

    if quiz.due_date and datetime.utcnow() > quiz.due_date:
        raise HTTPException(status_code=400, detail="This quiz deadline has passed")

    attempt = QuizAttempt(
        quiz_id=quiz_id,
        student_id=student.id,
        attempt_number=attempts + 1,
        status=AttemptStatus.in_progress,
    )
    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    # Return questions without revealing correct answers
    questions = [
        {
            "id": q.id, "question_text": q.question_text,
            "question_type": q.question_type, "marks": float(q.marks),
            "order_index": q.order_index,
            "options": [
                {"id": o.id, "option_text": o.option_text, "order_index": o.order_index}
                for o in q.options
            ],
        }
        for q in sorted(quiz.questions, key=lambda x: x.order_index)
    ]

    return {
        "attempt_id": attempt.id,
        "quiz_id": quiz_id,
        "attempt_number": attempt.attempt_number,
        "time_limit_minutes": quiz.time_limit_minutes,
        "started_at": attempt.started_at,
        "questions": questions,
    }


@quiz_router.post("/{quiz_id}/attempts/{attempt_id}/submit")
async def submit_quiz(
    quiz_id: int,
    attempt_id: int,
    answers: List[dict],  # [{question_id, selected_option_ids: []}]
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    quiz = _get_quiz_or_403(quiz_id, student, db)
    attempt = db.query(QuizAttempt).filter(
        QuizAttempt.id == attempt_id,
        QuizAttempt.student_id == student.id,
        QuizAttempt.quiz_id == quiz_id,
        QuizAttempt.status == AttemptStatus.in_progress,
    ).first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Active attempt not found")

    total_score = 0.0
    for answer_data in answers:
        q_id = answer_data.get("question_id")
        selected_ids = answer_data.get("selected_option_ids", [])

        question = db.query(QuizQuestion).filter(QuizQuestion.id == q_id, QuizQuestion.quiz_id == quiz_id).first()
        if not question:
            continue

        correct_ids = {o.id for o in question.options if o.is_correct}
        selected_set = set(selected_ids)
        is_correct = selected_set == correct_ids
        marks = float(question.marks) if is_correct else 0.0
        total_score += marks

        qa = QuizAnswer(
            attempt_id=attempt_id, question_id=q_id,
            selected_option_ids=selected_ids, is_correct=is_correct,
            marks_obtained=marks,
        )
        db.add(qa)

    total_marks = float(quiz.total_marks)
    percentage = (total_score / total_marks * 100) if total_marks > 0 else 0.0
    is_passed = percentage >= float(quiz.passing_score)

    attempt.score = total_score
    attempt.percentage = percentage
    attempt.is_passed = is_passed
    attempt.status = AttemptStatus.submitted
    attempt.submitted_at = datetime.utcnow()
    if attempt.started_at:
        attempt.time_taken_seconds = int((datetime.utcnow() - attempt.started_at).total_seconds())

    db.commit()

    create_notification(db, student.id, "Quiz Submitted",
                        f"Your quiz has been submitted. Score: {total_score:.1f}/{total_marks:.1f} ({percentage:.1f}%)",
                        "quiz", "quiz", quiz_id)

    result = {
        "score": total_score, "total_marks": total_marks,
        "percentage": percentage, "is_passed": is_passed,
    }
    if quiz.show_answers:
        result["answers"] = []
        for qa in db.query(QuizAnswer).filter(QuizAnswer.attempt_id == attempt_id).all():
            q = db.query(QuizQuestion).filter(QuizQuestion.id == qa.question_id).first()
            result["answers"].append({
                "question_id": qa.question_id,
                "is_correct": qa.is_correct,
                "marks_obtained": float(qa.marks_obtained),
                "explanation": q.explanation if quiz.show_explanations and q else None,
            })

    return result


@quiz_router.get("/{quiz_id}/attempts")
async def get_my_attempts(
    quiz_id: int,
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    attempts = db.query(QuizAttempt).filter(
        QuizAttempt.quiz_id == quiz_id, QuizAttempt.student_id == student.id
    ).order_by(QuizAttempt.created_at.desc()).all()
    return [
        {
            "id": a.id, "attempt_number": a.attempt_number,
            "score": float(a.score) if a.score else None,
            "percentage": float(a.percentage) if a.percentage else None,
            "is_passed": a.is_passed, "status": a.status,
            "started_at": a.started_at, "submitted_at": a.submitted_at,
        }
        for a in attempts
    ]


def _get_quiz_or_403(quiz_id: int, student: User, db: Session) -> Quiz:
    quiz = db.query(Quiz).filter(Quiz.id == quiz_id, Quiz.is_published == True).first()
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
    if not verify_student_domain_access(student, quiz.domain_id, db):
        raise HTTPException(status_code=403, detail="No access to this domain")
    return quiz


# ─── Student Assignments ─────────────────────────────────────

assignment_router = APIRouter(prefix="/student/assignments", tags=["Student - Assignments"])


@assignment_router.get("")
async def list_assignments(
    domain_id: int = Query(...),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    if not verify_student_domain_access(student, domain_id, db):
        raise HTTPException(status_code=403, detail="No access to this domain")

    from app.models.assignment import Assignment, AssignmentSubmission
    assignments = db.query(Assignment).filter(
        Assignment.domain_id == domain_id, Assignment.is_published == True
    ).order_by(Assignment.due_date.asc()).all()

    result = []
    for a in assignments:
        submission = db.query(AssignmentSubmission).filter(
            AssignmentSubmission.assignment_id == a.id,
            AssignmentSubmission.student_id == student.id,
        ).order_by(AssignmentSubmission.submitted_at.desc()).first()
        result.append({
            "id": a.id, "title": a.title, "description": a.description,
            "topic": a.topic, "due_date": a.due_date,
            "max_marks": float(a.max_marks),
            "allowed_extensions": a.allowed_extensions,
            "submission": {
                "status": submission.status if submission else "not_submitted",
                "marks_obtained": float(submission.marks_obtained) if submission and submission.marks_obtained else None,
                "submitted_at": submission.submitted_at if submission else None,
            } if submission else None,
        })
    return result


@assignment_router.post("/{assignment_id}/submit", status_code=201)
async def submit_assignment(
    assignment_id: int,
    files: List[UploadFile] = File(...),
    student: User = Depends(get_current_approved_student),
    db: Session = Depends(get_db),
):
    from app.models.assignment import Assignment, AssignmentSubmission, AssignmentSubmissionFile, SubmissionStatus
    from app.utils.file_handler import save_upload_file
    from app.config import settings

    assignment = db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.is_published == True
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if not verify_student_domain_access(student, assignment.domain_id, db):
        raise HTTPException(status_code=403, detail="No access to this domain")

    # Find previous submission number
    prev = db.query(AssignmentSubmission).filter(
        AssignmentSubmission.assignment_id == assignment_id,
        AssignmentSubmission.student_id == student.id,
    ).count()

    is_late = assignment.due_date and datetime.utcnow() > assignment.due_date
    sub_status = SubmissionStatus.resubmitted if prev > 0 else (SubmissionStatus.late if is_late else SubmissionStatus.submitted)

    submission = AssignmentSubmission(
        assignment_id=assignment_id,
        student_id=student.id,
        submission_number=prev + 1,
        status=sub_status,
        is_late=is_late,
    )
    db.add(submission)
    db.flush()

    for file in files:
        allowed_ext = [e.lstrip(".") for e in (assignment.allowed_extensions or [])]
        path, name, size, mime = await save_upload_file(
            file, settings.media_assignments_path,
            allowed_extensions=allowed_ext or None,
            max_size_mb=assignment.max_file_size_mb,
        )
        sf = AssignmentSubmissionFile(
            submission_id=submission.id, file_path=path, file_name=name,
            original_name=file.filename, file_size=size, file_mime=mime,
        )
        db.add(sf)

    db.commit()
    return {"message": "Assignment submitted successfully", "submission_id": submission.id, "status": submission.status}
