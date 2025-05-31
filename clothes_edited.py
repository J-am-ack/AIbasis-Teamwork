# 多轮交互穿搭推荐系统
import requests
import sqlite3
import os
from datetime import datetime
import json
import re
from typing import List, Dict, Any, Optional
from enum import Enum


# 用env文件实现了安全的api_key管理
from dotenv import load_dotenv
load_dotenv()

# print(f"模型类型: {os.environ.get('MODEL_TYPE', '未设置')}")


# wrongtime = 0

class SessionState(Enum):
    """会话状态枚举"""
    INIT = "初始化"
    PROFILE_SETUP = "用户信息设置"
    WEATHER_CONFIRM = "天气确认"
    RECOMMENDATION_SHOWN = "推荐展示"
    FEEDBACK_COLLECTION = "反馈收集"
    REFINEMENT = "方案优化"
    COMPLETED = "完成"

class UserSession:
    """用户会话管理类"""
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.state = SessionState.INIT
        self.context = {}
        self.conversation_history = []
        self.current_recommendations = []
        self.selected_option = None
        self.feedback_score = None
        self.refinement_requests = []
        
    def add_message(self, role: str, content: str):
        """添加对话消息"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().strftime("%H:%M:%S")
        })
    
    def get_conversation_context(self) -> str:
        """获取对话上下文"""
        recent_messages = self.conversation_history[-6:]  # 最近6条消息
        context = []
        for msg in recent_messages:
            role_emoji = "🤖" if msg["role"] == "assistant" else "👤"
            context.append(f"{role_emoji} {msg['content']}")
        return "\n".join(context)

class InteractiveFashionAssistant:
    """交互式穿搭助手"""
    
    def __init__(self):
        self.sessions = {}
        self.conn, self.cursor = self.init_database()
        self.wrongtime = 0  # 初始化 wrongtime 变量
        
    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect('fashion_assistant.db')
        c = conn.cursor()
        
        # 用户表
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id TEXT PRIMARY KEY, 
                      age INT, 
                      gender TEXT, 
                      style_pref TEXT,
                      city TEXT,
                      occupation TEXT,
                      created_at TEXT)''')
        
        # 对话历史表
        c.execute('''CREATE TABLE IF NOT EXISTS conversations
                     (user_id TEXT, 
                      session_id TEXT,
                      role TEXT,
                      content TEXT,
                      timestamp TEXT)''')
        
        # 推荐历史表
        c.execute('''CREATE TABLE IF NOT EXISTS recommendations
                     (user_id TEXT, 
                      session_id TEXT,
                      recommendation_text TEXT,
                      options TEXT,
                      selected_index INT,
                      feedback_score REAL,
                      created_at TEXT)''')
        
        # 用户偏好学习表
        c.execute('''CREATE TABLE IF NOT EXISTS preferences
                     (user_id TEXT,
                      item_type TEXT,
                      item_value TEXT,
                      preference_score REAL,
                      updated_at TEXT)''')
        
        conn.commit()
        return conn, c
    
    def get_or_create_session(self, user_id: str) -> UserSession:
        """获取或创建用户会话"""
        if user_id not in self.sessions:
            self.sessions[user_id] = UserSession(user_id)
        return self.sessions[user_id]
    
    def process_user_input(self, user_id: str, user_input: str) -> str:
        """处理用户输入的主要函数"""
        session = self.get_or_create_session(user_id)
        session.add_message("user", user_input)
        
        # 根据当前状态处理输入
        if session.state == SessionState.INIT:
            response = self.handle_init_state(session, user_input)
        elif session.state == SessionState.PROFILE_SETUP:
            response = self.handle_profile_setup(session, user_input)
        elif session.state == SessionState.WEATHER_CONFIRM:
            response = self.handle_weather_confirm(session, user_input)
        elif session.state == SessionState.RECOMMENDATION_SHOWN:
            response = self.handle_recommendation_feedback(session, user_input)
        elif session.state == SessionState.FEEDBACK_COLLECTION:
            response = self.handle_feedback_collection(session, user_input)
        elif session.state == SessionState.REFINEMENT:
            response = self.handle_refinement(session, user_input)
        else:
            response = self.handle_general_conversation(session, user_input)
        
        session.add_message("assistant", response)
        return response
    
    def handle_init_state(self, session: UserSession, user_input: str) -> str:
        """处理初始状态"""
        # 检查是否是新用户
        user_data = self.cursor.execute("SELECT * FROM users WHERE id=?", (session.user_id,)).fetchone()
        
        if not user_data:
            session.state = SessionState.PROFILE_SETUP
            return """👋 很高兴认识你~ 欢迎使用AI穿搭助手！我是你的专属穿搭顾问小北。

为了给你提供更精准的穿搭建议，我需要了解一些基本信息：

📝 请告诉我：
1. 你的年龄？
2. 性别？
3. 平时喜欢什么穿搭风格？（如：休闲、商务、潮流、文艺等）
4. 所在城市？
5. 职业？



你可以一次性直接全部告诉我，也可以一个一个回答～"""
        else:
            session.state = SessionState.WEATHER_CONFIRM
            session.context['user_profile'] = {
                'age': user_data[1],
                'gender': user_data[2],
                'style_pref': user_data[3],
                'city': user_data[4] if len(user_data) > 4 else '北京',
                'occupation': user_data[5] if len(user_data) > 5 else '大学生'
            }
            
            weather = self.get_weather(session.context['user_profile']['city'])
            session.context['weather'] = weather
            
            return f"""🎉 {user_data[0]}, 欢迎回来！

📍  当前位置：{session.context['user_profile']['city']}
🌤️  今日天气：{weather['temp']}°C，{weather['conditions']}
💧  湿度：{weather['humidity']}%

需要我为你推荐今日穿搭吗？还是有其他的想法鸭qwq？"""
    
    def handle_profile_setup(self, session: UserSession, user_input: str) -> str:
        """处理用户信息设置"""
        # 使用NLP提取用户信息
        profile = self.extract_user_profile(user_input)
        
        if not session.context.get('user_profile'):
            session.context['user_profile'] = {}
        
        session.context['user_profile'].update(profile)
        
        # 检查是否收集了足够信息
        required_fields = ['age', 'gender', 'city', 'style_pref' , 'occupation']
        missing_fields = [field for field in required_fields if field not in session.context['user_profile']]
        
        if missing_fields:
            missing_text = {
                'age': '年龄',
                'gender': '性别',
                'city': '所在城市',
                'style_pref': '穿搭风格偏好',
                'occupation': '职业'
            }
            return f"好的，我已经记录了你的信息！\n\n还需要补充：{', '.join([missing_text[field] for field in missing_fields])}"
        else:
            # 保存用户信息到数据库
            self.save_user_profile(session.user_id, session.context['user_profile'])
            
            # 获取天气信息
            weather = self.get_weather(session.context['user_profile']['city'])
            session.context['weather'] = weather
            session.state = SessionState.WEATHER_CONFIRM
            
            return f"""✅ 信息收集完成！

👤 {session.context['user_profile']['age']}岁{session.context['user_profile']['gender']}性朋友
📍 {session.context['user_profile']['city']}
👔 偏好风格：{session.context['user_profile']['style_pref']}

今天是{weather['date']}！
🌤️ 今日{session.context['user_profile']['city']}天气：
温度：{weather['temp']}°C
天气：{weather['conditions']}
湿度：{weather['humidity']}%

现在开始为你推荐穿搭方案吧！✨"""
    
    def handle_weather_confirm(self, session: UserSession, user_input: str) -> str:
        """处理天气确认和生成推荐"""
        # 生成穿搭推荐
        recommendations = self.generate_smart_recommendations(session)
        session.current_recommendations = recommendations
        session.state = SessionState.RECOMMENDATION_SHOWN
        
        response = "🎯 为你精心挑选了3套穿搭方案：\n\n"
        
        for i, option in enumerate(recommendations, 1):
            response += f"**方案 {i}：{option.get('style_name', f'搭配{i}')}**\n"
            response += f"👕 上衣：{option.get('top', '未指定')}\n"
            response += f"👖 下装：{option.get('bottom', '未指定')}\n"
            response += f"🧥 外套：{option.get('coat', '无需外套')}\n"
            response += f"👟 鞋履：{option.get('shoes', '未指定')}\n"
            response += f"💡 推荐理由：{option.get('reason', '经典搭配')}\n\n"
        
        response += """你可以：
🔢 输入具体要选择方案（如：选择1）
❓ 询问某个方案的详细信息（如：方案1的颜色搭配？）
🔄 要求调整某个方案（如：方案2能换个颜色吗？）
⭐ 直接告诉我你的想法和需求"""
        
        return response
    
    def handle_recommendation_feedback(self, session: UserSession, user_input: str) -> str:
        """处理推荐反馈"""
        # global wrongtime
        user_input_lower = user_input.lower().strip()
        
        # 检测选择意图
        selection_match = re.search(r'选择?(\d+)|方案(\d+)', user_input)
        if selection_match:
            selected_num = int(selection_match.group(1) or selection_match.group(2))
            if 1 <= selected_num <= len(session.current_recommendations):
                session.selected_option = selected_num - 1
                session.state = SessionState.FEEDBACK_COLLECTION
                
                selected = session.current_recommendations[session.selected_option]
                return f"""👍 你选择了方案{selected_num}：{selected.get('style_name', f'搭配{selected_num}')}

完整搭配：
👕 {selected.get('top')}
👖 {selected.get('bottom')}
🧥 {selected.get('coat')}
👟 {selected.get('shoes')}

这套搭配满意吗？请给个评分吧：
⭐⭐⭐⭐⭐ (1-5分)

也可以告诉我：
- 哪些地方特别喜欢？
- 有什么需要调整的？
- 其他想法和建议？"""
        
        # 检测调整需求
        elif any(word in user_input for word in ['调整', '换', '改', '不喜欢', '其他', '更多', '选择']):
            session.state = SessionState.REFINEMENT
            return self.handle_refinement_request(session, user_input)
        
        # 检测询问详情
        elif '?' in user_input or '？' in user_input:
            return self.answer_detail_question(session, user_input)
        
        elif self.wrongtime == 0:
            self.wrongtime +=1
            return """小北没有get到你的想法ww/(ㄒoㄒ)/~~，你可以：

🔢 选择方案：输入"选择1"或"我要方案2"
🔄 调整方案：比如"方案1换个颜色"、"有没有更休闲的？"
❓ 询问详情：比如"方案2什么颜色？"、"这样穿会不会热？"
💭 其他需求：直接告诉我你的想法（如果是提问题记得加上'？'哦qwq）

请告诉我您的选择或需求～"""
        else:
            # global wrongtime
            # self.wrongtime +=1
            
            return self.generate_conversational_response(session, user_input)
    
    def handle_feedback_collection(self, session: UserSession, user_input: str) -> str:
        """处理反馈收集"""
        # 提取评分
        score_match = re.search(r'(\d+)分|(\d+)星', user_input)
        if score_match:
            score = int(score_match.group(1) or score_match.group(2))
            session.feedback_score = min(max(score, 1), 5)  # 限制在1-5分之间
        
        # 保存推荐和反馈
        self.save_recommendation_feedback(session)
        
        session.state = SessionState.COMPLETED
        
        response = "🙏 感谢你的反馈！"
        
        if session.feedback_score:
            if session.feedback_score >= 4:
                response += f"\n\n🎉 {session.feedback_score}分！很高兴你喜欢这套搭配！"
            elif session.feedback_score >= 3:
                response += f"\n\n😊 {session.feedback_score}分，还不错～我会继续努力！"
            else:
                response += f"\n\n😅 {session.feedback_score}分，看来还需要改进，下次我会做得更好！"
        
        response += """\n\n还有其他需要帮助的吗？
🔄 重新推荐
👔 不同场合的穿搭建议
🛍️ 单品搭配建议
💡 穿搭小贴士
❓ 其他问题"""
        
        return response
    
    def handle_refinement(self, session: UserSession, user_input: str) -> str:
        """处理方案优化"""
        refinement_prompt = self.build_refinement_prompt(session, user_input)
        refined_recommendations = self.generate_refinement(refinement_prompt)
        
        if refined_recommendations:
            session.current_recommendations = refined_recommendations
            session.state = SessionState.RECOMMENDATION_SHOWN
            
            response = "🔄 根据你的要求，我重新为你推荐：\n\n"
            
            for i, option in enumerate(refined_recommendations, 1):
                response += f"**调整后方案 {i}：**\n"
                response += f"👕 上衣：{option.get('top', '未指定')}\n"
                response += f"👖 下装：{option.get('bottom', '未指定')}\n"
                response += f"🧥 外套：{option.get('coat', '无需外套')}\n"
                response += f"👟 鞋履：{option.get('shoes', '未指定')}\n"
                response += f"💡 调整说明：{option.get('reason', '根据你的要求调整')}\n\n"
            
            response += "这样的调整如何？可以继续选择或提出其他要求～"
            return response
        else:
            return "抱歉，让我重新理解你的需求。你希望怎样调整呢？比如：\n- 颜色偏好\n- 风格调整\n- 单品替换\n- 季节适应"
    
    def handle_general_conversation(self, session: UserSession, user_input: str) -> str:
        """处理一般对话"""
        # 重置会话状态，开始新的推荐流程
        if any(word in user_input for word in ['重新', '再来', '新的', '其他']):
            session.state = SessionState.WEATHER_CONFIRM
            return "好的，让我们重新开始！有什么特殊要求吗？还是按照今天的天气推荐？"
        
        # 检测不同意图
        if any(word in user_input for word in ['场合', '约会', '工作', '运动', '学习']):
            return self.handle_occasion_based_request(session, user_input)
        elif any(word in user_input for word in ['单品', '搭配', '颜色', '款式']):
            return self.handle_styling_question(session, user_input)
        else:
            return self.generate_conversational_response(session, user_input)
    
    def extract_user_profile(self, text: str) -> Dict[str, Any]:
        """从文本中提取用户信息"""
        profile = {}
        
        # 提取年龄
        age_match = re.search(r'(\d{1,2})[岁年]', text)
        if age_match:
            profile['age'] = int(age_match.group(1))
        
        # 提取性别
        if any(word in text for word in ['男', '先生', '男性', '男生']):
            profile['gender'] = '男'
        elif any(word in text for word in ['女', '女士', '女性', '女生']):
            profile['gender'] = '女'
        
        # 提取城市
        cities = ['北京', '上海', '广州', '深圳', '杭州', '南京', '成都', '武汉', '重庆', '天津', '苏州', '西安']
        for city in cities:
            if city in text:
                profile['city'] = city
                break
        
        # 提取风格偏好
        styles = ['休闲', '商务', '潮流', '文艺', '运动', '甜美', '酷帅', '简约', '复古', '街头']
        found_styles = [style for style in styles if style in text]
        if found_styles:
            profile['style_pref'] = ','.join(found_styles)
        
        # 提取职业
        occupations = ['学生', '程序员', '教员', '教授', '科研人员', '医生', '律师', '设计师', '经理', '公务员']
        for occupation in occupations:
            if occupation in text:
                profile['occupation'] = occupation
                break
        
        return profile
    
    def get_weather(self, location: str, api_key: str = None) -> dict:
        """获取天气信息"""
        if not api_key:
            api_key = os.getenv('GD_Weather_API_KEY')
            # api_key = os.getenv("HEF_weather")
        
        if not api_key:
            return {"temp": 22, "humidity": 65, "conditions": "晴朗"}
        
        # url = f"http://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
        
        # 为了统一方便的中文服务，尝试改用高德天气API
        # 5.25
        
        url = f"https://restapi.amap.com/v3/weather/weatherInfo?key={api_key}&city={location}&extensions=all"
        
        # 换用更好用的和风
        # url = f""
        
        try:
            # response = requests.get(url, timeout=10)
            # response.raise_for_status()
            # data = response.json()
            # return {
            #     "temp": data["main"]["temp"],
            #     "humidity": data["main"]["humidity"],
            #     "conditions": data["weather"][0]["description"]
            # }
            # 解析JSON
            # data = json.loads(weather_data)

            
            response  = requests.get(url)
            data = response.json()
            # 提取实时报告时间
            report_time = data["forecasts"][0]["reporttime"]
            # print(f"数据生成时间: {report_time}")

            # 提取当天的预报数据（casts数组第一个元素）
            today_forecast = data["forecasts"][0]["casts"][0]

            # 输出白天天气信息
            # print(f"日期: {today_forecast['date']}")
            # print(f"白天气温: {today_forecast['daytemp']}℃")
            # print(f"白天天气: {today_forecast['dayweather']}")
            
            return {
                "date": today_forecast['date'],
                "temp": today_forecast['daytemp'],
                "humidity": '50  //等一手和风，高德实现不了',
                "conditions": today_forecast['dayweather']
            }
            
        except Exception as e:
            print(f"Weather API error: {e}")
            return {"temp": 20, "humidity": 50, "conditions": "未知天气"}
    
    def generate_smart_recommendations(self, session: UserSession) -> List[Dict]:
        """生成智能推荐"""
        prompt = self.build_smart_prompt(session)
        model_type = os.getenv('MODEL_TYPE', 'qwen')
        api_key = os.getenv('DASHBOARD_API_KEY')
        
        recommendations_text = self.generate_recommendation(prompt, model_type, api_key)
        return self.parse_recommendations(recommendations_text)
    
    def build_smart_prompt(self, session: UserSession) -> str:
        """构建智能提示词"""
        profile = session.context['user_profile']
        weather = session.context['weather']
        conversation_context = session.get_conversation_context()
        
        # 获取历史偏好
        historical_prefs = self.get_user_preferences(session.user_id)
        
        prompt = f"""
作为专业时尚顾问，基于以下信息为用户提供3套方案作为个性化穿搭建议，供用户选择：

【用户画像】
- 基本信息：{profile['age']}岁{profile['gender']}性
- 职业：{profile.get('occupation', '未知')}
- 风格偏好：{profile['style_pref']}
- 所在城市：{profile['city']}

【环境条件】
- 温度：{weather['temp']}°C
- 天气：{weather['conditions']}  
- 湿度：{weather['humidity']}%

【对话上下文】
{conversation_context}

【历史偏好分析】
{historical_prefs}

【输出要求】
1. 生成3套风格不同的搭配方案
2. 每套方案需要有明确的风格定位
3. 考虑用户的职业和年龄特点
4. 适应当前天气条件
5. 融入用户的风格偏好

【输出格式】
方案1：[风格名称]
👕 上衣：[具体描述]
👖 下装：[具体描述]  
🧥 外套：[具体描述或"无需外套"]
👟 鞋履：[具体描述]
💡 理由：[详细说明适合的原因]

方案2：[风格名称]
👕 上衣：[具体描述]
👖 下装：[具体描述]  
🧥 外套：[具体描述或"无需外套"]
👟 鞋履：[具体描述]
💡 理由：[详细说明适合的原因]

方案3：[风格名称]
👕 上衣：[具体描述]
👖 下装：[具体描述]  
🧥 外套：[具体描述或"无需外套"]
👟 鞋履：[具体描述]
💡 理由：[详细说明适合的原因]
"""
        return prompt
    
    def generate_recommendation(self, prompt: str, model_type: str = "qwen", api_key: str = None) -> str:
        """生成推荐（复用原有函数）"""
        if model_type == "qwen":
            return self.generate_recommendation_qwen(prompt, api_key)
        # elif model_type == "openai":
        #     return self.generate_recommendation_openai(prompt, api_key)
        else:
            return self.generate_mock_recommendation()
    
    def generate_recommendation_qwen(self, prompt: str, api_key: str = None) -> str:
        """使用通义千问API"""
        if not api_key:
            api_key = os.getenv('DASHBOARD_API_KEY')
        
        if not api_key:
            return self.generate_mock_recommendation()
        
        try:
            import dashscope
            dashscope.api_key = api_key
            
            response = dashscope.Generation.call(
                model='qwen-turbo',
                prompt=prompt,
                max_tokens=1000,
                temperature=0.7
            )
            
            if response.status_code == 200:
                return response.output.text
            else:
                return self.generate_mock_recommendation()
        except Exception as e:
            print(f"Qwen API error: {e}")
            return self.generate_mock_recommendation()
    
    # def generate_recommendation_openai(self, prompt: str, api_key: str = None) -> str:
        
    #     try:
    #         import openai
    #         if not api_key:
    #             api_key = os.getenv('OPENAI_API_KEY')
            
    #         if not api_key:
    #             return self.generate_mock_recommendation()
            
    #         client = openai.OpenAI(api_key=api_key)
    #         response = client.chat.completions.create(
    #             model="gpt-3.5-turbo",
    #             messages=[
    #                 {"role": "system", "content": "你是一位专业的时尚穿搭顾问。"},
    #                 {"role": "user", "content": prompt}
    #             ],
    #             max_tokens=1000,
    #             temperature=0.7
    #         )
    #         return response.choices[0].message.content
    #     except Exception as e:
    #         print(f"OpenAI API error: {e}")
    #         return self.generate_mock_recommendation()
    
    def generate_mock_recommendation(self) -> str:
        """生成模拟推荐"""
        return """
方案1：休闲舒适
👕 上衣：白色纯棉T恤
👖 下装：深蓝色直筒牛仔裤
🧥 外套：薄款针织开衫
👟 鞋履：小白鞋
💡 理由：经典百搭组合，适合日常休闲场合

方案2：商务休闲
👕 上衣：浅蓝色衬衫
👖 下装：卡其色休闲裤
🧥 外套：深灰色西装外套
👟 鞋履：棕色乐福鞋
💡 理由：正式中带有轻松感，适合工作和社交

方案3：街头潮流
👕 上衣：印花卫衣
👖 下装：黑色工装裤
🧥 外套：牛仔夹克
👟 鞋履：高帮帆布鞋
💡 理由：时尚个性，展现年轻活力
"""
    
    def parse_recommendations(self, text: str) -> List[Dict]:
        """解析推荐文本"""
        options = []
        lines = text.strip().split('\n')
        current_option = {}
        
        for line in lines:
            line = line.strip()
            if re.match(r'方案\d+[：:]', line):
                if current_option:
                    options.append(current_option)
                current_option = {}
                # 提取风格名称
                style_match = re.search(r'方案\d+[：:]\s*(.+)', line)
                if style_match:
                    current_option['style_name'] = style_match.group(1)
            elif '👕' in line:
                current_option['top'] = re.split('[：:]', line)[-1].strip()
            elif '👖' in line:
                current_option['bottom'] = re.split('[：:]', line)[-1].strip()
            elif '🧥' in line:
                current_option['coat'] = re.split('[：:]', line)[-1].strip()
            elif '👟' in line:
                current_option['shoes'] = re.split('[：:]', line)[-1].strip()
            elif '💡' in line:
                current_option['reason'] = re.split('[：:]', line)[-1].strip()
        
        if current_option:
            options.append(current_option)
        
        return options[:3]
    
    def save_user_profile(self, user_id: str, profile: Dict):
        """保存用户信息"""
        try:
            self.cursor.execute("""
                INSERT OR REPLACE INTO users 
                (id, age, gender, style_pref, city, occupation, created_at) 
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                profile.get('age'),
                profile.get('gender'),
                profile.get('style_pref'),
                profile.get('city'),
                profile.get('occupation'),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            self.conn.commit()
        except Exception as e:
            print(f"Error saving user profile: {e}")
    
    def save_recommendation_feedback(self, session: UserSession):
        """保存推荐和反馈"""
        try:
            session_id = f"{session.user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.cursor.execute("""
                INSERT INTO recommendations 
                (user_id, session_id, recommendation_text, options, selected_index, feedback_score, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                session.user_id,
                session_id,
                json.dumps(session.current_recommendations, ensure_ascii=False),
                json.dumps(session.current_recommendations, ensure_ascii=False),
                session.selected_option,
                session.feedback_score,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            
            # 保存对话历史
            for msg in session.conversation_history:
                self.cursor.execute("""
                    INSERT INTO conversations 
                    (user_id, session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    session.user_id,
                    session_id,
                    msg['role'],
                    msg['content'],
                    msg['timestamp']
                ))
            
            self.conn.commit()
        except Exception as e:
            print(f"Error saving recommendation feedback: {e}")
    
    def get_user_preferences(self, user_id: str) -> str:
        """获取用户历史偏好"""
        try:
            # 获取历史反馈数据
            history = self.cursor.execute("""
                SELECT options, selected_index, feedback_score 
                FROM recommendations 
                WHERE user_id=? AND feedback_score >= 4
                ORDER BY created_at DESC LIMIT 5
            """, (user_id,)).fetchall()
            
            if not history:
                return "无历史偏好数据"
            
            preferences = []
            for record in history:
                try:
                    options = json.loads(record[0])
                    selected_idx = record[1]
                    if selected_idx is not None and 0 <= selected_idx < len(options):
                        selected_option = options[selected_idx]
                        preferences.append(f"喜欢：{selected_option.get('style_name', '未知风格')}")
                except:
                    continue
            
            return "历史偏好：" + "，".join(preferences[:3]) if preferences else "无明确偏好"
        except Exception as e:
            print(f"Error getting user preferences: {e}")
            return "偏好数据获取失败"
    
    def handle_refinement_request(self, session: UserSession, user_input: str) -> str:
        """处理优化请求"""
        session.refinement_requests.append(user_input)
        
        # 分析用户的调整需求
        refinement_analysis = self.analyze_refinement_request(user_input)
        
        return f"""我明白你的需求：{refinement_analysis}

让我为你重新调整方案～

你还可以具体说明：
🎨 **颜色偏好**："我想要更亮的颜色" / "喜欢深色系"
👔 **风格调整**："更商务一些" / "要更休闲的"
🔄 **单品替换**："换个上衣" / "不要外套"
🌡️ **舒适度**："要更透气的" / "保暖一些"

请告诉我具体想怎么调整？"""
    
    def analyze_refinement_request(self, request: str) -> str:
        """分析用户的调整请求"""
        request_lower = request.lower()
        
        if any(word in request for word in ['颜色', '色彩', '亮', '暗', '深', '浅', '白', '黑', '撞色', '刺眼', '红', '绿','交叉色', '纯色']):
            return "调整颜色搭配"
        elif any(word in request for word in ['风格', '休闲', '商务', '正式', '潮流']):
            return "调整穿搭风格"
        elif any(word in request for word in ['热', '冷', '透气', '保暖', '厚', '薄']):
            return "调整舒适度和温度适应性"
        elif any(word in request for word in ['上衣', '下装', '外套', '鞋子', '换']):
            return "替换特定单品"
        else:
            return "优化整体搭配方案"
    
    def build_refinement_prompt(self, session: UserSession, refinement_request: str) -> str:
        """构建优化提示词"""
        original_recommendations = session.current_recommendations
        profile = session.context['user_profile']
        weather = session.context['weather']
        
        prompt = f"""
根据用户反馈优化穿搭方案：

【原方案】
{self.format_recommendations_for_prompt(original_recommendations)}

【用户反馈】
{refinement_request}

【用户信息】
- {profile['age']}岁{profile['gender']}性
- 风格偏好：{profile['style_pref']}
- 当前天气：{weather['temp']}°C，{weather['conditions']}

【优化要求】
1. 根据用户反馈调整方案
2. 保持与天气和用户特征的匹配
3. 提供3个调整后的方案
4. 说明调整的具体原因

【输出格式】
方案1：[调整后风格名称]
👕 上衣：[具体描述]
👖 下装：[具体描述]
🧥 外套：[具体描述]
👟 鞋履：[具体描述]
💡 调整说明：[说明针对用户反馈做了什么调整]

方案2：...
方案3：...
"""
        return prompt
    
    def format_recommendations_for_prompt(self, recommendations: List[Dict]) -> str:
        """格式化推荐方案用于提示词"""
        formatted = []
        for i, rec in enumerate(recommendations, 1):
            formatted.append(f"""方案{i}：{rec.get('style_name', f'方案{i}')}
- 上衣：{rec.get('top', '未指定')}
- 下装：{rec.get('bottom', '未指定')}
- 外套：{rec.get('coat', '无')}
- 鞋履：{rec.get('shoes', '未指定')}""")
        return "\n\n".join(formatted)
    
    def generate_refinement(self, prompt: str) -> List[Dict]:
        """生成优化方案"""
        model_type = os.getenv('MODEL_TYPE', 'qwen')
        api_key = os.getenv('DASHBOARD_API_KEY')
        
        refined_text = self.generate_recommendation(prompt, model_type, api_key)
        return self.parse_recommendations(refined_text)
    
    def answer_detail_question(self, session: UserSession, question: str) -> str:
        """回答详细问题"""
        # 提取问题中的方案编号
        scheme_match = re.search(r'方案(\d+)', question)
        if scheme_match:
            scheme_num = int(scheme_match.group(1)) - 1
            if 0 <= scheme_num < len(session.current_recommendations):
                scheme = session.current_recommendations[scheme_num]
                return self.generate_detailed_answer(scheme, question)
        
        # 通用问题处理
        return self.generate_conversational_response(session, question)
    
    def generate_detailed_answer(self, scheme: Dict, question: str, session = UserSession) -> str:
        """生成详细回答"""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['颜色', '色彩']):
            return f"""关于方案的颜色搭配：

👕 **上衣**：{scheme.get('top', '未指定')}
👖 **下装**：{scheme.get('bottom', '未指定')}
🧥 **外套**：{scheme.get('coat', '无需外套')}

💡 **颜色建议**：这套搭配采用经典的色彩组合，既不会过于单调，也不会太过鲜艳，适合日常穿着。

还想了解什么具体细节吗？"""
        
        elif any(word in question_lower for word in ['搭配', '组合', '效果']):
            return f"""这套搭配的整体效果：

✨ **风格定位**：{scheme.get('style_name', '未知风格')}
🎯 **适合场合**：{self.get_suitable_occasions(scheme)}
👍 **搭配亮点**：{scheme.get('reason', '经典搭配')}

整体来说，这套搭配既实用又有型，你觉得怎么样？"""
        
        elif any(word in question_lower for word in ['热', '冷', '温度', '舒适']):
            weather = session.context.get('weather', {})
            return f"""关于穿着舒适度：

🌡️ **当前温度**：{weather.get('temp', '未知')}°C
👕 **透气性**：这套搭配的面料选择考虑了当前天气
🧥 **层次搭配**：可以根据温度变化灵活调整外套

如果觉得会热/冷，我可以为你调整！"""
        
        else:
            return f"""关于方案{scheme.get('style_name', '这套搭配')}：

{self.format_scheme_details(scheme)}

还有什么想了解的吗？比如：
- 具体的颜色搭配
- 适合的场合
- 舒适度如何
- 如何调整"""
    
    def get_suitable_occasions(self, scheme: Dict) -> str:
        """获取适合场合"""
        style_name = scheme.get('style_name', '').lower()
        
        if '商务' in style_name or '正式' in style_name:
            return "工作会议、商务场合、正式聚会"
        elif '休闲' in style_name or '舒适' in style_name:
            return "日常外出、朋友聚会、购物逛街"
        elif '运动' in style_name or '活力' in style_name:
            return "运动健身、户外活动、休闲运动"
        elif '潮流' in style_name or '街头' in style_name:
            return "时尚聚会、创意工作、个性展示"
        else:
            return "多种日常场合"
    
    def format_scheme_details(self, scheme: Dict) -> str:
        """格式化方案详情"""
        return f"""👕 **上衣**：{scheme.get('top', '未指定')}
👖 **下装**：{scheme.get('bottom', '未指定')}
🧥 **外套**：{scheme.get('coat', '无需外套')}
👟 **鞋履**：{scheme.get('shoes', '未指定')}
💡 **推荐理由**：{scheme.get('reason', '经典搭配')}"""
    
    def handle_occasion_based_request(self, session: UserSession, user_input: str) -> str:
        """处理基于场合的请求"""
        occasion = self.extract_occasion(user_input)
        
        # 构建场合相关的提示词
        occasion_prompt = self.build_occasion_prompt(session, occasion)
        model_type = os.getenv('MODEL_TYPE', 'qwen')
        api_key = os.getenv('DASHBOARD_API_KEY')
        
        recommendations = self.generate_recommendation(occasion_prompt, model_type, api_key)
        parsed_recommendations = self.parse_recommendations(recommendations)
        
        session.current_recommendations = parsed_recommendations
        session.state = SessionState.RECOMMENDATION_SHOWN
        
        response = f"🎯 为你推荐适合**{occasion}**的穿搭方案：\n\n"
        
        for i, option in enumerate(parsed_recommendations, 1):
            response += f"**方案 {i}：{option.get('style_name', f'搭配{i}')}**\n"
            response += self.format_scheme_details(option) + "\n\n"
        
        response += "选择你喜欢的方案，或告诉我需要调整的地方～"
        return response
    
    def extract_occasion(self, text: str) -> str:
        """提取场合信息"""
        occasions = {
            '约会': '约会',
            '工作': '工作',
            '面试': '面试',
            '聚会': '聚会',
            '运动': '运动',
            '旅行': '旅行',
            '婚礼': '婚礼',
            '派对': '派对',
            '商务': '商务会议',
            '休闲': '休闲外出'
        }
        
        for keyword, occasion in occasions.items():
            if keyword in text:
                return occasion
        
        return "日常外出"
    
    def build_occasion_prompt(self, session: UserSession, occasion: str) -> str:
        """构建场合相关提示词"""
        profile = session.context['user_profile']
        weather = session.context['weather']
        
        return f"""
为{occasion}场合推荐穿搭方案：

【用户信息】
- {profile['age']}岁{profile['gender']}性
- 风格偏好：{profile['style_pref']}
- 职业：{profile.get('occupation', '未知')}

【场合要求】
- 目标场合：{occasion}
- 当前天气：{weather['temp']}°C，{weather['conditions']}

【输出要求】
1. 生成3套适合{occasion}的搭配方案
2. 考虑场合的正式程度和氛围
3. 兼顾天气和个人风格
4. 给出具体的穿搭建议和理由

【输出格式】
方案1：[适合{occasion}的风格名称]
👕 上衣：[具体描述]
👖 下装：[具体描述]  
🧥 外套：[具体描述]
👟 鞋履：[具体描述]
💡 理由：[为什么适合这个场合]

方案2：...
方案3：...
"""
    
    def handle_styling_question(self, session: UserSession, user_input: str) -> str:
        """处理穿搭问题"""
        return f"""关于穿搭的问题，我来为你解答！

你的问题：{user_input}

💡 **穿搭小贴士**：
- **颜色搭配**：同色系搭配最安全，撞色搭配要谨慎
- **层次感**：内浅外深，或内深外浅都很好看
- **比例协调**：上松下紧，或上紧下松
- **配饰加分**：简单的配饰可以提升整体效果

需要针对具体情况给出建议吗？比如：
🎨 颜色搭配方案
👔 特定单品的搭配
🌟 风格转换技巧
📏 身材优化穿搭"""
    
    def generate_conversational_response(self, session: UserSession, user_input: str) -> str:
        """生成对话式回应"""
        # 构建对话提示词
        conversation_prompt = f"""
作为年轻人的专业穿搭顾问，请回答用户的问题：

【用户问题】
{user_input}

【用户背景】
{session.context.get('user_profile', {})}

【对话历史】
{session.get_conversation_context()}

请以专业、友好、实用的方式回答，可以包含：
- 直接回答问题
- 相关的穿搭建议
- 实用小贴士
- 进一步的问题引导

保持对话自然流畅，语气亲切专业。
"""
        
        model_type = os.getenv('MODEL_TYPE', 'qwen')
        api_key = os.getenv('DASHBOARD_API_KEY')
        
        response = self.generate_recommendation(conversation_prompt, model_type, api_key)
        
        # 如果API调用失败，使用默认回复
        if not response or "方案1" in response:
            return f"""我理解你的问题！

作为你的穿搭顾问，我可以帮你：
🎯 **个性化推荐**：根据你的喜好和场合推荐搭配
🎨 **搭配建议**：颜色、风格、单品的具体建议  
💡 **穿搭技巧**：分享实用的穿搭小贴士
🔄 **方案调整**：随时根据你的反馈优化方案

还有什么想了解的吗？或者需要我为你推荐新的穿搭方案？"""
        
        return response
    
    def reset_session(self, user_id: str):
        """重置用户会话"""
        if user_id in self.sessions:
            del self.sessions[user_id]
    
    def close_database(self):
        """关闭数据库连接"""
        if self.conn:
            self.conn.close()

# 交互式命令行界面
class FashionCLI:
    """命令行交互界面"""
    
    def __init__(self):
        self.assistant = InteractiveFashionAssistant()
        self.current_user = None
    
    def start(self):
        """启动交互式界面"""
        print("🎉 欢迎使用智能穿搭助手小北！我是由传奇debug王（没有AI就不会写代码）的yjm开发的颠覆级穿搭推荐agent。")
        print("=" * 50)
        
        # 用户登录/注册
        self.current_user = input("请输入你的用户名（新用户会自动注册）：").strip()
        if not self.current_user:
            self.current_user = f"user_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"\n👋 你好，{self.current_user}！")
        print("\n💡 使用提示：在使用过程中，你始终可以操作以下指令：")
        print("- 输入 'quit' 或 'exit' 退出")
        print("- 输入 'restart' 重新开始")
        print("- 输入 'help' 查看帮助")
        print("- 直接输入你的需求或问题小北都会耐心帮你解答啦~")
        print("- 没有疑问的话输入OK就可以开始和我聊天了呀😊")
        print("-" * 50)
        
        # 开始对话循环
        self.chat_loop()
    
    def chat_loop(self):
        """对话循环"""
        while True:
            try:
                user_input = input(f"\n{self.current_user}: ").strip()
                
                if not user_input:
                    continue
                
                # 处理特殊命令
                if user_input.lower() in ['quit', 'exit', '退出']:
                    print("\n👋 感谢你和小北对话，再见！")
                    break
                elif user_input.lower() in ['restart', '重新开始']:
                    self.assistant.reset_session(self.current_user)
                    print("\n🔄 会话已重置，让我们重新开始！输入OK和小北聊天哇~")
                    continue
                elif user_input.lower() in ['help', '帮助']:
                    self.show_help()
                    continue
                
                # 处理用户输入
                print("\n🤖 小北正在思考...")
                response = self.assistant.process_user_input(self.current_user, user_input)
                print(f"\n🤖 小北: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 感谢你陪小北聊天，再见！")
                break
            except Exception as e:
                print(f"\n❌ 出现错误：{e}")
                print("请重试或输入 'restart' 重新开始")
    
    def show_help(self):
        """显示帮助信息"""
        help_text = """
🆘 **穿搭助手小北使用指南**

**基本功能：**
🎯 个性化穿搭推荐 - "帮我推荐今天的穿搭"
🎨 场合穿搭建议 - "我要去约会，怎么穿？"
🔄 方案调整优化 - "能换个颜色吗？"
⭐ 穿搭评分反馈 - "这套我给4分"

**交互示例：**
👤 "我是19岁男生，在北京，喜欢休闲风格"
👤 "今天有点冷，推荐几套穿搭"
👤 "选择方案1"
👤 "方案2能不能换成蓝色的？"
👤 "我要去参加ICLR做论文报告（doge)，怎么穿比较合适？"

**命令说明：**
- restart：重新开始对话
- quit/exit：退出程序
- help：显示此帮助

直接输入你的需求，我会智能理解并提供帮助！
"""
        print(help_text)

# 主程序入口
if __name__ == "__main__":
    try:
        cli = FashionCLI()
        cli.start()
    except Exception as e:
        print(f"程序启动失败：{e}")
        print("请检查环境配置和依赖库安装")
    finally:
        # 清理资源
        try:
            cli.assistant.close_database()
        except:
            pass