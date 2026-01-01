#!/bin/bash

# PostgreSQL Configuration Update Script
# Safely apply optimized configuration với backup và validation

set -e  # Exit on any error

# Colors cho output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if running as root hoặc with sudo
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        log "Running as root/sudo - OK"
    else
        error "This script requires sudo privileges to modify PostgreSQL configuration"
        echo "Please run: sudo $0"
        exit 1
    fi
}

# Detect PostgreSQL version và config location
detect_postgresql_config() {
    log "Detecting PostgreSQL configuration..."
    
    # Try common PostgreSQL versions và paths
    local versions=("16" "15" "14" "13" "12")
    local base_paths=("/etc/postgresql" "/usr/local/pgsql/data" "/var/lib/pgsql/data")
    
    for version in "${versions[@]}"; do
        for base_path in "${base_paths[@]}"; do
            if [[ "$base_path" == "/etc/postgresql" ]]; then
                PGSQL_CONFIG_PATH="$base_path/$version/main/postgresql.conf"
                PGSQL_CONFIG_DIR="$base_path/$version/main"
            else
                PGSQL_CONFIG_PATH="$base_path/postgresql.conf"
                PGSQL_CONFIG_DIR="$base_path"
            fi
            
            if [[ -f "$PGSQL_CONFIG_PATH" ]]; then
                PGSQL_VERSION="$version"
                log "Found PostgreSQL $version config at: $PGSQL_CONFIG_PATH"
                return 0
            fi
        done
    done
    
    error "Could not find PostgreSQL configuration file"
    echo "Please manually specify the path to postgresql.conf"
    exit 1
}

# Backup current configuration
backup_config() {
    local backup_file="${PGSQL_CONFIG_PATH}.backup.$(date +%Y%m%d_%H%M%S)"
    
    log "Creating backup of current configuration..."
    cp "$PGSQL_CONFIG_PATH" "$backup_file"
    
    if [[ -f "$backup_file" ]]; then
        success "Configuration backed up to: $backup_file"
        BACKUP_FILE="$backup_file"
    else
        error "Failed to create backup"
        exit 1
    fi
}

# Validate current PostgreSQL status
check_postgresql_status() {
    log "Checking PostgreSQL service status..."
    
    if systemctl is-active --quiet postgresql; then
        success "PostgreSQL is running"
        PGSQL_WAS_RUNNING=true
    else
        warning "PostgreSQL is not running"
        PGSQL_WAS_RUNNING=false
    fi
}

# Get current system resources for memory calculations
get_system_resources() {
    log "Analyzing system resources..."
    
    # Get total RAM in MB
    TOTAL_RAM_KB=$(grep MemTotal /proc/meminfo | awk '{print $2}')
    TOTAL_RAM_MB=$((TOTAL_RAM_KB / 1024))
    
    # Calculate optimal memory settings
    SHARED_BUFFERS_MB=$((TOTAL_RAM_MB / 4))      # 25% of RAM
    EFFECTIVE_CACHE_MB=$((TOTAL_RAM_MB * 3 / 4)) # 75% of RAM
    
    # Ensure minimum values
    [[ $SHARED_BUFFERS_MB -lt 128 ]] && SHARED_BUFFERS_MB=128
    [[ $EFFECTIVE_CACHE_MB -lt 256 ]] && EFFECTIVE_CACHE_MB=256
    
    log "System RAM: ${TOTAL_RAM_MB}MB"
    log "Calculated shared_buffers: ${SHARED_BUFFERS_MB}MB"
    log "Calculated effective_cache_size: ${EFFECTIVE_CACHE_MB}MB"
}

# Apply optimized configuration
apply_optimized_config() {
    log "Applying optimized PostgreSQL configuration..."
    
    # Create optimized config với dynamic values
    cat > "${PGSQL_CONFIG_DIR}/postgresql.conf.new" << EOF
# PostgreSQL Configuration - Optimized for RAG Bidding System
# Generated on $(date)
# System RAM: ${TOTAL_RAM_MB}MB

# =============================================================================
# CONNECTIONS AND AUTHENTICATION
# =============================================================================
max_connections = 200
superuser_reserved_connections = 3
tcp_keepalives_idle = 600
tcp_keepalives_interval = 30
tcp_keepalives_count = 3

# =============================================================================
# RESOURCE USAGE (MEMORY)
# =============================================================================
shared_buffers = ${SHARED_BUFFERS_MB}MB
huge_pages = try
work_mem = 8MB
maintenance_work_mem = 128MB
hash_mem_multiplier = 2.0
effective_cache_size = ${EFFECTIVE_CACHE_MB}MB
shared_preload_libraries = 'vector'
max_worker_processes = 8
max_parallel_workers = 4
max_parallel_workers_per_gather = 2
max_parallel_maintenance_workers = 2

# =============================================================================
# WRITE-AHEAD LOGGING (WAL)
# =============================================================================
wal_buffers = 16MB
wal_level = replica
max_wal_size = 2GB
min_wal_size = 512MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 15min

# =============================================================================
# QUERY TUNING
# =============================================================================
random_page_cost = 1.1
effective_io_concurrency = 200
seq_page_cost = 1.0
cpu_tuple_cost = 0.01
cpu_index_tuple_cost = 0.005
cpu_operator_cost = 0.0025
join_collapse_limit = 8
from_collapse_limit = 8
geqo_threshold = 12

# =============================================================================
# LOCKS AND TRANSACTIONS
# =============================================================================
max_locks_per_transaction = 1024
max_pred_locks_per_transaction = 64
max_pred_locks_per_relation = 64
max_pred_locks_per_page = 2
statement_timeout = 60s
lock_timeout = 30s
idle_in_transaction_session_timeout = 300s

# =============================================================================
# LOGGING
# =============================================================================
logging_collector = on
log_destination = 'stderr'
log_directory = 'log'
log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
log_rotation_age = 1d
log_rotation_size = 100MB
log_min_duration_statement = 1000
log_connections = off
log_disconnections = off
log_lock_waits = on
log_checkpoints = on
log_autovacuum_min_duration = 0
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_timezone = 'UTC'

# =============================================================================
# AUTOVACUUM
# =============================================================================
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 30s
autovacuum_vacuum_threshold = 50
autovacuum_vacuum_scale_factor = 0.1
autovacuum_analyze_threshold = 50
autovacuum_analyze_scale_factor = 0.05
autovacuum_vacuum_cost_delay = 10ms
autovacuum_vacuum_cost_limit = 200

# =============================================================================
# BACKGROUND WRITER
# =============================================================================
bgwriter_delay = 200ms
bgwriter_lru_maxpages = 100
bgwriter_lru_multiplier = 2.0
bgwriter_flush_after = 512kB

# =============================================================================
# STATISTICS
# =============================================================================
track_activities = on
track_counts = on
track_io_timing = on
track_functions = pl
stats_temp_directory = 'pg_stat_tmp'

# =============================================================================
# JIT AND PARALLELISM
# =============================================================================
jit = off
jit_above_cost = -1
jit_inline_above_cost = -1
jit_optimize_above_cost = -1
parallel_tuple_cost = 0.1
parallel_setup_cost = 1000.0

EOF

    # Replace current config với new one
    mv "${PGSQL_CONFIG_DIR}/postgresql.conf.new" "$PGSQL_CONFIG_PATH"
    
    # Set proper permissions
    chown postgres:postgres "$PGSQL_CONFIG_PATH"
    chmod 644 "$PGSQL_CONFIG_PATH"
    
    success "Configuration file updated successfully"
}

# Validate configuration syntax
validate_config() {
    log "Validating PostgreSQL configuration syntax..."
    
    # Test configuration bằng cách trying to start in check mode
    sudo -u postgres postgres --check-config --config-file="$PGSQL_CONFIG_PATH" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        success "Configuration syntax is valid"
    else
        error "Configuration syntax validation failed"
        log "Restoring backup configuration..."
        cp "$BACKUP_FILE" "$PGSQL_CONFIG_PATH"
        exit 1
    fi
}

# Restart PostgreSQL service
restart_postgresql() {
    log "Restarting PostgreSQL service..."
    
    systemctl restart postgresql
    
    # Wait for service to come up
    local max_wait=30
    local count=0
    
    while [[ $count -lt $max_wait ]]; do
        if systemctl is-active --quiet postgresql; then
            success "PostgreSQL restarted successfully"
            return 0
        fi
        
        sleep 1
        count=$((count + 1))
        echo -n "."
    done
    
    error "PostgreSQL failed to restart within ${max_wait} seconds"
    log "Restoring backup configuration..."
    cp "$BACKUP_FILE" "$PGSQL_CONFIG_PATH"
    systemctl restart postgresql
    exit 1
}

# Test database connectivity
test_connectivity() {
    log "Testing database connectivity..."
    
    # Try to connect to database
    sudo -u postgres psql -c "SELECT version();" > /dev/null 2>&1
    
    if [[ $? -eq 0 ]]; then
        success "Database connectivity test passed"
        
        # Show current settings
        log "Current configuration summary:"
        sudo -u postgres psql -c "
            SELECT name, setting, unit, context 
            FROM pg_settings 
            WHERE name IN ('max_connections', 'shared_buffers', 'effective_cache_size', 'work_mem', 'maintenance_work_mem')
            ORDER BY name;
        "
    else
        error "Database connectivity test failed"
        exit 1
    fi
}

# Show performance monitoring queries
show_monitoring_info() {
    log "Performance monitoring information:"
    
    cat << 'EOF'

📊 PERFORMANCE MONITORING QUERIES:

1. Check active connections:
   SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';

2. Check connection pool utilization:
   SELECT count(*) as total_connections, 
          sum(case when state = 'active' then 1 else 0 end) as active,
          sum(case when state = 'idle' then 1 else 0 end) as idle
   FROM pg_stat_activity;

3. Monitor slow queries (requires pg_stat_statements):
   SELECT query, mean_exec_time, calls FROM pg_stat_statements 
   WHERE mean_exec_time > 1000 ORDER BY mean_exec_time DESC LIMIT 10;

4. Check pgvector index usage:
   SELECT schemaname, tablename, indexname, idx_scan, idx_tup_read, idx_tup_fetch
   FROM pg_stat_user_indexes WHERE indexname LIKE '%vector%';

5. Monitor autovacuum activity:
   SELECT * FROM pg_stat_progress_vacuum;

📁 CONFIGURATION FILES:
   - Current config: $PGSQL_CONFIG_PATH
   - Backup: $BACKUP_FILE
   - Logs: $PGSQL_CONFIG_DIR/log/

🔧 NEXT STEPS:
   1. Run performance tests to validate improvements
   2. Monitor connection pool utilization
   3. Adjust settings based on actual usage patterns

EOF
}

# Main execution
main() {
    log "Starting PostgreSQL optimization for RAG Bidding System..."
    
    check_permissions
    detect_postgresql_config
    backup_config
    check_postgresql_status
    get_system_resources
    apply_optimized_config
    validate_config
    restart_postgresql
    test_connectivity
    show_monitoring_info
    
    success "PostgreSQL optimization completed successfully!"
    
    warning "IMPORTANT: Monitor system performance và adjust settings as needed"
    log "Run performance tests to validate improvements"
}

# Handle script interruption
trap 'error "Script interrupted. Configuration may be incomplete."; exit 1' INT TERM

# Run main function
main "$@"