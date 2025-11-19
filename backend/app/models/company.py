from sqlalchemy import Column, String, Integer, Boolean, DateTime, Enum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

from app.core.database import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INCOMPLETE = "incomplete"


class CompanyStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FRAUDULENT = "fraudulent"
    REVOKED = "revoked"


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), nullable=False, index=True)
    website_url = Column(String(500), nullable=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    
    # Status fields
    status = Column(Enum(CompanyStatus), default=CompanyStatus.PENDING, nullable=False, index=True)
    risk_score = Column(Integer, default=0, nullable=False, index=True)
    
    # Analysis tracking fields
    analysis_status = Column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING, nullable=False, index=True)
    current_step = Column(String(50), nullable=True)  # whois|dns|mx_validation|website_scrape|llm_processing|complete
    last_analyzed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False, index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    analyses = relationship("CompanyAnalysis", back_populates="company", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="company", cascade="all, delete-orphan")
    notes = relationship("Note", back_populates="company", cascade="all, delete-orphan")

