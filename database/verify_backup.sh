#!/bin/bash
#
# 备份验证脚本
# 检查备份文件是否包含所有必需的表
#

set -e

BACKUP_FILE="$1"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup_file.sql.gz>"
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "Error: Backup file not found: $BACKUP_FILE"
    exit 1
fi

REQUIRED_TABLES=(
    "stock_basic"
    "daily"
    "stock_weekly"
    "stock_monthly"
    "TargetList"
    "index_basic"
    "index_daily"
)

echo "========================================"
echo "备份验证"
echo "========================================"
echo "备份文件: $BACKUP_FILE"
echo "文件大小: $(ls -lh $BACKUP_FILE | awk '{print $5}')"
echo "========================================"

# 解压并检查
if [[ "$BACKUP_FILE" == *.gz ]]; then
    echo "解压备份文件..."
    gunzip -c "$BACKUP_FILE" > /tmp/verify_backup.sql
    CHECK_FILE="/tmp/verify_backup.sql"
else
    CHECK_FILE="$BACKUP_FILE"
fi

echo ""
echo "检查必需表:"
MISSING=0
for table in "${REQUIRED_TABLES[@]}"; do
    # 使用不区分大小写的匹配
    if grep -iq "CREATE TABLE.*$table" "$CHECK_FILE" 2>/dev/null; then
        echo "  ✓ $table"
    else
        echo "  ✗ $table (MISSING)"
        MISSING=1
    fi
done

# 检查 TargetList 数据
if grep -q "TargetList" "$CHECK_FILE"; then
    echo ""
    echo "TargetList 表详情:"
    grep -c "INSERT INTO.*TargetList" "$CHECK_FILE" 2>/dev/null | xargs -I {} echo "  数据行数: {}"
fi

# 清理临时文件
if [[ "$BACKUP_FILE" == *.gz ]]; then
    rm -f /tmp/verify_backup.sql
fi

echo "========================================"
if [ $MISSING -eq 0 ]; then
    echo "✓ 备份验证通过!"
    exit 0
else
    echo "✗ 备份验证失败: 缺少必需表"
    exit 1
fi
