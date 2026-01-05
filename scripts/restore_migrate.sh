#!/bin/bash
# =============================================================================
# Restore & Run OpenUpgrade Migration Script for Odoo 17
# =============================================================================
# This script:
# 1. Drops existing isalab database (from previous migration)
# 2. Creates new database from template or backup
# 3. Runs OpenUpgrade migration command with live log
# 4. Creates backup for next version migration (isalab17_for_v18_xxx)
# =============================================================================

set -euo pipefail

# Configuration
VERSION="17"
NEXT_VERSION="18"
BACKUP_DIR="/opt/odoo/backups"
BACKUP_PATTERN="isalab16_for_v${VERSION}_"
TEMPLATE_DB="isalab16_for_v${VERSION}_T"
TARGET_DB="isalab"
PG_USER="odoo"
PG_PASSWORD="odoo"

# Odoo paths
ODOO_DIR="/opt/odoo/isalab${VERSION}"
VENV_DIR="${ODOO_DIR}/venv_isalab${VERSION}"
MIGRATE_CFG="${ODOO_DIR}/config/myodoo${VERSION}_migrate.cfg"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

print_header() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  🔄 Odoo ${VERSION} - OpenUpgrade Migration Tool${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_info() {
    echo -e "  ${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "  ${RED}❌ $1${NC}"
}

print_step() {
    echo ""
    echo -e "  ${MAGENTA}▶ STEP $1: $2${NC}"
    echo ""
}

# Check if database exists
db_exists() {
    sudo -u postgres psql -lqt | cut -d \| -f 1 | grep -qw "$1"
}

# Drop database if exists
drop_db() {
    local db_name="$1"
    if db_exists "$db_name"; then
        print_warning "Dropping existing database: $db_name"
        sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$db_name';" > /dev/null 2>&1 || true
        sudo -u postgres dropdb "$db_name"
        print_success "Database dropped: $db_name"
    else
        print_info "Database does not exist: $db_name"
    fi
}

# Create template from existing isalab database (from previous migration)
create_template_from_isalab() {
    print_info "Creating template from existing '${TARGET_DB}' database..."
    echo -e "    Source: ${YELLOW}${TARGET_DB}${NC}"
    echo -e "    Target: ${YELLOW}${TEMPLATE_DB}${NC}"
    echo ""
    
    # Drop existing template if exists
    drop_db "$TEMPLATE_DB"
    
    # Disconnect all sessions from source
    sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TARGET_DB';" > /dev/null 2>&1 || true
    
    # Create template from isalab
    print_info "Copying database (this may take a while)..."
    sudo -u postgres createdb -T "$TARGET_DB" -O "$PG_USER" "$TEMPLATE_DB"
    
    print_success "Template created: $TEMPLATE_DB (from existing $TARGET_DB)"
}

# List available backups
list_backups() {
    echo ""
    echo -e "  ${CYAN}📦 Available Migration Backups:${NC}"
    echo ""
    
    local i=1
    BACKUP_LIST=()
    
    for dir in "$BACKUP_DIR"/${BACKUP_PATTERN}*/; do
        if [ -d "$dir" ]; then
            local backup_name=$(basename "$dir")
            local backup_file=$(find "$dir" -name "*.backup" -o -name "*.dump" 2>/dev/null | head -1)
            
            if [ -n "$backup_file" ]; then
                local size=$(du -h "$backup_file" 2>/dev/null | cut -f1)
                local date_part=$(echo "$backup_name" | grep -oP '\d{8}_\d{6}' | head -1)
                
                if [ -n "$date_part" ]; then
                    local formatted_date="${date_part:0:4}-${date_part:4:2}-${date_part:6:2} ${date_part:9:2}:${date_part:11:2}"
                else
                    formatted_date="Unknown"
                fi
                
                BACKUP_LIST+=("$backup_file")
                printf "    ${GREEN}[%d]${NC} %s ${YELLOW}(%s)${NC} - %s\n" "$i" "$backup_name" "$size" "$formatted_date"
                ((i++))
            fi
        fi
    done
    
    if [ ${#BACKUP_LIST[@]} -eq 0 ]; then
        print_error "No backups found matching pattern: ${BACKUP_PATTERN}*"
        return 1
    fi
    
    echo ""
    return 0
}

# Restore backup to template database
restore_to_template() {
    local backup_file="$1"
    
    print_info "Restoring backup to template database..."
    echo -e "    Backup: ${YELLOW}$(basename "$backup_file")${NC}"
    echo -e "    Target: ${YELLOW}${TEMPLATE_DB}${NC}"
    echo ""
    
    # Drop existing template if exists
    drop_db "$TEMPLATE_DB"
    
    # Create empty database
    print_info "Creating template database..."
    sudo -u postgres createdb -O "$PG_USER" "$TEMPLATE_DB"
    
    # Restore: --no-owner prevents dump's ownership from being applied
    # --role sets the role for object creation when running as superuser
    print_info "Restoring backup (this may take a while)..."
    
    local restore_log=$(mktemp)
    local restore_exit=0
    sudo -u postgres pg_restore -d "$TEMPLATE_DB" --no-owner --no-privileges --role="$PG_USER" "$backup_file" 2>"$restore_log" || restore_exit=$?
    
    if [ $restore_exit -ne 0 ]; then
        if grep -q "FATAL\|could not connect\|database.*does not exist" "$restore_log"; then
            print_error "Database restore failed!"
            cat "$restore_log"
            rm -f "$restore_log"
            return 1
        else
            print_warning "Restore completed with warnings"
        fi
    else
        print_success "Restore completed"
    fi
    rm -f "$restore_log"
    
    # Check ownership BEFORE fixing - only fix if needed
    print_info "Verifying ownership..."
    
    local db_owner=$(sudo -u postgres psql -t -c "SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname='$TEMPLATE_DB';" | tr -d ' ')
    local schema_owner=$(sudo -u postgres psql -d "$TEMPLATE_DB" -t -c "SELECT r.rolname FROM pg_namespace n JOIN pg_roles r ON r.oid = n.nspowner WHERE n.nspname = 'public';" | tr -d ' ')
    local wrong_count=$(sudo -u postgres psql -d "$TEMPLATE_DB" -t -c "
        SELECT count(*) FROM (
            SELECT tablename FROM pg_tables WHERE schemaname='public' AND tableowner != '$PG_USER'
            UNION ALL
            SELECT sequencename FROM pg_sequences WHERE schemaname='public' AND sequenceowner != '$PG_USER'
        ) AS wrong_owners;" | tr -d ' ')
    
    if [ "$db_owner" != "$PG_USER" ] || [ "$schema_owner" != "$PG_USER" ] || [ "${wrong_count:-0}" -gt 0 ]; then
        print_warning "Ownership issues detected (db:$db_owner, schema:$schema_owner, objects:$wrong_count)"
        print_info "Fixing ownership..."
        
        [ "$db_owner" != "$PG_USER" ] && sudo -u postgres psql -q -c "ALTER DATABASE \"$TEMPLATE_DB\" OWNER TO $PG_USER;"
        
        if [ "$schema_owner" != "$PG_USER" ] || [ "${wrong_count:-0}" -gt 0 ]; then
            sudo -u postgres psql -d "$TEMPLATE_DB" -q << EOSQL
ALTER SCHEMA public OWNER TO $PG_USER;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner != '$PG_USER'
    LOOP EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' AND sequenceowner != '$PG_USER'
    LOOP EXECUTE 'ALTER SEQUENCE public.' || quote_ident(r.sequencename) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT viewname FROM pg_views WHERE schemaname = 'public' AND viewowner != '$PG_USER'
    LOOP EXECUTE 'ALTER VIEW public.' || quote_ident(r.viewname) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT matviewname FROM pg_matviews WHERE schemaname = 'public' AND matviewowner != '$PG_USER'
    LOOP EXECUTE 'ALTER MATERIALIZED VIEW public.' || quote_ident(r.matviewname) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
EOSQL
        fi
        
        wrong_count=$(sudo -u postgres psql -d "$TEMPLATE_DB" -t -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner != '$PG_USER';" | tr -d ' ')
        if [ "${wrong_count:-0}" -eq 0 ]; then
            print_success "Template database created: $TEMPLATE_DB (ownership fixed ✓)"
        else
            print_warning "Template created but $wrong_count objects still have wrong owner"
        fi
    else
        print_success "Template database created: $TEMPLATE_DB (ownership already correct ✓)"
    fi
}

# Create target database from template
create_from_template() {
    print_info "Creating database from template..."
    echo -e "    Template: ${YELLOW}${TEMPLATE_DB}${NC}"
    echo -e "    Target:   ${YELLOW}${TARGET_DB}${NC}"
    echo ""
    
    # Drop existing target if exists
    drop_db "$TARGET_DB"
    
    # Disconnect all sessions from template
    sudo -u postgres psql -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$TEMPLATE_DB';" > /dev/null 2>&1 || true
    
    # Create from template
    sudo -u postgres createdb -T "$TEMPLATE_DB" -O "$PG_USER" "$TARGET_DB"
    
    # Fix: Drop sequences that conflict with Odoo registry setup
    # These exist in older databases and cause "already exists" error
    # Note: Safe when Odoo processes are stopped and db_user has correct permissions
    print_info "Cleaning up legacy sequences..."
    sudo -u postgres psql -d "$TARGET_DB" -c "DROP SEQUENCE IF EXISTS base_registry_signaling CASCADE;" > /dev/null 2>&1 || true
    sudo -u postgres psql -d "$TARGET_DB" -c "DROP SEQUENCE IF EXISTS base_cache_signaling CASCADE;" > /dev/null 2>&1 || true
    
    # Check ownership BEFORE fixing - only fix if needed
    print_info "Verifying ownership..."
    
    local db_owner=$(sudo -u postgres psql -t -c "SELECT pg_catalog.pg_get_userbyid(datdba) FROM pg_database WHERE datname='$TARGET_DB';" | tr -d ' ')
    local schema_owner=$(sudo -u postgres psql -d "$TARGET_DB" -t -c "SELECT r.rolname FROM pg_namespace n JOIN pg_roles r ON r.oid = n.nspowner WHERE n.nspname = 'public';" | tr -d ' ')
    local wrong_count=$(sudo -u postgres psql -d "$TARGET_DB" -t -c "
        SELECT count(*) FROM (
            SELECT tablename FROM pg_tables WHERE schemaname='public' AND tableowner != '$PG_USER'
            UNION ALL
            SELECT sequencename FROM pg_sequences WHERE schemaname='public' AND sequenceowner != '$PG_USER'
        ) AS wrong_owners;" | tr -d ' ')
    
    if [ "$db_owner" != "$PG_USER" ] || [ "$schema_owner" != "$PG_USER" ] || [ "${wrong_count:-0}" -gt 0 ]; then
        print_warning "Ownership issues detected (db:$db_owner, schema:$schema_owner, objects:$wrong_count)"
        print_info "Fixing ownership..."
        
        [ "$db_owner" != "$PG_USER" ] && sudo -u postgres psql -q -c "ALTER DATABASE \"$TARGET_DB\" OWNER TO $PG_USER;"
        
        if [ "$schema_owner" != "$PG_USER" ] || [ "${wrong_count:-0}" -gt 0 ]; then
            sudo -u postgres psql -d "$TARGET_DB" -q << EOSQL
ALTER SCHEMA public OWNER TO $PG_USER;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tableowner != '$PG_USER'
    LOOP EXECUTE 'ALTER TABLE public.' || quote_ident(r.tablename) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT sequencename FROM pg_sequences WHERE schemaname = 'public' AND sequenceowner != '$PG_USER'
    LOOP EXECUTE 'ALTER SEQUENCE public.' || quote_ident(r.sequencename) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT viewname FROM pg_views WHERE schemaname = 'public' AND viewowner != '$PG_USER'
    LOOP EXECUTE 'ALTER VIEW public.' || quote_ident(r.viewname) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
DO \$\$ DECLARE r RECORD;
BEGIN
    FOR r IN SELECT matviewname FROM pg_matviews WHERE schemaname = 'public' AND matviewowner != '$PG_USER'
    LOOP EXECUTE 'ALTER MATERIALIZED VIEW public.' || quote_ident(r.matviewname) || ' OWNER TO $PG_USER'; END LOOP;
END \$\$;
EOSQL
        fi
        
        wrong_count=$(sudo -u postgres psql -d "$TARGET_DB" -t -c "SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tableowner != '$PG_USER';" | tr -d ' ')
        if [ "${wrong_count:-0}" -eq 0 ]; then
            print_success "Database created: $TARGET_DB (from template, ownership fixed ✓)"
        else
            print_warning "Database created but $wrong_count tables still have wrong owner"
        fi
    else
        print_success "Database created: $TARGET_DB (from template, ownership already correct ✓)"
    fi
}

# Setup OpenUpgrade and dependencies
setup_openupgrade() {
    print_step "SETUP" "Checking OpenUpgrade Prerequisites"
    
    local OPENUPGRADE_DIR="${ODOO_DIR}/OpenUpgrade"
    local CUSTOM_SCRIPTS_DIR="${ODOO_DIR}/custom_migration_scripts"
    local CUSTOM_SOURCE="/opt/odoo/isalab${VERSION}-custom/custom_migration_scripts"
    
    # Check/Clone OpenUpgrade
    if [ ! -d "$OPENUPGRADE_DIR" ]; then
        print_warning "OpenUpgrade not found. Cloning..."
        sudo -u odoo git clone --branch ${VERSION}.0 --depth 1 https://github.com/OCA/OpenUpgrade.git "$OPENUPGRADE_DIR"
        if [ $? -eq 0 ]; then
            print_success "OpenUpgrade cloned successfully"
        else
            print_error "Failed to clone OpenUpgrade"
            return 1
        fi
    else
        print_success "OpenUpgrade found: $OPENUPGRADE_DIR"
    fi
    
    # Check/Install openupgradelib
    print_info "Checking openupgradelib..."
    if sudo -u odoo bash -c "source ${VENV_DIR}/bin/activate && pip show openupgradelib > /dev/null 2>&1"; then
        print_success "openupgradelib is installed"
    else
        print_warning "Installing openupgradelib..."
        sudo -u odoo bash -c "source ${VENV_DIR}/bin/activate && pip install openupgradelib --quiet"
        if [ $? -eq 0 ]; then
            print_success "openupgradelib installed successfully"
        else
            print_error "Failed to install openupgradelib"
            return 1
        fi
    fi
    
    # Sync custom_migration_scripts (for version-specific fixes)
    if [ -d "$CUSTOM_SOURCE" ]; then
        if [ ! -d "$CUSTOM_SCRIPTS_DIR" ]; then
            print_warning "Syncing custom_migration_scripts..."
            sudo -u odoo cp -r "$CUSTOM_SOURCE" "$CUSTOM_SCRIPTS_DIR"
            print_success "custom_migration_scripts synced"
        else
            # Sync any updates
            print_info "Syncing custom_migration_scripts updates..."
            sudo -u odoo rsync -a "$CUSTOM_SOURCE/" "$CUSTOM_SCRIPTS_DIR/"
            print_success "custom_migration_scripts synced"
        fi
    fi
    
    echo ""
    return 0
}

# Run OpenUpgrade migration
run_migration() {
    print_step "3" "Running OpenUpgrade Migration"
    
    echo -e "    ${CYAN}Odoo Dir:${NC}    ${YELLOW}${ODOO_DIR}${NC}"
    echo -e "    ${CYAN}Config:${NC}      ${YELLOW}${MIGRATE_CFG}${NC}"
    echo -e "    ${CYAN}Database:${NC}    ${YELLOW}${TARGET_DB}${NC}"
    echo ""
    
    if [ ! -f "$MIGRATE_CFG" ]; then
        print_error "Migration config not found: $MIGRATE_CFG"
        exit 1
    fi
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found: $VENV_DIR"
        exit 1
    fi
    
    print_info "Starting migration (live log)..."
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    # Run migration with live output
    sudo -u odoo bash -c "cd ${ODOO_DIR} && source ${VENV_DIR}/bin/activate && python odoo-bin -c ${MIGRATE_CFG} -d ${TARGET_DB} --update=all --stop-after-init"
    
    local exit_code=$?
    
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    if [ $exit_code -eq 0 ]; then
        print_success "Migration completed successfully!"
        return 0
    else
        print_error "Migration failed with exit code: $exit_code"
        return $exit_code
    fi
}

# Create backup for next version
create_backup_for_next() {
    print_step "4" "Create Backup for v${NEXT_VERSION} Migration"
    
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="isalab${VERSION}_for_v${NEXT_VERSION}_${timestamp}"
    local backup_folder="${BACKUP_DIR}/${backup_name}"
    local backup_file="${backup_folder}/${backup_name}.backup"
    
    echo -e "    ${CYAN}Source DB:${NC}    ${YELLOW}${TARGET_DB}${NC}"
    echo -e "    ${CYAN}Backup:${NC}       ${YELLOW}${backup_name}${NC}"
    echo ""
    
    # Create backup directory with odoo user
    sudo -u "$PG_USER" mkdir -p "$backup_folder"
    
    # Create README with odoo user
    sudo -u "$PG_USER" tee "${backup_folder}/README.txt" > /dev/null << EOF
Backup Information
==================
Source Database: ${TARGET_DB}
Source Version:  Odoo ${VERSION}
Target Version:  Odoo ${NEXT_VERSION}
Created:         $(date '+%Y-%m-%d %H:%M:%S')
Server:          $(hostname)

This backup is ready for migration to Odoo ${NEXT_VERSION}
EOF
    
    print_info "Creating backup (this may take a while)..."
    
    # Create backup with odoo user (consistent ownership, no privileges stored)
    sudo -u "$PG_USER" PGPASSWORD="$PG_PASSWORD" pg_dump -h localhost -Fc --no-owner --no-privileges -f "$backup_file" "$TARGET_DB"
    
    local size=$(du -h "$backup_file" | cut -f1)
    
    print_success "Backup created: ${backup_name} (${size})"
    echo ""
    echo -e "    ${CYAN}Location:${NC} ${YELLOW}${backup_folder}${NC}"
    echo ""
    print_info "Ready for next migration: v${VERSION} → v${NEXT_VERSION}"
}

# Main menu
main() {
    print_header
    
    # Check prerequisites
    if [ ! -d "$ODOO_DIR" ]; then
        print_error "Odoo directory not found: $ODOO_DIR"
        print_info "Run setup_odoo_version.sh ${VERSION} first"
        exit 1
    fi
    
    print_step "1" "Database Preparation"
    
    # Check current database status
    local has_template=false
    local has_isalab=false
    
    if db_exists "$TEMPLATE_DB"; then
        has_template=true
    fi
    
    if db_exists "$TARGET_DB"; then
        has_isalab=true
    fi
    
    # Show status
    if $has_template; then
        echo -e "  ${GREEN}📋 Template database exists:${NC} ${YELLOW}${TEMPLATE_DB}${NC}"
    else
        echo -e "  ${YELLOW}📋 No template database found:${NC} ${TEMPLATE_DB}"
    fi
    
    if $has_isalab; then
        echo -e "  ${GREEN}📦 Previous migration database exists:${NC} ${YELLOW}${TARGET_DB}${NC}"
    fi
    echo ""
    
    # Build menu options dynamically
    echo -e "  ${CYAN}What would you like to do?${NC}"
    echo ""
    
    local opt=1
    local opt_from_template=""
    local opt_from_isalab=""
    local opt_from_backup=""
    local opt_exit=""
    
    if $has_template; then
        echo -e "    ${GREEN}[${opt}]${NC} Create ${YELLOW}${TARGET_DB}${NC} from existing template (fast)"
        opt_from_template=$opt
        ((opt++))
    fi
    
    if $has_isalab && ! $has_template; then
        echo -e "    ${GREEN}[${opt}]${NC} Save ${YELLOW}${TARGET_DB}${NC} as new template (for future retries)"
        opt_from_isalab=$opt
        ((opt++))
    fi
    
    echo -e "    ${GREEN}[${opt}]${NC} Restore backup file to template"
    opt_from_backup=$opt
    ((opt++))
    
    echo -e "    ${GREEN}[${opt}]${NC} Exit"
    opt_exit=$opt
    
    echo ""
    read -p "  Select option [1-${opt}]: " choice
    
    if [ "$choice" = "$opt_from_template" ] && [ -n "$opt_from_template" ]; then
        print_step "2" "Creating Database from Template"
        create_from_template
        
    elif [ "$choice" = "$opt_from_isalab" ] && [ -n "$opt_from_isalab" ]; then
        print_step "2" "Creating Template from Existing Database"
        create_template_from_isalab
        print_step "2b" "Creating Fresh Database from New Template"
        create_from_template
        
    elif [ "$choice" = "$opt_from_backup" ]; then
        if ! list_backups; then
            exit 1
        fi
        read -p "  Select backup number: " backup_num
        
        if [[ "$backup_num" =~ ^[0-9]+$ ]] && [ "$backup_num" -ge 1 ] && [ "$backup_num" -le ${#BACKUP_LIST[@]} ]; then
            selected_backup="${BACKUP_LIST[$((backup_num-1))]}"
            print_step "2" "Restoring Backup to Template"
            restore_to_template "$selected_backup"
            create_from_template
        else
            print_error "Invalid selection"
            exit 1
        fi
        
    elif [ "$choice" = "$opt_exit" ]; then
        echo ""
        print_info "Exiting..."
        exit 0
        
    else
        print_error "Invalid option"
        exit 1
    fi
    
    # Setup OpenUpgrade prerequisites
    if ! setup_openupgrade; then
        print_error "Failed to setup OpenUpgrade prerequisites"
        exit 1
    fi
    
    # Ask to run migration
    echo ""
    read -p "  Run OpenUpgrade migration now? [Y/n]: " run_choice
    
    if [[ ! "$run_choice" =~ ^[Nn]$ ]]; then
        if run_migration; then
            # Migration successful - ask about backup
            echo ""
            echo -e "  ${GREEN}🎉 Migration to v${VERSION} completed!${NC}"
            echo ""
            echo -e "  ${CYAN}Before creating backup for v${NEXT_VERSION}, please verify:${NC}"
            echo -e "    - Test the migrated database in Odoo"
            echo -e "    - Check for any errors or issues"
            echo ""
            read -p "  Migration verified OK? Create backup for v${NEXT_VERSION}? [y/N]: " backup_choice
            
            if [[ "$backup_choice" =~ ^[Yy]$ ]]; then
                create_backup_for_next
            else
                print_info "Skipping backup. You can run it later manually."
            fi
        fi
    else
        print_info "Skipping migration. You can run it manually:"
        echo ""
        echo -e "    ${YELLOW}sudo -u odoo bash -c \"cd ${ODOO_DIR} && source ${VENV_DIR}/bin/activate && python odoo-bin -c ${MIGRATE_CFG} -d ${TARGET_DB} --update=all --stop-after-init\"${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✨ Done!${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Run
main
