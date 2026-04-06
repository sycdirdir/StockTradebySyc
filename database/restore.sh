#!/bin/bash
#
# PostgreSQL 数据库恢复脚本
# 用于从备份文件恢复 tushare 数据库
#
# 使用方法:
#   ./restore.sh backup_file.sql.gz    # 从压缩备份恢复
#   ./restore.sh backup_file.sql       # 从普通备份恢复
#

set -e

# 配置
DB_NAME="tushare"
DB_USER="postgres"
DB_HOST="/var/run/postgresql"
DB_PORT="12335"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

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

# 检查参数
check_args() {
    if [ $# -eq 0 ]; then
        log_error "请指定备份文件"
        echo "用法: $0 <backup_file.sql.gz|backup_file.sql>"
        exit 1
    fi
    
    BACKUP_FILE="$1"
    
    if [ ! -f "${BACKUP_FILE}" ]; then
        log_error "备份文件不存在: ${BACKUP_FILE}"
        exit 1
    fi
    
    log_info "备份文件: ${BACKUP_FILE}"
}

# 检查 PostgreSQL
check_postgres() {
    if ! pg_isready -h "${DB_HOST}" -p "${DB_PORT}" > /dev/null 2>&1; then
        log_error "PostgreSQL 未运行或无法连接"
        exit 1
    fi
    log_info "PostgreSQL 连接正常"
}

# 解压备份文件（如果是压缩的）
prepare_backup() {
    if [[ "${BACKUP_FILE}" == *.gz ]]; then
        log_info "解压备份文件..."
        gunzip -c "${BACKUP_FILE}" > /tmp/restore_temp.sql
        RESTORE_FILE="/tmp/restore_temp.sql"
    else
        RESTORE_FILE="${BACKUP_FILE}"
    fi
}

# 恢复数据库
restore_database() {
    log_info "========================================"
    log_info "开始恢复数据库 ${DB_NAME}..."
    log_info "========================================"
    
    # 检查数据库是否存在
    if psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -lqt | cut -d \| -f 1 | grep -qw "${DB_NAME}"; then
        log_warn "数据库 ${DB_NAME} 已存在"
        read -p "是否删除并重新创建? (y/N): " confirm
        if [[ $confirm == [yY] ]]; then
            log_info "删除现有数据库..."
            dropdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"
        else
            log_info "取消恢复"
            exit 0
        fi
    fi
    
    # 创建数据库
    log_info "创建数据库 ${DB_NAME}..."
    createdb -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" "${DB_NAME}"
    
    # 恢复数据
    log_info "恢复数据..."
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" -f "${RESTORE_FILE}"
    
    if [ $? -eq 0 ]; then
        log_info "恢复完成!"
    else
        log_error "恢复失败"
        exit 1
    fi
    
    # 清理临时文件
    if [[ "${BACKUP_FILE}" == *.gz ]]; then
        rm -f /tmp/restore_temp.sql
    fi
}

# 验证恢复
verify_restore() {
    log_info "验证恢复结果..."
    
    # 获取表统计
    psql -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}" -d "${DB_NAME}" << EOF
\dt
SELECT 
    'daily' as table_name, 
    COUNT(*) as record_count,
    MAX(trade_date) as latest_date
FROM daily
UNION ALL
SELECT 
    'stock_weekly' as table_name,
    COUNT(*) as record_count,
    MAX(trade_date) as latest_date
FROM stock_weekly
UNION ALL
SELECT 
    'stock_monthly' as table_name,
    COUNT(*) as record_count,
    MAX(trade_date) as latest_date
FROM stock_monthly;
EOF
}

# 主函数
main() {
    log_info "========================================"
    log_info "PostgreSQL 数据库恢复脚本"
    log_info "========================================"
    
    check_args "$@"
    check_postgres
    prepare_backup
    restore_database
    verify_restore
    
    log_info "========================================"
    log_info "恢复任务完成!"
    log_info "========================================"
}

# 运行主函数
main "$@"
