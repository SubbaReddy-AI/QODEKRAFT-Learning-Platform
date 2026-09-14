from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.database import get_db
from app.auth.jwt import decode_token
from app.models.user import User, UserRole, UserStatus
from datetime import datetime

security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """Decode JWT and return the authenticated user. Raises 401 if invalid."""
    token = credentials.credentials
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject")

    user = db.query(User).filter(User.id == int(user_id), User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or deactivated")

    return user


def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required",
        )
    return current_user


def get_current_approved_student(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
    """Require approved student."""
    if current_user.role != UserRole.student:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student access only")
    if current_user.status != UserStatus.approved:
        status_messages = {
            UserStatus.pending: "Your account is pending admin approval",
            UserStatus.rejected: "Your account application was rejected",
            UserStatus.blocked: "Your account has been blocked",
            UserStatus.suspended: "Your account is currently suspended",
        }
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=status_messages.get(current_user.status, "Account access denied"),
        )
    from app.models.domain import StudentDomain, DomainAccessStatus
    has_active_domain = db.query(StudentDomain).filter(
        StudentDomain.student_id == current_user.id,
        StudentDomain.status == DomainAccessStatus.active,
    ).first()
    if not has_active_domain:
        raise HTTPException(status_code=403, detail="No active learning domain is assigned to your account")
    return current_user


def verify_student_domain_access(student: User, domain_id: int, db: Session) -> bool:
    """Verify that a student has active access to a specific domain."""
    from app.models.domain import StudentDomain, DomainAccessStatus
    from app.models.domain import Domain

    # Check student status
    if student.status != UserStatus.approved:
        return False

    # Find the student-domain assignment
    sd = db.query(StudentDomain).filter(
        StudentDomain.student_id == student.id,
        StudentDomain.domain_id == domain_id,
        StudentDomain.status == DomainAccessStatus.active,
    ).first()

    if not sd:
        return False

    # Check expiry
    if sd.access_expires_at and sd.access_expires_at < datetime.utcnow():
        # Auto-mark as expired
        sd.status = DomainAccessStatus.expired
        db.commit()
        return False

    # Check domain is active
    domain = db.query(Domain).filter(Domain.id == domain_id, Domain.is_active == True).first()
    if not domain:
        return False

    return True


def require_domain_access(domain_id: int):
    """Factory for a FastAPI dependency that checks student domain access."""
    def _dependency(
        current_user: User = Depends(get_current_approved_student),
        db: Session = Depends(get_db),
    ) -> User:
        if not verify_student_domain_access(current_user, domain_id, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have access to this domain",
            )
        return current_user
    return _dependency
