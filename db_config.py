"""
数据库配置模块
统一管理 PostgreSQL 数据库连接配置
"""
import os
from typing import Dict, Any

# 默认数据库配置
DEFAULT_DB_CONFIG = {
    'host': '/var/run/postgresql',
    'port': 12335,
    'database': 'tushare',
    'user': 'postgres',
}


def get_db_config() -> Dict[str, Any]:
    """
    获取数据库配置
    优先从环境变量读取，否则使用默认值
    """
    config = DEFAULT_DB_CONFIG.copy()
    
    # 从环境变量覆盖
    if os.environ.get('PGHOST'):
        config['host'] = os.environ.get('PGHOST')
    if os.environ.get('PGPORT'):
        config['port'] = int(os.environ.get('PGPORT'))
    if os.environ.get('PGDATABASE'):
        config['database'] = os.environ.get('PGDATABASE')
    if os.environ.get('PGUSER'):
        config['user'] = os.environ.get('PGUSER')
    if os.environ.get('PGPASSWORD'):
        config['password'] = os.environ.get('PGPASSWORD')
    
    return config


def get_connection_string() -> str:
    """获取 SQLAlchemy 格式的连接字符串"""
    config = get_db_config()
    
    if config.get('password'):
        return f"postgresql://{config['user']}:{config['password']}@{config['host']}:{config['port']}/{config['database']}"
    else:
        return f"postgresql://{config['user']}@{config['host']}:{config['port']}/{config['database']}"


if __name__ == '__main__':
    # 测试配置
    config = get_db_config()
    print("数据库配置:")
    for key, value in config.items():
        if key == 'password':
            print(f"  {key}: {'*' * len(str(value))}")
        else:
            print(f"  {key}: {value}")
