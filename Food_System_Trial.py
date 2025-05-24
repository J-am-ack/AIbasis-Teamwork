import os
import sqlite3
import random
from datetime import datetime
from typing import Dict, List, Tuple
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from geopy.distance import geodesic
from transformers import AutoModelForCausalLM, AutoTokenizer

# 加载环境变量
load_dotenv()
API_KEY = os.getenv("OPENWEATHER_API_KEY")

# 数据库配置
DATABASE_URL = "sqlite:///dietary.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ======================
# 数据模型定义
# ======================
class User(Base):
    __tablename__ = "users"
    id = Column(String(20), primary_key=True)
    age = Column(Integer)
    gender = Column(String(10))
    height = Column(Float)
    weight = Column(Float)
    bmi = Column(Float)
    body_goal = Column(String(20))
    activity_level = Column(String(20))
    waist_hip_ratio = Column(Float)
    dietary_restrictions = Column(String(200))
    preferences = Column(String(200))

class MealPlan(Base):
    __tablename__ = "meal_plan"
    id = Column(Integer, primary_key=True)
    user_id = Column(String(20))
    date = Column(String(20))
    plan = Column(Text)
    nutrition_info = Column(Text)
    selected_meal = Column(Integer)
    waist_target = Column(Float)

Base.metadata.create_all(bind=engine)

# ======================
# 增强型用户画像
# ======================
def get_user_profile(user_id: str) -> Dict:
    session = SessionLocal()
    user = session.query(User).filter(User.id == user_id).first()
    
    return {
        "gender": user.gender,
        "age": user.age,
        "bmi": user.bmi,
        "body_goal": user.body_goal,
        "activity_level": user.activity_level,
        "waist_hip_ratio": user.waist_hip_ratio,
        "restrictions": user.dietary_restrictions.split(',') if user.dietary_restrictions else [],
        "preferences": user.preferences.split(',') if user.preferences else []
    }

# ======================
# 食堂管理系统
# ======================
CAFETERIAS = {
    "学一食堂": {
        "location": (40.0035, 116.3270),
        "features": ["川菜", "面食", "早餐供应早"],
        "hours": {
            "早餐": ("06:50", "08:30"),
            "午餐": ("11:00", "13:30"),
            "晚餐": ("17:00", "19:00")
        }
    },
    "农园食堂": {
        "location": (40.0042, 116.3255),
        "features": ["清真", "面食", "自选菜"],
        "hours": {
            "早餐": ("07:00", "08:30"),
            "午餐": ("11:00", "13:30"),
            "晚餐": ("17:00", "19:00")
        }
    }
}

class CafeteriaManager:
    @staticmethod
    def get_available_cafeterias(current_time, user_location):
        available = []
        for name, data in CAFETERIAS.items():
            if CafeteriaManager.is_cafeteria_open(data["hours"], current_time):
                distance = geodesic(user_location, data["location"]).meters
                available.append({
                    "name": name,
                    "distance": distance,
                    "features": data["features"],
                    "hours": data["hours"]
                })
        return sorted(available, key=lambda x: (x["distance"], -len(x["features"])))

    @staticmethod
    def is_cafeteria_open(hours, current_time):
        check_time = current_time.time()
        for meal, (start, end) in hours.items():
            start_t = datetime.strptime(start, "%H:%M").time()
            end_t = datetime.strptime(end, "%H:%M").time()
            if start_t <= end_t:
                if start_t <= check_time <= end_t:
                    return True
            else:
                if check_time >= start_t or check_time <= end_t:
                    return True
        return False

# ======================
# 增强型提示构建
# ======================
WEATHER_DIET_MAPPING = {
    "晴朗": {"recommend": "补充维生素D食物", "bmi_adjust": {"减脂": "+增加蛋白质比例"}},
    "小雨": {"recommend": "热汤暖胃饮食", "bmi_adjust": {"增肌": "+增加碳水摄入"}}
}

def construct_enhanced_prompt(weather: Dict, profile: Dict) -> str:
    bmi_status = {
        "underweight": "体重过轻",
        "normal": "正常范围",
        "overweight": "超重",
        "obese": "肥胖"
    }.get(get_bmi_category(profile['bmi']), '正常范围')

    prompt = f"""
你是一位专业营养师，请为北京大学学生制定个性化饮食方案：

用户画像：
- 性别：{profile['gender']}性 | 年龄：{profile['age']}岁
- 身体数据：BMI {profile['bmi']} ({bmi_status}) | 腰臀比 {profile['waist_hip_ratio']}
- 目标：{profile['body_goal']} | 运动频率：{profile['activity_level']}
- 饮食限制：{', '.join(profile['restrictions']) or '无'}
- 偏好：{', '.join(profile['preferences']) or '无'}

环境参数：
- 日期：{weather['date']}
- 温度：{weather['temp']}℃
- 天气状况：{weather['conditions']}
- 湿度：{weather['humidity']}%
- 饮食规则：{WEATHER_DIET_MAPPING.get(weather['conditions'], {}).get('recommend', '')}

专业建议要求：
1. 根据BMI状态调整三大营养素比例（蛋白质/碳水/脂肪）
2. 结合运动强度推荐蛋白质摄入量（久坐：0.8g/kg，中度：1.2g/kg，高强度：1.6g/kg）
3. 针对腰臀比提供腹部脂肪管理建议
4. 使用emoji增强可读性
5. 输出3套差异化方案（早/中/晚）

输出格式示例：
方案1：
早餐：🥚 食物描述（热量：XX大卡 | 蛋白质：XXg）
午餐：🍱 食物描述（热量：XX大卡 | 蛋白质：XXg）
晚餐：🍲 食物描述（热量：XX大卡 | 蛋白质：XXg）
专业建议：结合BMI和运动量的营养说明

（共3个方案）
    """
    return prompt

# ======================
# 核心推荐引擎
# ======================
class NutritionRecommender:
    def __init__(self):
        self.model_name = "Qwen/Qwen-1_8B-Chat-Int4"
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            device_map="auto",
            torch_dtype=torch.float16,
            low_cpu_mem_usage=True
        )

    def generate_plan(self, prompt: str) -> str:
        messages = [{"role": "user", "content": prompt}]
        response = self.model.chat(self.tokenizer, messages)
        
        if "蛋白质" not in response or "热量" not in response:
            print("警告：模型输出缺少关键营养信息")
        return response

# ======================
# 主工作流
# ======================
def full_workflow(user_id: str):
    session = SessionLocal()
    
    # 获取用户数据
    profile = get_user_profile(user_id)
    
    # 获取环境数据
    weather = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "temp": random.uniform(10, 25),
        "conditions": random.choice(["晴朗", "多云", "小雨"]),
        "humidity": random.randint(40, 80)
    }
    
    # 构建提示词
    prompt = construct_enhanced_prompt(weather, profile)
    
    # 生成饮食方案
    recommender = NutritionRecommender()
    plan = recommender.generate_plan(prompt)
    
    # 获取可用食堂
    current_time = datetime.now()
    cafeterias = CafeteriaManager.get_available_cafeterias(current_time, (40.0035, 116.3270))
    
    # 存储结果
    meal_plan = MealPlan(
        user_id=user_id,
        date=weather['date'],
        plan=plan,
        nutrition_info="根据BMI和运动量定制",
        selected_meal=1,
        waist_target=profile['bmi'] * 0.5  # 示例计算值
    )
    session.add(meal_plan)
    session.commit()
    
    return plan

if __name__ == "__main__":
    # 初始化测试用户
    session = SessionLocal()
    if not session.query(User).filter(User.id == "PKU_STU_001").first():
        new_user = User(
            id="PKU_STU_001",
            age=20,
            gender="男",
            height=175.0,
            weight=68.0,
            bmi=calculate_bmi(175.0, 68.0),
            body_goal="减脂",
            activity_level="中度",
            waist_hip_ratio=0.75,
            dietary_restrictions="乳糖不耐",
            preferences="川菜"
        )
        session.add(new_user)
        session.commit()
    
    # 执行完整流程
    result = full_workflow("PKU_STU_001")
    print("最新饮食方案：")
    print(result)
    
    # 查看历史记录
    print("\n历史饮食计划：")
    for plan in session.query(MealPlan).filter_by(user_id="PKU_STU_001").order_by(MealPlan.date.desc()).all():
        print(f"日期：{plan.date}\n方案：{plan.plan[:200]}...")
