from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, Text
from sqlalchemy.orm import relationship
import datetime
from database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String, default="student") # "student" or "admin"
    phone_number = Column(String)

    # ── Biometric fields ─────────────────────────────────────────────────────────
    # face_encoding: JSON-serialised list[float] from face_recognition, or
    #                base64 JPEG string when the library is unavailable (PIL fallback)
    face_encoding  = Column(Text,   nullable=True)
    # fingerprint_id: opaque string returned by the hardware sensor (e.g. "FP-001")
    fingerprint_id = Column(String, nullable=True)

    parcels = relationship("Parcel", back_populates="owner")

class Parcel(Base):
    __tablename__ = "parcels"

    id = Column(String, primary_key=True, index=True) # Unique Tracking ID / Name
    student_id = Column(Integer, ForeignKey("users.id"))
    status = Column(String, default="Pending") # Pending, Arrived, Collected
    current_otp = Column(String, nullable=True) # Keeping plain text for this prototype to allow staff easily viewing in case of SMS failure, otherwise usually hashed.
    otp_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    collected_at = Column(DateTime, nullable=True)

    owner = relationship("User", back_populates="parcels")
    otp_logs = relationship("OTPLog", back_populates="parcel")

class OTPLog(Base):
    __tablename__ = "otp_logs"

    id = Column(Integer, primary_key=True, index=True)
    parcel_id = Column(String, ForeignKey("parcels.id"))
    attempt_time = Column(DateTime, default=datetime.datetime.utcnow)
    success = Column(Boolean, default=False)

    parcel = relationship("Parcel", back_populates="otp_logs")
