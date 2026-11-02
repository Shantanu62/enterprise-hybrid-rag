
-- =========================================================
-- ENTERPRISE HYBRID RAG
-- Multi-Tenant Database Foundation
-- PostgreSQL 17+
-- =========================================================

BEGIN;

-- ---------------------------------------------------------
-- 1. ORGANIZATIONS
-- Each organization represents one tenant.
-- ---------------------------------------------------------

CREATE TABLE organizations (
    id UUID PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    slug VARCHAR(100) NOT NULL UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT organizations_name_not_empty
        CHECK (LENGTH(TRIM(name)) > 0),

    CONSTRAINT organizations_slug_not_empty
        CHECK (LENGTH(TRIM(slug)) > 0),

    CONSTRAINT organizations_status_check
        CHECK (status IN ('active', 'suspended', 'deleted'))
);

-- ---------------------------------------------------------
-- 2. USERS
-- Global user identity.
-- Password hashes will be added through the auth layer.
-- Never store plain-text passwords.
-- ---------------------------------------------------------

CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    full_name VARCHAR(150) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT users_email_not_empty
        CHECK (LENGTH(TRIM(email)) > 0),

    CONSTRAINT users_status_check
        CHECK (status IN ('active', 'inactive', 'suspended'))
);

-- ---------------------------------------------------------
-- 3. ORGANIZATION MEMBERS
-- Connects users with organizations.
-- A user can belong to multiple organizations.
-- ---------------------------------------------------------

CREATE TABLE organization_members (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    user_id UUID NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'member',
    joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT organization_members_org_fk
        FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    CONSTRAINT organization_members_user_fk
        FOREIGN KEY (user_id)
        REFERENCES users(id)
        ON DELETE CASCADE,

    CONSTRAINT organization_members_role_check
        CHECK (role IN ('owner', 'admin', 'member', 'viewer')),

    CONSTRAINT organization_members_unique
        UNIQUE (organization_id, user_id)
);

-- ---------------------------------------------------------
-- 4. DOCUMENTS
-- One logical document belongs to one organization.
-- ---------------------------------------------------------

CREATE TABLE documents (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    uploaded_by UUID,
    source_name VARCHAR(500) NOT NULL,
    file_type VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT documents_org_fk
        FOREIGN KEY (organization_id)
        REFERENCES organizations(id)
        ON DELETE CASCADE,

    CONSTRAINT documents_uploader_fk
        FOREIGN KEY (uploaded_by)
        REFERENCES users(id)
        ON DELETE SET NULL,

    CONSTRAINT documents_source_not_empty
        CHECK (LENGTH(TRIM(source_name)) > 0),

    CONSTRAINT documents_file_type_check
        CHECK (file_type IN ('pdf', 'docx', 'txt')),

    CONSTRAINT documents_status_check
        CHECK (status IN ('active', 'processing', 'failed', 'deleted')),

    -- Supports tenant-safe composite foreign keys.
    CONSTRAINT documents_id_org_unique
        UNIQUE (id, organization_id)
);

-- ---------------------------------------------------------
-- 5. DOCUMENT VERSIONS
-- Every re-upload creates a new version.
-- ---------------------------------------------------------

CREATE TABLE document_versions (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    document_id UUID NOT NULL,
    version_number INTEGER NOT NULL,
    storage_path VARCHAR(1000),
    content_hash VARCHAR(128),
    chunk_count INTEGER NOT NULL DEFAULT 0,
    status VARCHAR(30) NOT NULL DEFAULT 'pending',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT document_versions_document_fk
        FOREIGN KEY (document_id, organization_id)
        REFERENCES documents(id, organization_id)
        ON DELETE CASCADE,

    CONSTRAINT document_versions_number_check
        CHECK (version_number > 0),

    CONSTRAINT document_versions_chunk_check
        CHECK (chunk_count >= 0),

    CONSTRAINT document_versions_status_check
        CHECK (status IN ('pending', 'processing', 'completed', 'failed')),

    CONSTRAINT document_versions_unique
        UNIQUE (document_id, version_number),
        
    CONSTRAINT document_versions_document_id_unique
        UNIQUE (document_id, id),

    -- Supports tenant-safe ingestion job references.
    CONSTRAINT document_versions_id_org_unique
        UNIQUE (id, organization_id)
);

-- ---------------------------------------------------------
-- 6. INGESTION JOBS
-- Tracks document processing lifecycle.
-- ---------------------------------------------------------

CREATE TABLE ingestion_jobs (
    id UUID PRIMARY KEY,
    organization_id UUID NOT NULL,
    document_id UUID NOT NULL,
    version_id UUID NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'queued',
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT ingestion_jobs_version_fk
        FOREIGN KEY (version_id, organization_id)
        REFERENCES document_versions(id, organization_id)
        ON DELETE CASCADE,

    CONSTRAINT ingestion_jobs_document_fk
        FOREIGN KEY (document_id, organization_id)
        REFERENCES documents(id, organization_id)
        ON DELETE CASCADE,

    CONSTRAINT ingestion_jobs_status_check
        CHECK (status IN ('queued', 'processing', 'completed', 'failed')),

    CONSTRAINT ingestion_jobs_version_document_fk
        FOREIGN KEY (document_id, version_id)
        REFERENCES document_versions(document_id, id)
        ON DELETE CASCADE
);

-- ---------------------------------------------------------
-- INDEXES
-- ---------------------------------------------------------

CREATE INDEX idx_organization_members_user
    ON organization_members(user_id);

CREATE INDEX idx_documents_organization
    ON documents(organization_id);

CREATE INDEX idx_documents_status
    ON documents(organization_id, status);

CREATE INDEX idx_document_versions_document
    ON document_versions(document_id);

CREATE INDEX idx_document_versions_organization
    ON document_versions(organization_id);

CREATE INDEX idx_ingestion_jobs_organization_status
    ON ingestion_jobs(organization_id, status);

CREATE INDEX idx_ingestion_jobs_document
    ON ingestion_jobs(document_id);

CREATE INDEX idx_ingestion_jobs_version
    ON ingestion_jobs(version_id);

COMMIT;
