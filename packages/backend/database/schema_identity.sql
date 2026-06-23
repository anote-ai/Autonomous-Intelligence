-- Identity migration: SSO, SCIM, organizations, roles, audit log
-- Run once against the anote database after schema.sql

USE anote;

-- Extend users with SSO and account-state columns
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS sso_provider  VARCHAR(50)  DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS sso_id        VARCHAR(500) DEFAULT NULL,
    ADD COLUMN IF NOT EXISTS mfa_enabled   TINYINT(1)   DEFAULT 0,
    ADD COLUMN IF NOT EXISTS is_active     TINYINT(1)   DEFAULT 1;

CREATE TABLE IF NOT EXISTS organizations (
    id                 INT AUTO_INCREMENT PRIMARY KEY,
    name               VARCHAR(255)  NOT NULL,
    slug               VARCHAR(100)  NOT NULL,
    domain             VARCHAR(255)  DEFAULT NULL,
    sso_provider       ENUM('okta','azure','google','generic') DEFAULT NULL,
    sso_client_id      VARCHAR(500)  DEFAULT NULL,
    sso_client_secret  VARCHAR(500)  DEFAULT NULL,
    sso_discovery_url  VARCHAR(1000) DEFAULT NULL,
    mfa_required       TINYINT(1)    DEFAULT 0,
    scim_token_hash    VARCHAR(255)  DEFAULT NULL,
    created_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_org_slug (slug)
);

CREATE TABLE IF NOT EXISTS organization_members (
    id               INT AUTO_INCREMENT PRIMARY KEY,
    org_id           INT          NOT NULL,
    user_id          INT          NOT NULL,
    role             ENUM('admin','member','viewer') DEFAULT 'member',
    provisioned_by   ENUM('manual','scim','sso')    DEFAULT 'manual',
    scim_external_id VARCHAR(255) DEFAULT NULL,
    created_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_org_user (org_id, user_id),
    FOREIGN KEY (org_id)  REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id)         ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS identity_audit_log (
    id         INT AUTO_INCREMENT PRIMARY KEY,
    org_id     INT          DEFAULT NULL,
    user_id    INT          DEFAULT NULL,
    event_type VARCHAR(100) NOT NULL,
    actor      VARCHAR(255) DEFAULT NULL,
    detail     JSON         DEFAULT NULL,
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (org_id)  REFERENCES organizations(id) ON DELETE SET NULL,
    FOREIGN KEY (user_id) REFERENCES users(id)         ON DELETE SET NULL
);
