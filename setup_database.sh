#!/bin/bash

# =====================================================
# GenAI Coach Backend - Database Setup Script
# =====================================================
# Description: Sets up MySQL database schema on Railway
# Usage: ./setup_database.sh
# =====================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# =====================================================
# Configuration
# =====================================================

# Railway MySQL Connection (from your environment)
MYSQL_URL="mysql://root:tTAhOqSOcqIFcTUygPFvaRJowmMPadgn@shortline.proxy.rlwy.net:52538/railway"

# Parse connection details
MYSQL_USER=$(echo $MYSQL_URL | sed -n 's|.*://\([^:]*\):.*|\1|p')
MYSQL_PASSWORD=$(echo $MYSQL_URL | sed -n 's|.*://[^:]*:\([^@]*\)@.*|\1|p')
MYSQL_HOST=$(echo $MYSQL_URL | sed -n 's|.*@\([^:]*\):.*|\1|p')
MYSQL_PORT=$(echo $MYSQL_URL | sed -n 's|.*:\([0-9]*\)/.*|\1|p')
MYSQL_DATABASE=$(echo $MYSQL_URL | sed -n 's|.*/\([^?]*\).*|\1|p')

SCHEMA_FILE="schema.sql"

# =====================================================
# Pre-flight Checks
# =====================================================

print_header "GenAI Coach - Database Setup"

print_info "Checking prerequisites..."

# Check if mysql client is installed
if ! command -v mysql &> /dev/null; then
    print_error "MySQL client not found!"
    print_info "Install it with:"
    print_info "  macOS: brew install mysql-client"
    print_info "  Ubuntu/Debian: sudo apt-get install mysql-client"
    print_info "  CentOS/RHEL: sudo yum install mysql"
    exit 1
fi

print_success "MySQL client found: $(mysql --version | head -n1)"

# Check if schema file exists
if [ ! -f "$SCHEMA_FILE" ]; then
    print_error "Schema file not found: $SCHEMA_FILE"
    exit 1
fi

print_success "Schema file found: $SCHEMA_FILE"

# =====================================================
# Connection Details
# =====================================================

print_header "Connection Details"

echo "Host:     $MYSQL_HOST"
echo "Port:     $MYSQL_PORT"
echo "User:     $MYSQL_USER"
echo "Database: $MYSQL_DATABASE"
echo "Password: ${MYSQL_PASSWORD:0:5}***"

# =====================================================
# Test Connection
# =====================================================

print_header "Testing Database Connection"

if mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" -e "SELECT 1;" &> /dev/null; then
    print_success "Connection successful!"
else
    print_error "Failed to connect to database!"
    print_info "Please check your connection details and network access."
    exit 1
fi

# =====================================================
# Backup Existing Schema (Optional)
# =====================================================

print_header "Backup Check"

BACKUP_FILE="backup_$(date +%Y%m%d_%H%M%S).sql"

print_info "Checking if tables exist..."

EXISTING_TABLES=$(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;" 2>/dev/null | wc -l)

if [ "$EXISTING_TABLES" -gt 1 ]; then
    print_warning "Found existing tables in database."
    echo -n "Create backup before proceeding? (y/n) [y]: "
    read -r CREATE_BACKUP
    CREATE_BACKUP=${CREATE_BACKUP:-y}

    if [[ "$CREATE_BACKUP" =~ ^[Yy]$ ]]; then
        print_info "Creating backup: $BACKUP_FILE"
        mysqldump -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" > "$BACKUP_FILE" 2>/dev/null
        print_success "Backup created: $BACKUP_FILE"
    fi
else
    print_info "No existing tables found. Skipping backup."
fi

# =====================================================
# Confirmation
# =====================================================

print_header "Confirmation"

print_warning "This will DROP and RECREATE all tables!"
echo -n "Are you sure you want to continue? (yes/no) [no]: "
read -r CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    print_info "Operation cancelled."
    exit 0
fi

# =====================================================
# Execute Schema
# =====================================================

print_header "Executing Schema"

print_info "Running schema.sql..."

if mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" < "$SCHEMA_FILE"; then
    print_success "Schema executed successfully!"
else
    print_error "Failed to execute schema!"
    exit 1
fi

# =====================================================
# Verification
# =====================================================

print_header "Verification"

print_info "Verifying tables..."

TABLES=$(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SHOW TABLES;" 2>/dev/null | tail -n +2)

if [ -z "$TABLES" ]; then
    print_error "No tables found after schema execution!"
    exit 1
fi

print_success "Tables created:"
echo "$TABLES" | while read -r table; do
    echo "  • $table"
done

# Count records in each table
print_info "\nTable statistics:"
for table in $TABLES; do
    COUNT=$(mysql -h"$MYSQL_HOST" -P"$MYSQL_PORT" -u"$MYSQL_USER" -p"$MYSQL_PASSWORD" "$MYSQL_DATABASE" -e "SELECT COUNT(*) FROM \`$table\`;" 2>/dev/null | tail -n +2)
    echo "  • $table: $COUNT rows"
done

# =====================================================
# Success
# =====================================================

print_header "Setup Complete"

print_success "Database schema setup completed successfully!"

print_info "\nNext steps:"
echo "  1. Update your .env file with the database URL"
echo "  2. Test the connection: mysql -h$MYSQL_HOST -P$MYSQL_PORT -u$MYSQL_USER -p$MYSQL_PASSWORD $MYSQL_DATABASE"
echo "  3. Deploy your application to Railway"

print_info "\nDatabase URL for .env:"
echo "  DATABASE_URL=\"mysql+aiomysql://root:$MYSQL_PASSWORD@$MYSQL_HOST:$MYSQL_PORT/$MYSQL_DATABASE\""

print_info "\nBackup file (if created): $BACKUP_FILE"

echo ""
