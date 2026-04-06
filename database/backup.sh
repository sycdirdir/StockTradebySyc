#!/bin/bash
#
# PostgreSQL 数据库备份脚本
# 用于备份 tushare 数据库
#
# 使用方法:
#   ./backup.sh              # 备份到默认目录
#   ./backup.sh /path/to/dir # 备份到指定目录
#

set -e

# 配置
DB_NAME="tushare"
DB_USER="postgres"
DB_HOST="/var/run/postgresql"
DB_PORT="12335"
BACKUP_DIR="${1:-./backups}"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/tushare_backup_${DATE}.sql"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查 PostgreSQL 是否运行
check_postgres() {
    if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" > /dev/null 2>&1; then
        log_error "PostgreSQL 未运行或无法连接"
        exit 1
    fi
    log_info "PostgreSQL 连接正常"
}

# 创建备份目录
mkdir -p "${BACKUP_DIR}"

# 检查数据库是否存在
check_database() {
    if ! psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
        log_error "数据库 ${DB_NAME} 不存在"
        exit 1
    fi
    log_info "数据库 ${DB_NAME} 存在"
    
    # 显示主要表统计
    log_info "数据库表统计:"
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -c "
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as size
FROM pg_tables 
WHERE schemaname='public' 
AND tablename IN ('daily', 'stock_weekly', 'stock_monthly', 'stock_basic', 'TargetList', 'index_daily')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
" 2>/dev/null || true
}

# 执行备份
backup_database() {
    log_info "开始备份数据库 ${DB_NAME}..."
    log_info "备份文件: ${BACKUP_FILE}"
    
    # 使用 pg_dump 备份
    PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        -h "${DB_HOST}" \
        -p "${DB_PORT}" \
        -U "${DB_USER}" \
        -d "${DB_NAME}" \
        -F p \
        -v \
        --no-owner \
        --no-acl \
        -f "${BACKUP_FILE}"
    
    if [ $? -eq 0 ]; then
        log_info "备份完成: ${BACKUP_FILE}"
        
        # 压缩备份文件
        gzip "${BACKUP_FILE}"
        log_info "压缩完成: ${BACKUP_FILE}.gz"
        
        # 显示文件大小
        ls -lh "${BACKUP_FILE}.gz"
    else
        log_error "备份失败"
        exit 1
    fi
}

# 清理旧备份（保留最近 7 天）
cleanup_old_backups() {
    log_info "清理旧备份文件（保留最近 7 天）..."
    find "${BACKUP_DIR}" -name "tushare_backup_*.sql.gz" -mtime +7 -delete
    log_info "清理完成"
}

# 主函数
main() {
    log_info "========================================"
    log_info "PostgreSQL 数据库备份脚本"
    log_info "========================================"
    log_info "数据库: ${DB_NAME}"
    log_info "备份目录: ${BACKUP_DIR}"
    log_info "========================================"
    
    check_postgres
    check_database
    backup_database
    cleanup_old_backups
    
    log_info "========================================"
    log_info "备份任务完成!"
    log_info "========================================"
}

# 运行主函数
main
