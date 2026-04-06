import requests
import json
from config import QYWX_WEBHOOK_KEY


def send_wechat_message(content, msgtype="text", mentioned_list=None, webhook_key=None):
    """
    发送企业微信机器人消息

    参数:
        content -- 消息内容
        msgtype -- 消息类型，可选"text"或"markdown"
        mentioned_list -- 需要@的用户列表，例如["@all"]或["张三", "13800001111"]
        webhook_key -- webhook的key，如果不提供则从配置文件读取
    """
    # 优先使用传入的 key，否则从配置文件读取
    key = webhook_key or QYWX_WEBHOOK_KEY

    if not key:
        raise ValueError(
            "企业微信 Webhook Key 未设置。请通过以下方式之一设置：\n"
            "1. 设置环境变量: export QYWX_WEBHOOK_KEY=your_key\n"
            "2. 创建 .env 文件并添加 QYWX_WEBHOOK_KEY=your_key\n"
            "3. 调用时传入 webhook_key 参数"
        )

    webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={key}"

    if mentioned_list is None:
        mentioned_list = []

    if msgtype == "text":
        message = {
            "msgtype": "text",
            "text": {
                "content": content,
                "mentioned_list": mentioned_list
            }
        }
    elif msgtype == "markdown":
        message = {
            "msgtype": "markdown",
            "markdown": {
                "content": content
            }
        }
    else:
        raise ValueError("不支持的消息类型，仅支持'text'或'markdown'")

    headers = {"Content-Type": "application/json"}
    response = requests.post(webhook_url, data=json.dumps(message), headers=headers)
    return response.json()


# 使用示例
if __name__ == "__main__":
    # 确保已设置 QYWX_WEBHOOK_KEY 环境变量或在 .env 文件中配置

    # 发送文本消息
    result = send_wechat_message(
        "002036联创电子 2026-02-23 17:21:05 价格跌破5日均线，请注意风险！",
        mentioned_list=["@all"]
    )
    print(result)

    # 发送Markdown消息
    markdown_content = """### 系统告警
> **周期**：<font color=\"warning\">日线</font>
> **600031**：`app-server-01`
> **时间**：2026-01-08 15:11:05
>
> 均线开始多头排列，请及时关注！"""

    result = send_wechat_message(
        markdown_content,
        msgtype="markdown"
    )
    print(result)
