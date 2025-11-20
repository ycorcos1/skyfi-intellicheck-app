"""
Database utilities for Lambda worker.
"""
import os
import json
import logging
from datetime import datetime
from typing import Optional
import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError

from app.models.company import Company, AnalysisStatus
from app.models.analysis import CompanyAnalysis
from worker.config import WorkerConfig

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for the worker."""
    
    def __init__(self, config: WorkerConfig):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._initialize_db()
    
    def _initialize_db(self):
        """Initialize database connection from secrets or environment."""
        try:
            # Get DB credentials from Secrets Manager or environment
            if self.config.db_secret_arn:
                db_creds = self._get_secret()
            else:
                # Fallback to environment variables
                db_creds = {
                    'host': self.config.db_host or os.getenv('DB_HOST'),
                    'dbname': self.config.db_name or os.getenv('DB_NAME', 'intellicheck'),
                    'username': self.config.db_user or os.getenv('DB_USER'),
                    'password': self.config.db_password or os.getenv('DB_PASSWORD'),
                    'port': os.getenv('DB_PORT', '5432')
                }
            
            # Build connection string
            db_url = (
                f"postgresql://{db_creds['username']}:{db_creds['password']}"
                f"@{db_creds['host']}:{db_creds.get('port', '5432')}"
                f"/{db_creds['dbname']}"
            )
            
            # Log connection info (mask password)
            safe_url = (
                f"postgresql://{db_creds['username']}:***"
                f"@{db_creds['host']}:{db_creds.get('port', '5432')}"
                f"/{db_creds['dbname']}"
            )
            logger.info(f"Connecting to database: {safe_url}")
            
            self.engine = create_engine(
                db_url,
                pool_pre_ping=True,
                pool_size=1,
                max_overflow=0,
                echo=False
            )
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
            
            logger.info("Database connection initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
            logger.error(f"DB Secret ARN: {self.config.db_secret_arn}")
            logger.error(f"AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}")
            raise
    
    def _get_secret(self) -> dict:
        """Retrieve database credentials from AWS Secrets Manager."""
        try:
            region = os.getenv('AWS_REGION', 'us-east-1')
            logger.info(f"Retrieving database secret from Secrets Manager (ARN: {self.config.db_secret_arn[:50]}..., Region: {region})")
            secrets_client = boto3.client('secretsmanager', region_name=region)
            response = secrets_client.get_secret_value(SecretId=self.config.db_secret_arn)
            secret = json.loads(response['SecretString'])
            
            # Validate required keys
            required_keys = ['username', 'password', 'host', 'dbname', 'port']
            missing_keys = [key for key in required_keys if key not in secret]
            if missing_keys:
                raise ValueError(f"Secret missing required keys: {missing_keys}. Found keys: {list(secret.keys())}")
            
            logger.info("Database secret retrieved successfully")
            return secret
        except Exception as e:
            logger.error(f"Failed to retrieve secret: {str(e)}", exc_info=True)
            logger.error(f"Secret ARN: {self.config.db_secret_arn}")
            logger.error(f"AWS Region: {os.getenv('AWS_REGION', 'us-east-1')}")
            raise
    
    def get_session(self):
        """Get a database session."""
        return self.SessionLocal()
    
    def fetch_company(self, company_id: str) -> Company:
        """Fetch company by ID."""
        session = self.get_session()
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError(f"Company {company_id} not found")
            return company
        finally:
            session.close()

    def fetch_latest_analysis(self, company_id: str) -> Optional[CompanyAnalysis]:
        """Fetch the most recent analysis record for a company."""
        session = self.get_session()
        try:
            return (
                session.query(CompanyAnalysis)
                .filter(CompanyAnalysis.company_id == company_id)
                .order_by(CompanyAnalysis.created_at.desc())
                .first()
            )
        finally:
            session.close()
    
    def update_company_step(self, company_id: str, step: str, status: AnalysisStatus = None):
        """Update company's current analysis step."""
        session = self.get_session()
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if company:
                company.current_step = step
                if status:
                    company.analysis_status = status
                session.commit()
                logger.debug(f"Updated company {company_id} step to {step}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update company step: {str(e)}")
            raise
        finally:
            session.close()
    
    def update_company_analysis_status(
        self,
        company_id: str,
        status: AnalysisStatus,
        current_step: Optional[str] = None
    ):
        """Update company analysis status atomically."""
        session = self.get_session()
        try:
            company = session.query(Company).filter(Company.id == company_id).first()
            if not company:
                raise ValueError(f"Company {company_id} not found")
            
            company.analysis_status = status
            if current_step:
                company.current_step = current_step
            
            if status == AnalysisStatus.COMPLETED:
                company.current_step = 'complete'
                company.last_analyzed_at = datetime.utcnow()
            elif status == AnalysisStatus.FAILED:
                company.current_step = None
            
            session.commit()
            logger.info(f"Updated company {company_id} status to {status.value}")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update company analysis status: {str(e)}")
            raise
        finally:
            session.close()
    
    def save_analysis(
        self,
        company_id: str,
        risk_score: int,
        signals: list,
        failed_checks: list,
        submitted_data: dict,
        discovered_data: dict,
        is_complete: bool,
        algorithm_version: str = "1.0.0",
        llm_summary: Optional[str] = None,
        llm_details: Optional[str] = None
    ) -> CompanyAnalysis:
        """
        Save analysis results to database.
        
        Args:
            company_id: Company UUID
            risk_score: Final hybrid risk score (0-100)
            signals: List of Signal objects or dicts
            failed_checks: List of failed check names
            submitted_data: Original submitted company data
            discovered_data: Discovered data from external checks
            is_complete: Whether analysis completed successfully
            algorithm_version: Algorithm version string
            llm_summary: LLM-generated summary (optional)
            llm_details: LLM-generated detailed reasoning (optional)
            
        Returns:
            Created CompanyAnalysis object
        """
        session = self.get_session()
        try:
            # Get latest version for this company
            latest_analysis = (
                session.query(CompanyAnalysis)
                .filter(CompanyAnalysis.company_id == company_id)
                .order_by(CompanyAnalysis.version.desc())
                .first()
            )
            
            next_version = (latest_analysis.version + 1) if latest_analysis else 1
            
            # Convert signals to dict format for JSONB
            signals_dict = []
            for s in signals:
                if isinstance(s, dict):
                    signals_dict.append(s)
                else:
                    signals_dict.append({
                        'field': s.field,
                        'status': s.status.value if hasattr(s.status, 'value') else str(s.status),
                        'value': s.value,
                        'weight': s.weight,
                        'severity': s.severity.value if hasattr(s.severity, 'value') else str(s.severity)
                    })
            
            # Create analysis record
            analysis = CompanyAnalysis(
                company_id=company_id,
                version=next_version,
                algorithm_version=algorithm_version,
                submitted_data=submitted_data,
                discovered_data=discovered_data,
                signals=signals_dict,
                risk_score=risk_score,
                llm_summary=llm_summary,
                llm_details=llm_details,
                is_complete=is_complete,
                failed_checks=failed_checks
            )
            
            session.add(analysis)
            
            # Update company record
            company = session.query(Company).filter(Company.id == company_id).first()
            if company:
                company.risk_score = risk_score
                company.analysis_status = AnalysisStatus.COMPLETED if is_complete else AnalysisStatus.INCOMPLETE
                company.current_step = "complete"
                company.last_analyzed_at = datetime.utcnow()
            
            session.commit()
            logger.info(
                f"Saved analysis version {next_version} for company {company_id} "
                f"(risk_score: {risk_score}, is_complete: {is_complete})"
            )
            
            return analysis
            
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save analysis: {str(e)}")
            raise
        finally:
            session.close()

