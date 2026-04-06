import requests
import json

def send_wechat_message(webhook_key, content, msgtype="text", mentioned_list=None):
    """
    发送企业微信机器人消息
    
    参数:
    webhook_key -- webhook的key
    content -- 消息内容
    msgtype -- 消息类型，可选"text"或"markdown"
    mentioned_list -- 需要@的用户列表，例如["@all"]或["张三", "13800001111"]
    """
    webhook_url = f"https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={webhook_key}"
    
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
    webhook_key = "173cf9b8-010b-4b85-b127-2c4cb881bb36"
    
    # 发送文本消息
    result = send_wechat_message(
        webhook_key,
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
        webhook_key,
        markdown_content,
        msgtype="markdown"
    )
    print(result)