
# 数据获取
import requests
# from tenacity import retry, stop_after_attempt
# @retry(stop=stop_after_attempt(3))
# def safe_api_call():
# def get_weather(location: str, api_key: str) -> dict:
    

#     url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
#     response = requests.get(url)
#     return {
#         "temp": response.json()["main"]["temp"],
#         "humidity": response.json()["main"]["humidity"],
#         "conditions": response.json()["weather"][0]["description"]
#     }


def get_weather(location: str, api_key: str) -> dict:
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
        return None  # 添加降级处理逻辑


# 存储用户历史数据
import sqlite3

conn = sqlite3.connect('users.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id TEXT PRIMARY KEY, age INT, gender TEXT, style_pref TEXT)''')


# c.execute('''CREATE TABLE IF NOT EXISTS history
#              (user_id TEXT, date TEXT, recommendation TEXToptions TEXT, 
#             selected_index INT)''')  # 记录用户选择的方案序号

# 修正后
c.execute('''CREATE TABLE IF NOT EXISTS history
             (user_id TEXT, date TEXT, 
             recommendation TEXT, 
             options TEXT,
             selected_index INT)''')



def build_features(user_id):
    # 获取用户特征
    user_data = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    # 获取最近3次推荐
    history = c.execute("SELECT recommendation FROM history WHERE user_id=? ORDER BY date DESC LIMIT 3", (user_id,)).fetchall()
    
    return {
        "age": user_data[1],
        "gender": user_data[2],
        "preferred_styles": user_data[3].split(','),
        "recent_recommendations": [h[0] for h in history]
    }


# 从prompt的修改来让大模型的输出有调整    
def construct_prompt(weather, features):
    prompt_template = f"""
    你是一位专业的穿衣顾问，请根据以下信息提供建议：
    - 当前天气：{weather['temp']}℃, {weather['conditions']}, 湿度{weather['humidity']}%
    - 用户特征：{features['gender']}性，{features['age']}岁
    - 风格偏好：{', '.join(features['preferred_styles'])}
    - 近期推荐记录：{features['recent_recommendations']}

    要求：
    1. 避免重复近1-2天推荐
    2. 考虑温度变化建议外套选择
    3. 给出搭配理由
    4. 使用emoji增加亲和力
    5. 提供2-3套方案供用户选择，并记录他们的选择
    
    
    
    作为专业穿搭助手，请提供3套不同的着装方案：
    
    【环境信息】
    - 气温：{weather['temp']}℃
    - 天气状况：{weather['conditions']}
    - 湿度：{weather['humidity']}%
    - 用户特征：{features['gender']}性，{features['age']}岁
    - 风格偏好：{', '.join(features['preferred_styles'])}
    
    【历史记录】（最近3次推荐）：
    {chr(10).join(features['recent_recommendations'])}
    
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
    
    (可选)
    方案3：
    建议格式：
    👕 上衣：...
    👖 下装：...
    🧥 外套：...
    👟 鞋履：...
    💡 理由：...
    
    【输出结束语：
    请为我的回答打分！1-5qwq（喜欢就5分好评球球qaq
    如果都不满意的话，可以提供更多信息，我将为你生成其他方案！
    

    """
    return prompt_template


from transformers import AutoModelForCausalLM, AutoTokenizer
import torch
# 加载量化版模型提升推理速度
model = AutoModelForCausalLM.from_pretrained("Qwen/Qwen-1_8B-Chat-Int4", 
                                           device_map="auto", 
                                           trust_remote_code=True,
                                           torch_dtype=torch.float16,
                                        low_cpu_mem_usage=True)
tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen-1_8B-Chat", 
                                        trust_remote_code=True)

def generate_recommendation(prompt):
    messages = [{"role": "user", "content": prompt}]
    response = model.chat(tokenizer, messages)
    return response


def diversified_generation(prompt):
    response = model.chat(
            tokenizer,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.2,  # 提高随机性
            top_p=0.95,
            num_return_sequences=3
        )
    return response
def generate_alternative(user_id ,weather, features):
    """生成差异化备选方案"""
    # 方法1：调整模型参数增加多样性
    
    # 方法2：修改提示词要求不同风格
    alternative_prompt = f"""
    {construct_prompt(weather, features)}
    
    附加要求：
    - 至少包含1套与之前完全不同的风格
    - 添加一个「特别推荐」的创新搭配
    """
    
    return diversified_generation(alternative_prompt)



def save_feedback(user_id, recommendation, rating):
    # 存储用户评分（1-5分）
    c.execute("INSERT INTO feedback VALUES (?, ?, ?)", 
             (user_id, recommendation, rating))
    conn.commit()
    
    # # 当差评时触发重新生成
    # if rating < 3:
    #     new_rec = generate_alternative(user_id,)
    #     # send_push_notification(user_id, new_rec)
    #     c.execute("INSERT INTO feedback VALUES (?, ?, ?)", 
    #          (user_id, new_rec, 4))  # 这里我们人为给出
    #     conn.commit()



def full_workflow(user_id):
    # 数据获取
    # user_location = get_user_location(user_id)  # 需实现位置查询
    
    
    weather  = get_weather("Beijing")
    #  weather = get_weather('Peking University')
    # 默认位置在白鲸大学
    features = build_features(user_id)
    
    # 生成主推荐
    main_prompt = construct_prompt(weather, features)
    recommendations = generate_recommendation(main_prompt)
    
    # 解析多方案输出
    parsed_options = parse_recommendations(recommendations)  # 需要实现解析器
    
    # 存储选项
    save_feedback(user_id, recommendations, 3.5)
    # 怎么传递用户打分
    
    # 用户交互界面
    # show_selection_interface(parsed_options)  # 根据实际前端实现
    
    # 等待用户选择后...
    # save_selection(user_id, selected_index)

def parse_recommendations(text):
    """解析模型输出的多方案文本"""
    options = []
    current_option = {}
    
    for line in text.split('\n'):
        if '方案' in line and '：' in line:
            if current_option:
                options.append(current_option)
                current_option = {}
        elif '👕' in line:
            current_option['top'] = line.split('：')[-1].strip()
        elif '👖' in line:
            current_option['bottom'] = line.split('：')[-1].strip()
        elif '🧥' in line:
            current_option['coat'] = line.split('：')[-1].strip()
        elif '👟' in line:
            current_option['shoes'] = line.split('：')[-1].strip()
        elif '💡' in line:
            current_option['reason'] = line.split('：')[-1].strip()
    
    return options[:3]  # 最多返回3个方案



if __name__ == "__main__":
    # 初始化测试用户
    c.execute("INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?)", 
             ("test_user", 18, "男", "休闲,运动"))
    conn.commit()
    
    # 运行完整流程
    full_workflow("test_user")
    
    # 打印结果
    print(c.execute("SELECT * FROM history").fetchall())