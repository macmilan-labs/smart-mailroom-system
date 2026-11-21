from sqlalchemy.orm import Session
import models
import schemas
import auth
import datetime
import random

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        password_hash=hashed_password,
        role=user.role,
        phone_number=user.phone_number
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_parcels(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Parcel).offset(skip).limit(limit).all()

def get_student_parcels(db: Session, student_id: int):
    return db.query(models.Parcel).filter(models.Parcel.student_id == student_id).all()

def get_parcel(db: Session, parcel_id: str):
    return db.query(models.Parcel).filter(models.Parcel.id == parcel_id).first()

def create_parcel(db: Session, parcel: schemas.ParcelCreate):
    student = get_user_by_username(db, parcel.student_username)
    if not student:
        return None
    
    db_parcel = models.Parcel(
        id=parcel.id,
        student_id=student.id,
        status="Pending"
    )
    db.add(db_parcel)
    db.commit()
    db.refresh(db_parcel)
    return db_parcel

def mark_parcel_arrived(db: Session, parcel_id: str):
    db_parcel = get_parcel(db, parcel_id)
    if not db_parcel:
        return None
    
    # Generate 6 digit OTP
    otp = str(random.randint(100000, 999999))
    
    db_parcel.status = "Arrived"
    db_parcel.current_otp = otp
    db_parcel.otp_expiry = datetime.datetime.utcnow() + datetime.timedelta(minutes=5)
    
    db.commit()
    db.refresh(db_parcel)
    
    # In a real app, send OTP via SMS here using db_parcel.owner.phone_number
    return db_parcel, otp

def log_otp_attempt(db: Session, parcel_id: str, success: bool):
    otp_log = models.OTPLog(parcel_id=parcel_id, success=success)
    db.add(otp_log)
    db.commit()

def verify_parcel_otp(db: Session, parcel_id: str, otp: str):
    db_parcel = get_parcel(db, parcel_id)
    if not db_parcel:
        return False, "Parcel not found"
        
    if db_parcel.status != "Arrived":
        return False, f"Parcel is in status: {db_parcel.status}"
        
    if not db_parcel.otp_expiry or db_parcel.otp_expiry < datetime.datetime.utcnow():
        return False, "OTP Expired"
        
    if db_parcel.current_otp != otp:
        log_otp_attempt(db, parcel_id, False)
        return False, "Invalid OTP"
        
    # Success
    log_otp_attempt(db, parcel_id, True)
    db_parcel.status = "Collected"
    db_parcel.collected_at = datetime.datetime.utcnow()
    db_parcel.current_otp = None
    db_parcel.otp_expiry = None
    db.commit()
    
    return True, "Parcel Collected"


# ══════════════════════════════════════════════════════════════════════════════
# BIOMETRIC CRUD
# ══════════════════════════════════════════════════════════════════════════════

def save_face_encoding(db: Session, user_id: int, encoding_json: str) -> None:
    """Persist a face encoding JSON string to the user's record."""
    user = get_user_by_id(db, user_id)
    if user:
        user.face_encoding = encoding_json
        db.commit()


def save_fingerprint_id(db: Session, user_id: int, fingerprint_id: str) -> None:
    """Persist a fingerprint ID string to the user's record."""
    user = get_user_by_id(db, user_id)
    if user:
        user.fingerprint_id = fingerprint_id
        db.commit()


def get_face_encoding(db: Session, user_id: int) -> str | None:
    """Return the stored face encoding JSON or None if not yet enrolled."""
    user = get_user_by_id(db, user_id)
    return user.face_encoding if user else None


def get_fingerprint_id(db: Session, user_id: int) -> str | None:
    """Return the stored fingerprint ID or None if not yet enrolled."""
    user = get_user_by_id(db, user_id)
    return user.fingerprint_id if user else None


def get_user_by_fingerprint_id(db: Session, fingerprint_id: str):
    """Identify a user by their enrolled fingerprint ID."""
    return db.query(models.User).filter(models.User.fingerprint_id == fingerprint_id).first()
