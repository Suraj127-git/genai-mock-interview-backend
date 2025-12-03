# Database Setup Guide

This guide explains how to set up the MySQL database schema for the GenAI Coach Backend.

## Overview

The database consists of three main tables:
- **users**: User authentication and profiles
- **interview_sessions**: Interview practice sessions with AI feedback
- **uploads**: File upload tracking (audio recordings)

## Quick Start

### Prerequisites

- MySQL client installed
  - **macOS**: `brew install mysql-client`
  - **Ubuntu/Debian**: `sudo apt-get install mysql-client`
  - **CentOS/RHEL**: `sudo yum install mysql`

### Automated Setup (Recommended)

Run the setup script to automatically create the database schema:

```bash
cd genai-coach-backend
./setup_database.sh
```

The script will:
1. ✅ Check prerequisites (MySQL client)
2. ✅ Test database connection
3. ✅ Offer to backup existing tables
4. ✅ Execute schema.sql
5. ✅ Verify table creation
6. ✅ Display table statistics

### Manual Setup

If you prefer to run SQL commands manually:

```bash
# Connect to Railway MySQL
mysql -h shortline.proxy.rlwy.net \
      -P 52538 \
      -u root \
      -p \
      railway

# Then run the schema file
source schema.sql;
```

Or execute in one command:

```bash
mysql -h shortline.proxy.rlwy.net -P 52538 -u root -p railway < schema.sql
```

## Database Schema Details

### Table: `users`

Stores user authentication and profile information.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT UNSIGNED | Primary key (auto-increment) |
| `email` | VARCHAR(255) | User email (unique, indexed) |
| `name` | VARCHAR(255) | User display name (nullable) |
| `hashed_password` | VARCHAR(255) | Bcrypt hashed password |
| `is_active` | TINYINT(1) | Account active status |
| `created_at` | DATETIME(6) | Account creation timestamp |
| `updated_at` | DATETIME(6) | Last update timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- UNIQUE KEY on `email`
- INDEX on `email`
- INDEX on `is_active`

**Best Practices:**
- Passwords are hashed with bcrypt (cost factor 12)
- Email is unique and indexed for fast lookups
- Soft delete via `is_active` flag
- Automatic timestamps with timezone support

---

### Table: `interview_sessions`

Stores interview practice sessions with AI-generated feedback and scores.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT UNSIGNED | Primary key (auto-increment) |
| `user_id` | INT UNSIGNED | Foreign key to users.id |
| `title` | VARCHAR(255) | Session title/name |
| `question` | TEXT | Interview question asked |
| `transcript` | MEDIUMTEXT | Speech-to-text transcript |
| `audio_s3_key` | VARCHAR(500) | S3/Storage key for audio file |
| `duration_seconds` | INT | Session duration in seconds |
| `overall_score` | DECIMAL(4,2) | Overall performance (0-10) |
| `communication_score` | DECIMAL(4,2) | Communication skills (0-10) |
| `technical_score` | DECIMAL(4,2) | Technical accuracy (0-10) |
| `clarity_score` | DECIMAL(4,2) | Clarity and structure (0-10) |
| `strengths` | JSON | Array of identified strengths |
| `improvements` | JSON | Array of improvement areas |
| `detailed_feedback` | MEDIUMTEXT | AI-generated detailed feedback |
| `created_at` | DATETIME(6) | Session start timestamp |
| `updated_at` | DATETIME(6) | Last update timestamp |
| `completed_at` | DATETIME(6) | Session completion timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY on `user_id` → `users.id` (CASCADE)
- INDEX on `user_id`
- INDEX on `created_at`
- INDEX on `completed_at`
- COMPOSITE INDEX on (`user_id`, `created_at` DESC)

**Best Practices:**
- JSON columns for flexible feedback structure
- MEDIUMTEXT for large transcripts (up to 16MB)
- Decimal(4,2) for precise score storage (e.g., 8.75)
- Cascade delete: deleting a user removes their sessions
- Composite index optimizes "user's recent sessions" queries

**Example JSON Data:**

```json
// strengths
["Clear articulation of technical concepts", "Good use of examples", "Confident delivery"]

// improvements
["Add more specific metrics", "Better time management", "Reduce filler words"]
```

---

### Table: `uploads`

Tracks file uploads to S3 or Railway Object Storage.

| Column | Type | Description |
|--------|------|-------------|
| `id` | INT UNSIGNED | Primary key (auto-increment) |
| `user_id` | INT UNSIGNED | Foreign key to users.id |
| `s3_key` | VARCHAR(500) | Unique S3/Storage key |
| `content_type` | VARCHAR(100) | MIME type (e.g., audio/webm) |
| `file_size` | BIGINT UNSIGNED | File size in bytes |
| `uploaded_at` | DATETIME(6) | Upload timestamp |
| `confirmed_at` | DATETIME(6) | Confirmation timestamp |

**Indexes:**
- PRIMARY KEY on `id`
- FOREIGN KEY on `user_id` → `users.id` (CASCADE)
- UNIQUE KEY on `s3_key`
- INDEX on `user_id`
- INDEX on `s3_key`
- INDEX on `uploaded_at`
- COMPOSITE INDEX on (`user_id`, `uploaded_at` DESC)

**Best Practices:**
- Unique constraint on `s3_key` prevents duplicates
- BIGINT for file_size supports files up to ~9 exabytes
- Separate upload and confirmation timestamps for reliability
- Cascade delete: deleting a user removes their upload records

---

## Database Configuration

### Character Set & Collation

```sql
ENGINE=InnoDB
DEFAULT CHARSET=utf8mb4
COLLATE=utf8mb4_unicode_ci
```

**Why `utf8mb4`?**
- Full Unicode support (including emojis 😊)
- Required for international names and text
- Industry standard for modern applications

**Why `utf8mb4_unicode_ci`?**
- Case-insensitive comparisons
- Better sorting for international characters
- More accurate than `utf8mb4_general_ci`

### Storage Engine

**InnoDB Features:**
- ✅ ACID transactions (data integrity)
- ✅ Foreign key constraints
- ✅ Row-level locking (better concurrency)
- ✅ Crash recovery
- ✅ Better for read/write workloads

### Timestamp Precision

All timestamps use `DATETIME(6)` for microsecond precision:
- Supports: `2025-12-04 12:34:56.123456`
- Compatible with Python's `datetime.now()`
- Essential for accurate duration calculations

## Environment Variables

After setup, configure your application:

```bash
# .env file
DATABASE_URL="mysql+aiomysql://root:tTAhOqSOcqIFcTUygPFvaRJowmMPadgn@shortline.proxy.rlwy.net:52538/railway"
```

**Note:** Use `mysql+aiomysql://` prefix for async SQLAlchemy compatibility.

## Backup & Restore

### Create Backup

```bash
mysqldump -h shortline.proxy.rlwy.net \
          -P 52538 \
          -u root \
          -p \
          railway > backup_$(date +%Y%m%d).sql
```

### Restore from Backup

```bash
mysql -h shortline.proxy.rlwy.net \
      -P 52538 \
      -u root \
      -p \
      railway < backup_20251204.sql
```

## Common Operations

### Check Table Structure

```sql
DESCRIBE users;
DESCRIBE interview_sessions;
DESCRIBE uploads;
```

### View Indexes

```sql
SHOW INDEX FROM interview_sessions;
```

### Table Statistics

```sql
SELECT
    table_name,
    table_rows,
    ROUND(data_length / 1024 / 1024, 2) AS 'Size (MB)',
    ROUND(index_length / 1024 / 1024, 2) AS 'Index Size (MB)'
FROM information_schema.tables
WHERE table_schema = 'railway';
```

### Sample Queries

```sql
-- Recent sessions for a user
SELECT * FROM interview_sessions
WHERE user_id = 1
ORDER BY created_at DESC
LIMIT 10;

-- Average scores by user
SELECT
    user_id,
    COUNT(*) as total_sessions,
    AVG(overall_score) as avg_score
FROM interview_sessions
GROUP BY user_id;

-- User's storage usage
SELECT
    u.email,
    COUNT(up.id) as file_count,
    SUM(up.file_size) / 1024 / 1024 as total_mb
FROM users u
LEFT JOIN uploads up ON u.id = up.user_id
GROUP BY u.id, u.email;
```

## Troubleshooting

### Connection Issues

**Problem:** Cannot connect to Railway MySQL

**Solution:**
1. Check if IP is whitelisted on Railway dashboard
2. Verify credentials are correct
3. Test with: `mysql -h shortline.proxy.rlwy.net -P 52538 -u root -p`

### Character Encoding Issues

**Problem:** Emojis or special characters not displaying

**Solution:**
```sql
ALTER DATABASE railway CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
ALTER TABLE users CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

### Slow Queries

**Problem:** Queries taking too long

**Solution:**
1. Check if indexes exist: `SHOW INDEX FROM table_name;`
2. Analyze query: `EXPLAIN SELECT ...;`
3. Add missing indexes based on WHERE/ORDER BY clauses

## Security Best Practices

1. ✅ **Never commit credentials** - Use environment variables
2. ✅ **Use strong passwords** - Min 16 chars, mixed case, numbers, symbols
3. ✅ **Limit database user permissions** - Only grant necessary privileges
4. ✅ **Enable SSL connections** - Encrypt data in transit
5. ✅ **Regular backups** - Automate daily backups
6. ✅ **Audit logs** - Monitor database access
7. ✅ **Parameterized queries** - Prevent SQL injection (SQLAlchemy handles this)

## Performance Optimization

### Index Strategy

- ✅ Primary keys on all tables
- ✅ Foreign keys indexed
- ✅ Unique constraints on email, s3_key
- ✅ Composite indexes for common queries
- ✅ Timestamp columns indexed for sorting

### Query Optimization

```python
# Good: Uses index on user_id
sessions = await db.execute(
    select(InterviewSession)
    .where(InterviewSession.user_id == user_id)
    .order_by(InterviewSession.created_at.desc())
    .limit(10)
)

# Bad: Full table scan
sessions = await db.execute(
    select(InterviewSession)
    .where(InterviewSession.title.like('%interview%'))
)
```

## Migration Strategy

For future schema changes, use Alembic:

```bash
# Create migration
alembic revision --autogenerate -m "Add new column"

# Apply migration
alembic upgrade head

# Rollback
alembic downgrade -1
```

## Support

For issues or questions:
1. Check Railway logs: `railway logs`
2. Test connection: `mysql -h ... -u ... -p`
3. Review application logs for SQL errors
4. Check Railway dashboard for database metrics

---

**Last Updated:** 2025-12-04
**Schema Version:** 1.0.0
**Database:** MySQL 8.0+ (Railway)
