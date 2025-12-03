-- =====================================================
-- GenAI Coach Backend - MySQL Database Schema
-- =====================================================
-- Description: Database schema for AI-powered mock interview coach
-- Version: 1.0.0
-- Created: 2025-12-04
-- =====================================================

-- Set character set and collation for proper UTF-8 support
SET NAMES utf8mb4;
SET CHARACTER SET utf8mb4;

-- Drop existing tables if they exist (in correct order due to foreign keys)
DROP TABLE IF EXISTS `uploads`;
DROP TABLE IF EXISTS `interview_sessions`;
DROP TABLE IF EXISTS `users`;

-- =====================================================
-- Table: users
-- =====================================================
-- Description: Stores user authentication and profile information
-- Indexes: email (unique), id (primary key)
-- =====================================================

CREATE TABLE `users` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `email` VARCHAR(255) NOT NULL,
    `name` VARCHAR(255) DEFAULT NULL,
    `hashed_password` VARCHAR(255) NOT NULL,
    `is_active` TINYINT(1) NOT NULL DEFAULT 1,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_users_email` (`email`),
    KEY `idx_users_email` (`email`),
    KEY `idx_users_is_active` (`is_active`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='User authentication and profile management';

-- =====================================================
-- Table: interview_sessions
-- =====================================================
-- Description: Stores interview practice session data with AI feedback
-- Indexes: user_id (foreign key), created_at, id (primary key)
-- =====================================================

CREATE TABLE `interview_sessions` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` INT UNSIGNED NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `question` TEXT DEFAULT NULL,
    `transcript` MEDIUMTEXT DEFAULT NULL,
    `audio_s3_key` VARCHAR(500) DEFAULT NULL,
    `duration_seconds` INT DEFAULT NULL,

    -- Feedback scores (0.0 to 10.0)
    `overall_score` DECIMAL(4,2) DEFAULT NULL,
    `communication_score` DECIMAL(4,2) DEFAULT NULL,
    `technical_score` DECIMAL(4,2) DEFAULT NULL,
    `clarity_score` DECIMAL(4,2) DEFAULT NULL,

    -- Detailed feedback (JSON format)
    `strengths` JSON DEFAULT NULL,
    `improvements` JSON DEFAULT NULL,
    `detailed_feedback` MEDIUMTEXT DEFAULT NULL,

    -- Timestamps
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `completed_at` DATETIME(6) DEFAULT NULL,

    PRIMARY KEY (`id`),
    KEY `idx_sessions_user_id` (`user_id`),
    KEY `idx_sessions_created_at` (`created_at`),
    KEY `idx_sessions_completed_at` (`completed_at`),

    CONSTRAINT `fk_sessions_user_id`
        FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='Interview practice sessions with AI feedback';

-- =====================================================
-- Table: uploads
-- =====================================================
-- Description: Tracks audio and file uploads to S3/Railway Object Storage
-- Indexes: user_id (foreign key), s3_key (unique), id (primary key)
-- =====================================================

CREATE TABLE `uploads` (
    `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
    `user_id` INT UNSIGNED NOT NULL,
    `s3_key` VARCHAR(500) NOT NULL,
    `content_type` VARCHAR(100) NOT NULL,
    `file_size` BIGINT UNSIGNED DEFAULT NULL,
    `uploaded_at` DATETIME(6) NOT NULL,
    `confirmed_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (`id`),
    UNIQUE KEY `uq_uploads_s3_key` (`s3_key`),
    KEY `idx_uploads_user_id` (`user_id`),
    KEY `idx_uploads_s3_key` (`s3_key`),
    KEY `idx_uploads_uploaded_at` (`uploaded_at`),

    CONSTRAINT `fk_uploads_user_id`
        FOREIGN KEY (`user_id`)
        REFERENCES `users` (`id`)
        ON DELETE CASCADE
        ON UPDATE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='File upload tracking for S3/Railway Object Storage';

-- =====================================================
-- Indexes for Performance Optimization
-- =====================================================

-- Composite index for common queries: user sessions by date
CREATE INDEX `idx_sessions_user_created` ON `interview_sessions` (`user_id`, `created_at` DESC);

-- Composite index for user uploads by date
CREATE INDEX `idx_uploads_user_uploaded` ON `uploads` (`user_id`, `uploaded_at` DESC);

-- =====================================================
-- Initial Data (Optional)
-- =====================================================

-- Example: Insert a system user for testing (password: Test123!)
-- Password hash generated with bcrypt
-- INSERT INTO `users` (`email`, `name`, `hashed_password`, `is_active`)
-- VALUES ('test@example.com', 'Test User', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYIvAprzZ3.', 1);

-- =====================================================
-- Database Information
-- =====================================================

SELECT
    'Schema created successfully!' AS status,
    DATABASE() AS database_name,
    VERSION() AS mysql_version,
    NOW() AS created_at;

-- Show all tables
SHOW TABLES;

-- Show table structure
DESCRIBE `users`;
DESCRIBE `interview_sessions`;
DESCRIBE `uploads`;
