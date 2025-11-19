from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.core.database import Base


class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # File metadata
    filename = Column(String(255), nullable=False)
    s3_key = Column(String(500), nullable=False, unique=True)
    file_size = Column(Integer, nullable=False)  # Size in bytes
    mime_type = Column(String(100), nullable=False)
    
    # Upload tracking
    uploaded_by = Column(String(255), nullable=False)  # Cognito user_id
    document_type = Column(String(100), nullable=True)  # e.g., "proof_of_address", "business_license"
    description = Column(String(500), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False, index=True)

    # Relationships
    company = relationship("Company", back_populates="documents")

