"""Initial schema: companies, company_analyses, documents, notes

Revision ID: 001_initial_schema
Revises: 
Create Date: 2025-01-15 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    company_status = postgresql.ENUM('pending', 'approved', 'rejected', 'fraudulent', 'revoked', name='companystatus')
    company_status.create(op.get_bind())
    
    analysis_status = postgresql.ENUM('pending', 'in_progress', 'completed', 'failed', 'incomplete', name='analysisstatus')
    analysis_status.create(op.get_bind())
    
    # Create companies table
    op.create_table(
        'companies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255), nullable=False),
        sa.Column('website_url', sa.String(500), nullable=True),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('status', company_status, nullable=False, server_default='pending'),
        sa.Column('risk_score', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('analysis_status', analysis_status, nullable=False, server_default='pending'),
        sa.Column('current_step', sa.String(50), nullable=True),
        sa.Column('last_analyzed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
    )
    
    # Create indexes on companies
    op.create_index('ix_companies_domain', 'companies', ['domain'])
    op.create_index('ix_companies_status', 'companies', ['status'])
    op.create_index('ix_companies_risk_score', 'companies', ['risk_score'])
    op.create_index('ix_companies_analysis_status', 'companies', ['analysis_status'])
    op.create_index('ix_companies_is_deleted', 'companies', ['is_deleted'])
    op.create_index('ix_companies_created_at', 'companies', ['created_at'])
    
    # Create company_analyses table
    op.create_table(
        'company_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('algorithm_version', sa.String(50), nullable=False, server_default='1.0.0'),
        sa.Column('submitted_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('discovered_data', postgresql.JSONB, nullable=False, server_default='{}'),
        sa.Column('signals', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('risk_score', sa.Integer(), nullable=False),
        sa.Column('llm_summary', sa.String(2000), nullable=True),
        sa.Column('llm_details', sa.String(5000), nullable=True),
        sa.Column('is_complete', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('failed_checks', postgresql.JSONB, nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    
    # Create indexes on company_analyses
    op.create_index('ix_company_analyses_company_id', 'company_analyses', ['company_id'])
    op.create_index('ix_company_analyses_created_at', 'company_analyses', ['created_at'])
    op.create_index('ix_company_analyses_company_version', 'company_analyses', ['company_id', 'version'], unique=True)
    
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('s3_key', sa.String(500), nullable=False, unique=True),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('uploaded_by', sa.String(255), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=True),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    
    # Create indexes on documents
    op.create_index('ix_documents_company_id', 'documents', ['company_id'])
    op.create_index('ix_documents_created_at', 'documents', ['created_at'])
    
    # Create notes table
    op.create_table(
        'notes',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('company_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', sa.String(255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.ForeignKeyConstraint(['company_id'], ['companies.id'], ondelete='CASCADE'),
    )
    
    # Create indexes on notes
    op.create_index('ix_notes_company_id', 'notes', ['company_id'])
    op.create_index('ix_notes_created_at', 'notes', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_notes_created_at', table_name='notes')
    op.drop_index('ix_notes_company_id', table_name='notes')
    op.drop_table('notes')
    
    op.drop_index('ix_documents_created_at', table_name='documents')
    op.drop_index('ix_documents_company_id', table_name='documents')
    op.drop_table('documents')
    
    op.drop_index('ix_company_analyses_company_version', table_name='company_analyses')
    op.drop_index('ix_company_analyses_created_at', table_name='company_analyses')
    op.drop_index('ix_company_analyses_company_id', table_name='company_analyses')
    op.drop_table('company_analyses')
    
    op.drop_index('ix_companies_created_at', table_name='companies')
    op.drop_index('ix_companies_is_deleted', table_name='companies')
    op.drop_index('ix_companies_analysis_status', table_name='companies')
    op.drop_index('ix_companies_risk_score', table_name='companies')
    op.drop_index('ix_companies_status', table_name='companies')
    op.drop_index('ix_companies_domain', table_name='companies')
    op.drop_table('companies')
    
    # Drop enums
    analysis_status = postgresql.ENUM(name='analysisstatus')
    analysis_status.drop(op.get_bind(), checkfirst=True)
    
    company_status = postgresql.ENUM(name='companystatus')
    company_status.drop(op.get_bind(), checkfirst=True)

