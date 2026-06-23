-- Governance migration: retention policies, legal holds, export requests, classifications
-- Run after schema.sql and schema_identity.sql

USE anote;

-- Retention / deletion policies per org and data type
CREATE TABLE IF NOT EXISTS data_policies (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    org_id          INT NOT NULL,
    data_type       ENUM('runs','artifacts','logs','prompts','connector_data','documents','chats') NOT NULL,
    retention_days  INT NOT NULL DEFAULT 365,
    auto_delete     TINYINT(1) NOT NULL DEFAULT 0,
    classification  ENUM('public','internal','confidential','sensitive') NOT NULL DEFAULT 'internal',
    created_by      INT DEFAULT NULL,
    updated_by      INT DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uq_org_data_type (org_id, data_type),
    FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Legal hold records — prevent deletion of governed resources
CREATE TABLE IF NOT EXISTS legal_holds (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    org_id          INT NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     VARCHAR(255) NOT NULL,
    reason          TEXT NOT NULL,
    placed_by       INT DEFAULT NULL,
    released_by     INT DEFAULT NULL,
    released_at     DATETIME DEFAULT NULL,
    expires_at      DATETIME DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_legal_holds_resource (org_id, resource_type, resource_id),
    FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Data export request queue
CREATE TABLE IF NOT EXISTS export_requests (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    org_id          INT NOT NULL,
    requested_by    INT NOT NULL,
    data_types      JSON NOT NULL,
    scope           JSON DEFAULT NULL,
    status          ENUM('pending','processing','ready','fulfilled','failed') NOT NULL DEFAULT 'pending',
    download_url    VARCHAR(2000) DEFAULT NULL,
    fulfilled_by    INT DEFAULT NULL,
    fulfilled_at    DATETIME DEFAULT NULL,
    expires_at      DATETIME DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Per-resource data classification tags
CREATE TABLE IF NOT EXISTS resource_classifications (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    org_id          INT NOT NULL,
    resource_type   VARCHAR(100) NOT NULL,
    resource_id     VARCHAR(255) NOT NULL,
    classification  ENUM('public','internal','confidential','sensitive') NOT NULL DEFAULT 'internal',
    tagged_by       INT DEFAULT NULL,
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_org_resource (org_id, resource_type, resource_id),
    FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
);

-- Governance-specific audit trail
CREATE TABLE IF NOT EXISTS governance_audit_log (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    org_id      INT NOT NULL,
    actor_id    INT DEFAULT NULL,
    action      VARCHAR(100) NOT NULL,
    resource    VARCHAR(255) DEFAULT NULL,
    detail      JSON DEFAULT NULL,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (org_id) REFERENCES organizations(id) ON DELETE CASCADE
);
