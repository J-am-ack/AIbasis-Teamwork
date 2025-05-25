# 数据获取
import requests
import sqlite3
import os
from datetime import datetime
import json

# 直接在代码中设置API密钥（请替换为你的真实密钥）
os.environ['OPENAI_API_KEY'] = 'your-openai-key-here'  # ⚠️ 替换为你的真实OpenAI API key
os.environ['DASHBOARD_API_KEY'] = 'sk-f86f14554675473d86bf1e8f1228b29b'

os.environ['MODEL_TYPE'] = 'qwen'


os.environ['OPENWEATHER_API_KEY'] = '7e006d9b6049e2cb983a408bd1db3374'  # ⚠️ 替换为你的真实天气API key

# print("🔑 当前设置的API密钥:")
# print(f"天气API: {os.environ.get('OPENWEATHER_API_KEY', '未设置')}")
# print(f"OpenAI API: {os.environ.get('OPENAI_API_KEY', '未设置')[:10]}...")
print(f"模型类型: {os.environ.get('MODEL_TYPE', '未设置')}")

# 加载环境变量
# try:
#     from dotenv import load_dotenv
#     load_dotenv()  # 自动加载.env文件
#     print("✅ .env文件加载成功")
# except ImportError:
#     print("⚠️  未安装python-dotenv，使用代码中设置的API密钥")
#     print("💡 建议安装: pip install python-dotenv")

# 修复1: get_weather函数缺少api_key参数
def get_weather(location: str, api_key: str = None) -> dict:
    """获取天气信息，添加了错误处理和默认值"""
    if not api_key:
        # 如果没有API key，返回模拟数据用于测试
        print("Warning: No API key provided, using mock data")
        return {
            "temp": 22,
            "humidity": 65,
            "conditions": "晴朗"
        }
    
    url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        return {
            "temp": data["main"]["temp"],
            "humidity": data["main"]["humidity"],
            "conditions": data["weather"][0]["description"]
        }
    except (requests.exceptions.RequestException, KeyError) as e:
        print(f"Weather API error: {e}")
        # 返回默认值而不是None
        return {
            "temp": 20,
            "humidity": 50,
            "conditions": "未知天气"
        }

# 修复2: 数据库连接和表创建
def init_database():
    """初始化数据库"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    
    # 创建用户表
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id TEXT PRIMARY KEY, age INT, gender TEXT, style_pref TEXT)''')
    
    # 修复3: 修正history表的SQL语法错误
    c.execute('''CREATE TABLE IF NOT EXISTS history
                 (user_id TEXT, 
                  date TEXT, 
                  recommendation TEXT, 
                  options TEXT,
                  selected_index INT)''')
    
    # 修复4: 添加缺失的feedback表
    c.execute('''CREATE TABLE IF NOT EXISTS feedback
                 (user_id TEXT, 
                  recommendation TEXT, 
                  rating REAL)''')
    
    conn.commit()
    return conn, c

# 修复5: build_features函数添加错误处理
def build_features(user_id, cursor):
    """构建用户特征，添加了错误处理"""
    try:
        # 获取用户特征
        user_data = cursor.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not user_data:
            print(f"User {user_id} not found, using default values")
            return {
                "age": 25,
                "gender": "男",
                "preferred_styles": ["休闲"],
                "recent_recommendations": []
            }
        
        # 获取最近3次推荐
        history = cursor.execute("SELECT recommendation FROM history WHERE user_id=? ORDER BY date DESC LIMIT 3", (user_id,)).fetchall()
        
        return {
            "age": user_data[1],
            "gender": user_data[2],
            "preferred_styles": user_data[3].split(',') if user_data[3] else ["休闲"],
            "recent_recommendations": [h[0] for h in history] if history else []
        }
    except Exception as e:
        print(f"Error building features: {e}")
        return {
            "age": 25,
            "gender": "男",
            "preferred_styles": ["休闲"],
            "recent_recommendations": []
        }

# 修复6: 简化prompt构建函数
def construct_prompt(weather, features):
    """构建提示词"""
    prompt_template = f"""
作为专业穿搭助手，请提供3套不同的着装方案：

【环境信息】
- 气温：{weather['temp']}℃
- 天气状况：{weather['conditions']}
- 湿度：{weather['humidity']}%
- 用户特征：{features['gender']}性，{features['age']}岁
- 风格偏好：{', '.join(features['preferred_styles'])}

【历史记录】（最近3次推荐）：
{chr(10).join(features['recent_recommendations']) if features['recent_recommendations'] else '无历史记录'}

【输出要求】：
1. 生成3套差异明显的搭配方案
2. 每套方案包含：👕上衣、👖下装、🧥外套、👟鞋履、💡理由
3. 使用emoji增加亲和力
4. 避免与历史推荐重复

【输出格式】：
方案1：
👕 上衣：...
👖 下装：...
🧥 外套：...
👟 鞋履：...
💡 理由：...

方案2：
👕 上衣：...
👖 下装：...
🧥 外套：...
👟 鞋履：...
💡 理由：...

方案3：
👕 上衣：...
👖 下装：...
🧥 外套：...
👟 鞋履：...
💡 理由：...
"""
    return prompt_template

# 方法1: 使用OpenAI API
def generate_recommendation_openai(prompt, api_key=None):
    """使用OpenAI API生成推荐"""
    import openai
    
    if not api_key:
        api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("Warning: No OpenAI API key found, using mock data")
        return generate_mock_recommendation()
    
    try:
        client = openai.OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # 或使用 "gpt-4" 获得更好效果
            messages=[
                {"role": "system", "content": "你是一位专业的时尚穿搭顾问。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return generate_mock_recommendation(prompt)  # 修复：传递prompt参数

# 方法2: 使用通义千问API
def generate_recommendation_qwen(prompt, api_key=None):
    """使用通义千问API生成推荐"""
    if not api_key:
        api_key = os.getenv('DASHBOARD_API_KEY')
    
    if not api_key:
        print("Warning: No DashScope API key found, using mock data")
        return generate_mock_recommendation()
    
    try:
        import dashscope
        dashscope.api_key = api_key
        
        response = dashscope.Generation.call(
            model='qwen-turbo',  # 或使用 'qwen-plus', 'qwen-max'
            prompt=prompt,
            max_tokens=1000,
            temperature=0.7
        )
        
        if response.status_code == 200:
            return response.output.text
        else:
            print(f"Qwen API error: {response.message}")
            return generate_mock_recommendation(prompt)  # 修复：传递prompt参数
    except Exception as e:
        print(f"Qwen API error: {e}")
        return generate_mock_recommendation(prompt)  # 修复：传递prompt参数

# 方法3: 使用智谱AI (GLM)
def generate_recommendation_glm(prompt, api_key=None):
    """使用智谱AI GLM生成推荐"""
    if not api_key:
        api_key = os.getenv('ZHIPUAI_API_KEY')
    
    if not api_key:
        print("Warning: No ZhipuAI API key found, using mock data")
        return generate_mock_recommendation()
    
    try:
        from zhipuai import ZhipuAI
        client = ZhipuAI(api_key=api_key)
        
        response = client.chat.completions.create(
            model="glm-4",  # 或使用 "glm-3-turbo"
            messages=[
                {"role": "system", "content": "你是一位专业的时尚穿搭顾问。"},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"GLM API error: {e}")
        return generate_mock_recommendation(prompt)  # 修复：传递prompt参数

# 方法4: 使用百度文心一言
def generate_recommendation_ernie(prompt, api_key=None):
    """使用百度文心一言生成推荐"""
    if not api_key:
        api_key = os.getenv('BAIDU_API_KEY')
    
    secret_key = os.getenv('BAIDU_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("Warning: No Baidu API credentials found, using mock data")
        return generate_mock_recommendation()
    
    try:
        # 获取access_token
        token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
        token_response = requests.get(token_url)
        access_token = token_response.json().get('access_token')
        
        # 调用文心一言API
        url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions_pro?access_token={access_token}"
        
        payload = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_output_tokens": 1000,
            "temperature": 0.7
        }
        
        response = requests.post(url, json=payload)
        result = response.json()
        
        if 'result' in result:
            return result['result']
        else:
            print(f"Ernie API error: {result}")
            return generate_mock_recommendation(prompt)  # 修复：传递prompt参数
            
    except Exception as e:
        print(f"Ernie API error: {e}")
        return generate_mock_recommendation(prompt)  # 修复：传递prompt参数

# 备用方案：模拟数据
def generate_mock_recommendation(prompt=None):
    """生成模拟推荐数据"""
    print("⚠️  使用模拟数据生成推荐")
    return """
方案1：
👕 上衣：白色基础T恤
👖 下装：深蓝色牛仔裤
🧥 外套：薄款运动夹克
👟 鞋履：白色运动鞋
💡 理由：适合当前温度，舒适休闲

方案2：
👕 上衣：条纹长袖衫
👖 下装：卡其色休闲裤
🧥 外套：轻薄风衣
👟 鞋履：棕色休闲鞋
💡 理由：商务休闲风格，适合多种场合

方案3：
👕 上衣：黑色POLO衫
👖 下装：灰色运动裤
🧥 外套：连帽卫衣
👟 鞋履：黑色运动鞋
💡 理由：运动风格，方便活动
"""

# 统一的生成函数
def generate_recommendation(prompt, model_type="openai", api_key=None):
    """
    统一的推荐生成函数
    model_type: "openai", "qwen", "glm", "ernie", "mock"
    """
    if model_type == "openai":
        return generate_recommendation_openai(prompt, api_key)
    elif model_type == "qwen":
        return generate_recommendation_qwen(prompt, api_key)
    elif model_type == "glm":
        return generate_recommendation_glm(prompt, api_key)
    elif model_type == "ernie":
        return generate_recommendation_ernie(prompt, api_key)
    else:
        return generate_mock_recommendation()

def parse_recommendations(text):
    """解析模型输出的多方案文本"""
    options = []
    current_option = {}
    
    lines = text.strip().split('\n')
    for line in lines:
        line = line.strip()
        if '方案' in line and ('：' in line or ':' in line):
            if current_option:
                options.append(current_option)
            current_option = {}
        elif '👕' in line and ('：' in line or ':' in line):
            current_option['top'] = line.split('：')[-1].split(':')[-1].strip()
        elif '👖' in line and ('：' in line or ':' in line):
            current_option['bottom'] = line.split('：')[-1].split(':')[-1].strip()
        elif '🧥' in line and ('：' in line or ':' in line):
            current_option['coat'] = line.split('：')[-1].split(':')[-1].strip()
        elif '👟' in line and ('：' in line or ':' in line):
            current_option['shoes'] = line.split('：')[-1].split(':')[-1].strip()
        elif '💡' in line and ('：' in line or ':' in line):
            current_option['reason'] = line.split('：')[-1].split(':')[-1].strip()
    
    # 添加最后一个方案
    if current_option:
        options.append(current_option)
    
    return options[:3]  # 最多返回3个方案

def save_feedback(user_id, recommendation, rating, cursor, conn):
    """存储用户评分"""
    try:
        cursor.execute("INSERT INTO feedback VALUES (?, ?, ?)", 
                     (user_id, recommendation, rating))
        conn.commit()
        print(f"Feedback saved for user {user_id}")
    except Exception as e:
        print(f"Error saving feedback: {e}")

def save_selection(user_id, recommendation, options, selected_index, cursor, conn):
    """保存用户选择"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        options_json = json.dumps(options, ensure_ascii=False)
        cursor.execute("INSERT INTO history VALUES (?, ?, ?, ?, ?)", 
                     (user_id, current_time, recommendation, options_json, selected_index))
        conn.commit()
        print(f"Selection saved for user {user_id}")
    except Exception as e:
        print(f"Error saving selection: {e}")

def full_workflow(user_id):
    """完整工作流程"""
    # 初始化数据库
    conn, cursor = init_database()
    
    try:
        # 获取API密钥
        weather_api_key = os.getenv('OPENWEATHER_API_KEY')
        # model_api_key = os.getenv('OPENAI_API_KEY')  # 或其他模型的key
        model_api_key = os.getenv('DASHBOARD_API_KEY')
        
        # 获取天气数据
        weather = get_weather("Beijing", weather_api_key)
        print(f"Weather: {weather}")
        
        # 构建用户特征
        features = build_features(user_id, cursor)
        print(f"User features: {features}")
        
        # 生成推荐
        main_prompt = construct_prompt(weather, features)
        model_type = os.getenv('MODEL_TYPE', 'dashscore')  # 从环境变量获取模型类型
        recommendations = generate_recommendation(main_prompt, model_type, model_api_key)
        print(f"Recommendations:\n{recommendations}")
        
        # 解析推荐方案
        parsed_options = parse_recommendations(recommendations)
        print(f"Parsed options: {parsed_options}")
        
        # 模拟用户选择（实际应用中由用户交互决定）
        selected_index = 0  # 假设用户选择第一个方案
        
        # 保存用户选择
        save_selection(user_id, recommendations, parsed_options, selected_index, cursor, conn)
        
        # 模拟用户评分
        rating = 4.0
        save_feedback(user_id, recommendations, rating, cursor, conn)
        
        return parsed_options
        
    except Exception as e:
        print(f"Error in workflow: {e}")
        return []
    finally:
        conn.close()

if __name__ == "__main__":
    # 初始化数据库
    conn, cursor = init_database()
    
    # 初始化测试用户
    try:
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", 
                     ("test_user", 18, "男", "休闲,运动"))
        conn.commit()
        print("Test user created")
    except Exception as e:
        print(f"Error creating test user: {e}")
    finally:
        conn.close()
    
    # 运行完整流程
    print("Running full workflow...")
    results = full_workflow("test_user")  # 不再需要传递api_key参数
    
    if results:
        print("\nFinal results:")
        for i, option in enumerate(results, 1):
            print(f"方案{i}: {option}")
