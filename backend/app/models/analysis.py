from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class CompanyAnalysis(Base):
    __tablename__ = "company_analyses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    version = Column(Integer, nullable=False)  # Incremental version number per company
    algorithm_version = Column(String(50), nullable=False, default="1.0.0")
    
    # Analysis data
    submitted_data = Column(JSONB, nullable=False, default=dict)
    discovered_data = Column(JSONB, nullable=False, default=dict)
    signals = Column(JSONB, nullable=False, default=list)  # Array of signal objects
    
    # Scoring
    risk_score = Column(Integer, nullable=False)
    
    # LLM output
    llm_summary = Column(String(2000), nullable=True)
    llm_details = Column(String(5000), nullable=True)
    
    # Completeness tracking
    is_complete = Column(Boolean, default=True, nullable=False)
    failed_checks = Column(JSONB, nullable=False, default=list)  # Array of failed check names
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    company = relationship("Company", back_populates="analyses")

