"""phase_12_schema_updates

Revision ID: d2c3f4e5a6b7
Revises: e92050ea4e69
Create Date: 2026-09-23 19:10:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'd2c3f4e5a6b7'
down_revision = 'e92050ea4e69'
branch_labels = None
depends_on = None

def upgrade():
    # 1. Update recognitions table
    recognition_status = postgresql.ENUM('AUTO_ACCEPTED', 'REVIEW_REQUIRED', 'HUMAN_CORRECTED', name='recognitionstatus')
    recognition_status.create(op.get_bind(), checkfirst=True)
    op.add_column('recognitions', sa.Column('status', recognition_status, nullable=False, server_default='AUTO_ACCEPTED'))
    
    # 2. Update AuditStatus ENUM in Postgres
    op.execute("ALTER TYPE auditstatus ADD VALUE IF NOT EXISTS 'PENDING_REVIEW'")
    
    # 3. Update human_reviews table
    op.add_column('human_reviews', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('human_reviews', sa.Column('audit_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('human_reviews', sa.Column('predicted_similarity', sa.Float(), nullable=True))
    op.add_column('human_reviews', sa.Column('predicted_margin', sa.Float(), nullable=True))
    op.add_column('human_reviews', sa.Column('crop_storage_key', sa.String(), nullable=True))
    op.add_column('human_reviews', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    
    # Handle the status ENUM
    review_status = postgresql.ENUM('PENDING', 'COMPLETED', name='reviewstatus')
    review_status.create(op.get_bind(), checkfirst=True)
    op.add_column('human_reviews', sa.Column('status', review_status, nullable=False, server_default='PENDING'))
    
    # Rename correct_product_id to corrected_product_id
    op.alter_column('human_reviews', 'correct_product_id', new_column_name='corrected_product_id')
    
    # Drop old action and notes
    op.drop_column('human_reviews', 'action')
    op.drop_column('human_reviews', 'notes')
    
    # Create Foreign Keys and Indexes
    op.create_foreign_key('fk_human_reviews_org_id', 'human_reviews', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_human_reviews_audit_id', 'human_reviews', 'shelf_audits', ['audit_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_human_reviews_org_id', 'human_reviews', ['organization_id'])
    op.create_index('ix_human_reviews_audit_id', 'human_reviews', ['audit_id'])
    op.create_index('ix_human_reviews_status', 'human_reviews', ['status'])
    
    # 4. Update ml_training_samples table
    op.add_column('ml_training_samples', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key('fk_ml_samples_org_id', 'ml_training_samples', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE')
    op.create_index('ix_ml_samples_org_id', 'ml_training_samples', ['organization_id'])
    
    # Update SampleStatus ENUM
    op.execute("ALTER TYPE samplestatus ADD VALUE IF NOT EXISTS 'USED_FOR_TRAINING'")

def downgrade():
    # Down revisions are generally not recommended for complex ENUM changes,
    # but we can drop the columns for safety.
    op.drop_column('ml_training_samples', 'organization_id')
    op.alter_column('human_reviews', 'corrected_product_id', new_column_name='correct_product_id')
    op.add_column('human_reviews', sa.Column('action', sa.String(), nullable=True))
    op.add_column('human_reviews', sa.Column('notes', sa.String(), nullable=True))
    op.drop_column('human_reviews', 'status')
    op.drop_column('human_reviews', 'reviewed_at')
    op.drop_column('human_reviews', 'crop_storage_key')
    op.drop_column('human_reviews', 'predicted_margin')
    op.drop_column('human_reviews', 'predicted_similarity')
    op.drop_column('human_reviews', 'audit_id')
    op.drop_column('human_reviews', 'organization_id')
    op.drop_column('recognitions', 'status')
