-- Create database
CREATE DATABASE IF NOT EXISTS agents CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE agents;

-- Users table (3NF compliant)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    avatar_url VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_login TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    INDEX idx_username (username),
    INDEX idx_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Chats table (3NF compliant)
CREATE TABLE IF NOT EXISTS chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    chat_uuid VARCHAR(36) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    title VARCHAR(255) DEFAULT 'New Chat',
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    last_message_at TIMESTAMP NULL,
    is_archived BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_chat_uuid (chat_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Messages table (3NF compliant)
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    message_id VARCHAR(36) NOT NULL UNIQUE,
    chat_uuid VARCHAR(36) NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    sender_type ENUM('user', 'assistant', 'system') DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    is_edited BOOLEAN DEFAULT FALSE,
    is_deleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (chat_uuid) REFERENCES chats(chat_uuid) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_chat_uuid (chat_uuid),
    INDEX idx_user_id (user_id),
    INDEX idx_message_id (message_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- File types lookup table (new - for normalization)
CREATE TABLE IF NOT EXISTS file_types (
    id INT AUTO_INCREMENT PRIMARY KEY,
    type_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    max_size BIGINT DEFAULT NULL,
    allowed_extensions JSON,
    INDEX idx_type_name (type_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Files table (3NF compliant - removed transitive dependencies)
CREATE TABLE IF NOT EXISTS files (
    id INT AUTO_INCREMENT PRIMARY KEY,
    file_uuid VARCHAR(36) NOT NULL UNIQUE,
    user_id INT NOT NULL,
    chat_uuid VARCHAR(36) NOT NULL,
    message_id VARCHAR(36) NULL,
    original_filename VARCHAR(255) NOT NULL,
    stored_filename VARCHAR(255) NOT NULL UNIQUE,
    file_data LONGBLOB NOT NULL, 
    mime_type VARCHAR(100) NOT NULL,
    file_type_id INT NULL,
    file_size BIGINT NOT NULL,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (chat_uuid) REFERENCES chats(chat_uuid) ON DELETE CASCADE,
    FOREIGN KEY (message_id) REFERENCES messages(message_id) ON DELETE SET NULL,
    FOREIGN KEY (file_type_id) REFERENCES file_types(id) ON DELETE SET NULL,
    INDEX idx_user_id (user_id),
    INDEX idx_chat_uuid (chat_uuid),
    INDEX idx_message_id (message_id),
    INDEX idx_file_uuid (file_uuid),
    INDEX idx_file_type_id (file_type_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User roles table (if needed for authorization)
CREATE TABLE IF NOT EXISTS roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    role_name VARCHAR(50) NOT NULL UNIQUE,
    description VARCHAR(255),
    INDEX idx_role_name (role_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- User-Role mapping (many-to-many)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT NOT NULL,
    role_id INT NOT NULL,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Chat participants (normalized for multi-user chats)
CREATE TABLE IF NOT EXISTS chat_participants (
    chat_id INT NOT NULL,
    user_id INT NOT NULL,
    role_id INT NULL,
    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    left_at TIMESTAMP NULL,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (chat_id, user_id),
    FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Shared chats table for public sharing
CREATE TABLE IF NOT EXISTS shared_chats (
    id INT AUTO_INCREMENT PRIMARY KEY,
    share_uuid VARCHAR(36) NOT NULL UNIQUE,
    chat_uuid VARCHAR(36) NOT NULL,
    user_id INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    view_count INT DEFAULT 0,
    FOREIGN KEY (chat_uuid) REFERENCES chats(chat_uuid) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_share_uuid (share_uuid),
    INDEX idx_chat_uuid (chat_uuid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- -- Insert reference data
INSERT INTO file_types (type_name, description, allowed_extensions) VALUES
('document', 'Document files', '["pdf", "doc", "docx", "txt"]'),
('image', 'Image files', '["jpg", "jpeg", "png", "gif"]'),
('spreadsheet', 'Spreadsheet files', '["xls", "xlsx", "csv"]'),
('presentation', 'Presentation files', '["ppt", "pptx"]');

INSERT INTO roles (role_name, description) VALUES
('admin', 'Administrator with full access'),
('user', 'Regular user'),
('guest', 'Guest with limited access');

-- -- Sample user
-- INSERT INTO users (username, email, password_hash, full_name) VALUES 
-- ('john_doe', 'john@example.com', '$2b$12$hash', 'John Doe');

-- -- Assign default role
-- INSERT INTO user_roles (user_id, role_id) 
-- SELECT u.id, r.id FROM users u, roles r WHERE u.username = 'john_doe' AND r.role_name = 'user';