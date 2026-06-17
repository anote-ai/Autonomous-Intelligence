-- Anote AI — unified database schema
CREATE DATABASE IF NOT EXISTS anote;
USE anote;

CREATE TABLE IF NOT EXISTS users (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    name          VARCHAR(255) DEFAULT '',
    plan          ENUM('free','basic','pro','enterprise') DEFAULT 'free',
    credits       INT DEFAULT 100,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS chats (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    name        VARCHAR(500) DEFAULT 'New Chat',
    mode        ENUM('chat','document','code') DEFAULT 'chat',
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    chat_id     INT NOT NULL,
    role        ENUM('user','assistant','system') NOT NULL,
    content     TEXT NOT NULL,
    model       VARCHAR(100),
    tokens      INT DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documents (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    doc_uuid    VARCHAR(36) NOT NULL UNIQUE,
    filename    VARCHAR(500) NOT NULL,
    chunk_count INT DEFAULT 0,
    created_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_keys (
    id                     INT AUTO_INCREMENT PRIMARY KEY,
    user_id                INT NOT NULL,
    name                   VARCHAR(255) DEFAULT '',
    key_hash               VARCHAR(255) NOT NULL,
    key_prefix             VARCHAR(20) NOT NULL,
    is_active              BOOLEAN NOT NULL DEFAULT TRUE,
    rate_limit_per_minute  INT NOT NULL DEFAULT 60,
    last_used_at           DATETIME,
    expires_at             DATETIME,
    created_at             DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS api_usage_log (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    api_key_id   INT NOT NULL,
    user_id      INT NOT NULL,
    endpoint     VARCHAR(255) NOT NULL,
    status_code  INT NOT NULL,
    credits_used INT NOT NULL DEFAULT 0,
    created_at   DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (api_key_id) REFERENCES api_keys(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS stripe_customers (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL UNIQUE,
    stripe_id   VARCHAR(255) NOT NULL,
    plan        VARCHAR(100),
    status      VARCHAR(50) DEFAULT 'inactive',
    period_end  DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
