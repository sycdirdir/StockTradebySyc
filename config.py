"""
配置管理模块
支持从环境变量或 .env 文件加载配置
"""
import os
from pathlib import Path


def load_env_file(env_path=None):
    """
    加载 .env 文件中的环境变量

    参数:
        env_path: .env 文件路径，默认为项目根目录下的 .env
    """
    if env_path is None:
        env_path = Path(__file__).parent / ".env"

    if not env_path.exists():
        return

    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            # 解析 KEY=VALUE
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                # 只设置未存在的环境变量
                if key and key not in os.environ:
                    os.environ[key] = value


def get_config(key, default=None, required=False):
    """
    获取配置项

    参数:
        key: 配置键名
        default: 默认值
        required: 是否必需，为 True 时如果未设置会抛出异常

    返回:
        配置值
    """
    value = os.environ.get(key, default)
    if required and not value:
        raise ValueError(
            f"配置项 {key} 未设置。请通过以下方式之一设置：\n"
            f"1. 设置环境变量: export {key}=your_value\n"
            f"2. 创建 .env 文件并添加 {key}=your_value\n"
            f"3. 复制 .env.example 为 .env 并修改"
        )
    return value


# 加载 .env 文件
load_env_file()

# ============================================
# 配置项定义
# ============================================

# Tushare API Token
TUSHARE_TOKEN = get_config("TUSHARE_TOKEN", required=True)

# 企业微信机器人 Webhook Key
QYWX_WEBHOOK_KEY = get_config("QYWX_WEBHOOK_KEY", default="")

# 代理设置
HTTP_PROXY = get_config("HTTP_PROXY", default="")
HTTPS_PROXY = get_config("HTTPS_PROXY", default="")


if __name__ == "__main__":
    # 测试配置加载
    print(f"TUSHARE_TOKEN: {'已设置' if TUSHARE_TOKEN else '未设置'}")
    print(f"QYWX_WEBHOOK_KEY: {'已设置' if QYWX_WEBHOOK_KEY else '未设置'}")
