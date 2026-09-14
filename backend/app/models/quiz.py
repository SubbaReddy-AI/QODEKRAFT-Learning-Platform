from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text,
    ForeignKey, Enum, DECIMAL, JSON
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import enum


class QuizStatus(str, enum.Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class QuestionType(str, enum.Enum):
    single_choice = "single_choice"
    multiple_choice = "multiple_choice"


class AttemptStatus(str, enum.Enum):
    in_progress = "in_progress"
    submitted = "submitted"
    timed_out = "timed_out"
    abandoned = "abandoned"


class Quiz(Base):
    __tablename__ = "quizzes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="SET NULL"))
    title = Column(String(500), nullable=False)
    description = Column(Text)
    time_limit_minutes = Column(Integer)
    max_attempts = Column(Integer, default=1)
    passing_score = Column(DECIMAL(5, 2), default=60.00)
    total_marks = Column(DECIMAL(8, 2), default=100.00)
    due_date = Column(DateTime)
    is_published = Column(Boolean, default=False)
    show_answers = Column(Boolean, default=False)
    show_explanations = Column(Boolean, default=False)
    status = Column(Enum(QuizStatus), default=QuizStatus.draft)
    created_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    domain = relationship("Domain", back_populates="quizzes")
    questions = relationship("QuizQuestion", back_populates="quiz", cascade="all, delete-orphan")
    attempts = relationship("QuizAttempt", back_populates="quiz", cascade="all, delete-orphan")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(Enum(QuestionType), default=QuestionType.single_choice)
    marks = Column(DECIMAL(6, 2), default=1.00)
    explanation = Column(Text)
    attachment_path = Column(String(512))
    attachment_name = Column(String(255))
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    quiz = relationship("Quiz", back_populates="questions")
    options = relationship("QuizOption", back_populates="question", cascade="all, delete-orphan")
    answers = relationship("QuizAnswer", back_populates="question", cascade="all, delete-orphan")


class QuizOption(Base):
    __tablename__ = "quiz_options"

    id = Column(Integer, primary_key=True, autoincrement=True)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)
    order_index = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    question = relationship("QuizQuestion", back_populates="options")


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    quiz_id = Column(Integer, ForeignKey("quizzes.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    attempt_number = Column(Integer, default=1)
    started_at = Column(DateTime, server_default=func.now())
    submitted_at = Column(DateTime)
    time_taken_seconds = Column(Integer)
    score = Column(DECIMAL(8, 2))
    percentage = Column(DECIMAL(5, 2))
    is_passed = Column(Boolean)
    status = Column(Enum(AttemptStatus), default=AttemptStatus.in_progress)
    created_at = Column(DateTime, server_default=func.now())

    quiz = relationship("Quiz", back_populates="attempts")
    student = relationship("User", back_populates="quiz_attempts")
    answers = relationship("QuizAnswer", back_populates="attempt", cascade="all, delete-orphan")


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    attempt_id = Column(Integer, ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(Integer, ForeignKey("quiz_questions.id", ondelete="CASCADE"), nullable=False)
    selected_option_ids = Column(JSON)
    is_correct = Column(Boolean)
    marks_obtained = Column(DECIMAL(6, 2), default=0.00)
    created_at = Column(DateTime, server_default=func.now())

    attempt = relationship("QuizAttempt", back_populates="answers")
    question = relationship("QuizQuestion", back_populates="answers")
