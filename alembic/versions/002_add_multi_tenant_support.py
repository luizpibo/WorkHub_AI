"""Add multi-tenant support

Revision ID: 002
Revises: 001
Create Date: 2026-01-28

This migration transforms the system from single-tenant to multi-tenant:
1. Creates new tenant infrastructure tables
2. Adds tenant_id to existing tables
3. Creates default "workhub" tenant
4. Backfills tenant_id in existing data
5. Updates constraints for tenant isolation
6. Creates performance indexes
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.dialects import postgresql
import uuid
import bcrypt
import json

# revision identifiers, used by Alembic.
revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ========================================
    # STEP 1: Create new tenant tables
    # ========================================

    # Create TenantStatus enum (only if not exists)
    op.execute(text("""
        DO $$ BEGIN
            CREATE TYPE tenantstatus AS ENUM ('ACTIVE', 'TRIAL', 'SUSPENDED', 'CANCELLED');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create PromptType enum (only if not exists)
    op.execute(text("""
        DO $$ BEGIN
            CREATE TYPE prompttype AS ENUM ('SALES_AGENT', 'ADMIN_AGENT', 'ANALYST_AGENT');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create DocumentType enum (only if not exists)
    op.execute(text("""
        DO $$ BEGIN
            CREATE TYPE documenttype AS ENUM ('PRODUCT', 'FAQ', 'OBJECTIONS', 'SCRIPTS');
        EXCEPTION
            WHEN duplicate_object THEN null;
        END $$;
    """))

    # Create enum objects for use in table definitions (create_type=False means don't try to create, just reference)
    tenant_status_enum = postgresql.ENUM('ACTIVE', 'TRIAL', 'SUSPENDED', 'CANCELLED', name='tenantstatus', create_type=False)
    prompt_type_enum = postgresql.ENUM('SALES_AGENT', 'ADMIN_AGENT', 'ANALYST_AGENT', name='prompttype', create_type=False)
    document_type_enum = postgresql.ENUM('PRODUCT', 'FAQ', 'OBJECTIONS', 'SCRIPTS', name='documenttype', create_type=False)

    # Create tenants table
    op.create_table('tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('api_key_hash', sa.String(), nullable=True),
        sa.Column('api_key_prefix', sa.String(), nullable=True),
        sa.Column('status', tenant_status_enum, nullable=False, server_default='ACTIVE'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('expires_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tenants_slug', 'tenants', ['slug'], unique=True)

    # Create prompt_templates table
    op.create_table('prompt_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('prompt_type', prompt_type_enum, nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('system_prompt', sa.Text(), nullable=False),
        sa.Column('knowledge_base', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'prompt_type', 'version', name='uq_tenant_prompt_version')
    )
    op.create_index('ix_prompt_templates_tenant_id', 'prompt_templates', ['tenant_id'])
    op.create_index('idx_tenant_prompt_type_active', 'prompt_templates', ['tenant_id', 'prompt_type', 'is_active'])

    # Create knowledge_documents table
    op.create_table('knowledge_documents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('document_type', document_type_enum, nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'slug', name='uq_tenant_knowledge_slug')
    )
    op.create_index('ix_knowledge_documents_tenant_id', 'knowledge_documents', ['tenant_id'])
    op.create_index('ix_knowledge_documents_slug', 'knowledge_documents', ['slug'])
    op.create_index('idx_tenant_document_type', 'knowledge_documents', ['tenant_id', 'document_type'])

    # ========================================
    # STEP 2: Add tenant_id to existing tables (nullable)
    # ========================================

    op.add_column('users', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('plans', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('conversations', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('messages', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('leads', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column('analysis_reports', sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True))

    # Create indexes on tenant_id columns (before FK constraints)
    op.create_index('ix_users_tenant_id', 'users', ['tenant_id'])
    op.create_index('ix_plans_tenant_id', 'plans', ['tenant_id'])
    op.create_index('ix_conversations_tenant_id', 'conversations', ['tenant_id'])
    op.create_index('ix_messages_tenant_id', 'messages', ['tenant_id'])
    op.create_index('ix_leads_tenant_id', 'leads', ['tenant_id'])
    op.create_index('ix_analysis_reports_tenant_id', 'analysis_reports', ['tenant_id'])

    # ========================================
    # STEP 3: Create default "workhub" tenant
    # ========================================

    # Generate a default API key for WorkHub
    default_api_key = f"wh_{uuid.uuid4().hex[:32]}"
    api_key_hash = bcrypt.hashpw(default_api_key.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    api_key_prefix = default_api_key[:8]

    # Default tenant configuration for WorkHub
    workhub_config = {
        "business_type": "coworking",
        "currency": "BRL",
        "features": {
            "enable_handoff": True,
            "enable_analytics": True,
            "max_users": 10000
        },
        "funnel_config": {
            "stages": [
                {"key": "awareness", "name": "Conscientização"},
                {"key": "interest", "name": "Interesse"},
                {"key": "consideration", "name": "Consideração"},
                {"key": "negotiation", "name": "Negociação"},
                {"key": "closed_won", "name": "Fechado Ganho"},
                {"key": "closed_lost", "name": "Perdido"}
            ]
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-4o-mini",
            "temperature": 0.7
        }
    }

    # Insert default tenant
    workhub_id = uuid.uuid4()
    config_json = json.dumps(workhub_config)
    op.execute(
        sa.text(
            """
            INSERT INTO tenants (id, slug, name, config, api_key_hash, api_key_prefix, status, is_active, created_at, updated_at)
            VALUES (:id, :slug, :name, CAST(:config AS jsonb), :api_key_hash, :api_key_prefix, CAST(:status AS tenantstatus), :is_active, NOW(), NOW())
            """
        ).bindparams(
            id=workhub_id,
            slug='workhub',
            name='WorkHub Coworking',
            config=config_json,
            api_key_hash=api_key_hash,
            api_key_prefix=api_key_prefix,
            status='ACTIVE',
            is_active=True
        )
    )

    # Print API key for admin (will be shown only once)
    print("\n" + "="*80)
    print("DEFAULT TENANT CREATED: WorkHub")
    print("="*80)
    print(f"Tenant ID: {workhub_id}")
    print(f"Tenant Slug: workhub")
    print(f"API Key: {default_api_key}")
    print("="*80)
    print("⚠️  SAVE THIS API KEY! It will not be shown again.")
    print("="*80 + "\n")

    # ========================================
    # STEP 4: Backfill tenant_id in existing data
    # ========================================

    # Update all existing records to use the workhub tenant
    op.execute(
        sa.text("UPDATE users SET tenant_id = :tenant_id WHERE tenant_id IS NULL")
        .bindparams(tenant_id=workhub_id)
    )

    op.execute(
        sa.text("UPDATE plans SET tenant_id = :tenant_id WHERE tenant_id IS NULL")
        .bindparams(tenant_id=workhub_id)
    )

    op.execute(
        sa.text("UPDATE conversations SET tenant_id = :tenant_id WHERE tenant_id IS NULL")
        .bindparams(tenant_id=workhub_id)
    )

    op.execute(
        sa.text("UPDATE messages SET tenant_id = :tenant_id WHERE tenant_id IS NULL")
        .bindparams(tenant_id=workhub_id)
    )

    op.execute(
        sa.text("UPDATE leads SET tenant_id = :tenant_id WHERE tenant_id IS NULL")
        .bindparams(tenant_id=workhub_id)
    )

    op.execute(
        sa.text("UPDATE analysis_reports SET tenant_id = :tenant_id WHERE tenant_id IS NULL")
        .bindparams(tenant_id=workhub_id)
    )

    # ========================================
    # STEP 5: Make tenant_id NOT NULL and add foreign keys
    # ========================================

    op.alter_column('users', 'tenant_id', nullable=False)
    op.alter_column('plans', 'tenant_id', nullable=False)
    op.alter_column('conversations', 'tenant_id', nullable=False)
    op.alter_column('messages', 'tenant_id', nullable=False)
    op.alter_column('leads', 'tenant_id', nullable=False)
    op.alter_column('analysis_reports', 'tenant_id', nullable=False)

    # Add foreign key constraints
    op.create_foreign_key('fk_users_tenant_id', 'users', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_plans_tenant_id', 'plans', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_conversations_tenant_id', 'conversations', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_messages_tenant_id', 'messages', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_leads_tenant_id', 'leads', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('fk_analysis_reports_tenant_id', 'analysis_reports', 'tenants', ['tenant_id'], ['id'], ondelete='CASCADE')

    # ========================================
    # STEP 6: Update constraints (drop global unique, add tenant-scoped unique)
    # ========================================

    # Users: drop global unique on user_key, add tenant-scoped unique
    op.drop_index('ix_users_user_key', table_name='users')
    op.create_index('ix_users_user_key', 'users', ['user_key'])  # Non-unique index
    op.create_unique_constraint('uq_tenant_user_key', 'users', ['tenant_id', 'user_key'])

    # Plans: drop global unique on slug, add tenant-scoped unique
    op.drop_index('ix_plans_slug', table_name='plans')
    op.create_index('ix_plans_slug', 'plans', ['slug'])  # Non-unique index
    op.create_unique_constraint('uq_tenant_plan_slug', 'plans', ['tenant_id', 'slug'])

    # ========================================
    # STEP 7: Create performance indexes
    # ========================================

    # User indexes
    op.create_index('idx_user_tenant_key', 'users', ['tenant_id', 'user_key'])

    # Plan indexes
    op.create_index('idx_plan_tenant_active', 'plans', ['tenant_id', 'is_active'])

    # Conversation indexes
    op.create_index('idx_conversation_tenant_user', 'conversations', ['tenant_id', 'user_id'])
    op.create_index('idx_conversation_tenant_status', 'conversations', ['tenant_id', 'status'])
    op.create_index('idx_conversation_tenant_funnel', 'conversations', ['tenant_id', 'funnel_stage'])

    # Message indexes
    op.create_index('idx_message_tenant_conversation', 'messages', ['tenant_id', 'conversation_id'])

    # Lead indexes
    op.create_index('idx_lead_tenant_stage', 'leads', ['tenant_id', 'stage'])
    op.create_index('idx_lead_tenant_user', 'leads', ['tenant_id', 'user_id'])

    # Analysis Report indexes
    op.create_index('idx_analysis_tenant_type', 'analysis_reports', ['tenant_id', 'analysis_type'])


def downgrade() -> None:
    """
    Downgrade migration - reverses all multi-tenant changes
    WARNING: This will remove tenant isolation and may cause data loss if multiple tenants exist!
    """

    # Drop performance indexes
    op.drop_index('idx_analysis_tenant_type', table_name='analysis_reports')
    op.drop_index('idx_lead_tenant_user', table_name='leads')
    op.drop_index('idx_lead_tenant_stage', table_name='leads')
    op.drop_index('idx_message_tenant_conversation', table_name='messages')
    op.drop_index('idx_conversation_tenant_funnel', table_name='conversations')
    op.drop_index('idx_conversation_tenant_status', table_name='conversations')
    op.drop_index('idx_conversation_tenant_user', table_name='conversations')
    op.drop_index('idx_plan_tenant_active', table_name='plans')
    op.drop_index('idx_user_tenant_key', table_name='users')

    # Restore global unique constraints
    op.drop_constraint('uq_tenant_plan_slug', 'plans', type_='unique')
    op.drop_index('ix_plans_slug', table_name='plans')
    op.create_index('ix_plans_slug', 'plans', ['slug'], unique=True)

    op.drop_constraint('uq_tenant_user_key', 'users', type_='unique')
    op.drop_index('ix_users_user_key', table_name='users')
    op.create_index('ix_users_user_key', 'users', ['user_key'], unique=True)

    # Drop foreign key constraints
    op.drop_constraint('fk_analysis_reports_tenant_id', 'analysis_reports', type_='foreignkey')
    op.drop_constraint('fk_leads_tenant_id', 'leads', type_='foreignkey')
    op.drop_constraint('fk_messages_tenant_id', 'messages', type_='foreignkey')
    op.drop_constraint('fk_conversations_tenant_id', 'conversations', type_='foreignkey')
    op.drop_constraint('fk_plans_tenant_id', 'plans', type_='foreignkey')
    op.drop_constraint('fk_users_tenant_id', 'users', type_='foreignkey')

    # Drop tenant_id indexes
    op.drop_index('ix_analysis_reports_tenant_id', table_name='analysis_reports')
    op.drop_index('ix_leads_tenant_id', table_name='leads')
    op.drop_index('ix_messages_tenant_id', table_name='messages')
    op.drop_index('ix_conversations_tenant_id', table_name='conversations')
    op.drop_index('ix_plans_tenant_id', table_name='plans')
    op.drop_index('ix_users_tenant_id', table_name='users')

    # Drop tenant_id columns
    op.drop_column('analysis_reports', 'tenant_id')
    op.drop_column('leads', 'tenant_id')
    op.drop_column('messages', 'tenant_id')
    op.drop_column('conversations', 'tenant_id')
    op.drop_column('plans', 'tenant_id')
    op.drop_column('users', 'tenant_id')

    # Drop new tenant tables
    op.drop_table('knowledge_documents')
    op.drop_table('prompt_templates')
    op.drop_table('tenants')

    # Drop enums
    document_type_enum = postgresql.ENUM('PRODUCT', 'FAQ', 'OBJECTIONS', 'SCRIPTS', name='documenttype')
    document_type_enum.drop(op.get_bind(), checkfirst=True)

    prompt_type_enum = postgresql.ENUM('SALES_AGENT', 'ADMIN_AGENT', 'ANALYST_AGENT', name='prompttype')
    prompt_type_enum.drop(op.get_bind(), checkfirst=True)

    tenant_status_enum = postgresql.ENUM('ACTIVE', 'TRIAL', 'SUSPENDED', 'CANCELLED', name='tenantstatus')
    tenant_status_enum.drop(op.get_bind(), checkfirst=True)
