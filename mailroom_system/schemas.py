from pydantic import BaseModel
from typing import Optional, List
import datetime

class UserBase(BaseModel):
    username: str
    phone_number: str

class UserCreate(UserBase):
    password: str
    role: str = "student"

class User(UserBase):
    id: int
    role: str

    class Config:
        from_attributes = True

class OTPLog(BaseModel):
    id: int
    attempt_time: datetime.datetime
    success: bool

    class Config:
        from_attributes = True

class ParcelBase(BaseModel):
    id: str

class ParcelCreate(ParcelBase):
    student_username: str

class Parcel(ParcelBase):
    student_id: int
    status: str
    created_at: datetime.datetime
    collected_at: Optional[datetime.datetime] = None
    
    owner: User
    otp_logs: List[OTPLog] = []

    class Config:
        from_attributes = True

class ParcelStatus(BaseModel):
    id: str
    status: str
