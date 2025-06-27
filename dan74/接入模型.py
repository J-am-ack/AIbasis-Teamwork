import httpx
import json
from openai import OpenAI
client = OpenAI(
    api_key="sk-c9cc12071c1642e0829f91335ba50c56", 
    base_url="https://api.deepseek.com", 
    http_client=httpx.Client(verify=False)
)

def build_male_health_prompt():
    return """你是一位专业的男性健康顾问，具有丰富的医学知识和经验。你的职责是：
    1. 为用户提供专业、准确的健康建议
    2. 回答用户关于男性健康的各类问题
    3. 提供科学的生活方式和饮食建议
    4. 必要时建议用户及时就医
    
    请注意：
    - 保持专业、友善的态度
    - 给出清晰、易懂的解释
    - 不做具体的诊断，而是提供建议和指导
    - 遇到严重问题时，建议用户及时就医
    """
messages = [
    {"role": "system", "content": build_male_health_prompt()}
]

print("男性健康顾问 - AI诊断系统已启动")
print("输入'退出'或'exit'结束对话")
print("-" * 50)
while True:

    user_input = input("您的问题: ")
    if user_input.lower() in ['退出', 'exit', 'quit']:
        print("对话结束")
        break
    messages.append({"role": "user", "content": user_input})
    print("正在分析您的问题...")
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        assistant_reply = response.choices[0].message.content
        print(f"\n医生回复: {assistant_reply}\n")
        messages.append({"role": "assistant", "content": assistant_reply})
    except Exception as e:
        print(f"发生错误: {str(e)}")