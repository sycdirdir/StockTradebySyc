"""数据库配置模块"""
import os
from dotenv import load_dotenv

load_dotenv()


def get_db_config() -> dict:
    """获取 PostgreSQL 数据库连接配置"""
    host = os.getenv('DB_HOST', '/var/run/postgresql')
    port = os.getenv('DB_PORT', '12335')
    dbname = os.getenv('DB_NAME', 'tushare')
    user = os.getenv('DB_USER', 'postgres')
    password = os.getenv('DB_PASSWORD', '')

    config = {
        'host': host,
        'port': int(port),
        'dbname': dbname,
        'user': user,
    }
    if password:
        config['password'] = password

    return config
