import sqlite3
import random
from datetime import datetime
from typing import Dict, List

# ======================
# 数据库初始化（包含用户画像）
# ======================
conn = sqlite3.connect('dietary.db')
c = conn.cursor()

# 创建包含用户画像的表结构
c.execute('''CREATE TABLE IF NOT EXISTS users
             (id TEXT PRIMARY KEY, 
              age INT, 
              gender TEXT,
              height REAL,  # 新增身高(cm)
              weight REAL,  # 新增体重(kg)
              bmi REAL,     # 新增BMI
              body_goal TEXT,  # 身材目标（减脂/增肌/保持）
              activity_level TEXT,  # 运动习惯（久坐/轻度/中度/高强度）
              waist_hip_ratio REAL,  # 腰臀比
              dietary_restrictions TEXT,
              preference TEXT)''')

# 饮食计划表（新增字段）
c.execute('''CREATE TABLE IF NOT EXISTS meal_plan
             (user_id TEXT, 
              date TEXT, 
              meal_plan TEXT,
              nutrition_info TEXT,
              selected_meal TEXT,
              waist_target REAL)''')  # 新增腰围目标
conn.commit()

# ======================
# 用户画像增强模块
# ======================
USER_PROFILE = {
    "PKU_STU_001": {
        "height": 175.0,
        "weight": 68.0,
        "bmi": 21.9,
        "body_goal": "减脂",
        "activity_level": "中度",
        "waist_hip_ratio": 0.75,
        "dietary_restrictions": "乳糖不耐",
        "preference": "川菜"
    }
}

def calculate_bmi(height: float, weight: float) -> float:
    """计算BMI指数"""
    return round(weight / ((height/100)**2), 1)

def enhance_user_profile(user_id: str) -> Dict:
    """增强用户画像数据"""
    base_data = c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    profile = {
        "height": base_data[2],
        "weight": base_data[3],
        "bmi": USER_PROFILE[user_id]["bmi"],
        "body_goal": USER_PROFILE[user_id]["body_goal"],
        "activity_level": USER_PROFILE[user_id]["activity_level"],
        "waist_hip_ratio": USER_PROFILE[user_id]["waist_hip_ratio"],
        "restrictions": base_data[3].split(',') if base_data[3] else [],
        "preference": base_data[4].split(',') if base_data[4] else []
    }
    return profile

# ======================
# 增强型天气饮食规则
# ======================
WEATHER_DIET_MAPPING = {
    "晴朗": {
        "recommend": "补充维生素D食物",
        "avoid": ["高糖饮料"],
        "bmi_adjust": {"减脂": "+增加蛋白质比例"}
    },
    "小雨": {
        "recommend": "热汤暖胃饮食",
        "avoid": ["生冷食物"],
        "bmi_adjust": {"增肌": "+增加碳水摄入"}
    },
    # 其他天气规则...
}

# ======================
# 增强型提示词构建
# ======================
def construct_enhanced_prompt(weather: Dict, profile: Dict) -> str:
    """构建包含用户画像的增强提示"""
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
- 偏好：{', '.join(profile['preference']) or '无'}

环境参数：
- 日期：{weather['date']}
- 温度：{weather['temp']}℃
- 天气状况：{weather['conditions']}
- 湿度：{weather['humidity']}%
- 饮食规则：{WEATHER_DIET_MAPPING[weather['conditions']]['recommend']}

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
# BMI分类函数
# ======================
def get_bmi_category(bmi: float) -> str:
    if bmi < 18.5:
        return "underweight"
    elif 18.5 <= bmi < 24:
        return "normal"
    elif 24 <= bmi < 28:
        return "overweight"
    else:
        return "obese"

# ======================
# 模型交互增强
# ======================
def generate_enhanced_plan(prompt: str) -> str:
    """生成考虑用户画像的饮食方案"""
    messages = [{"role": "user", "content": prompt}]
    response = model.chat(tokenizer, messages)
    
    # 验证营养信息完整性
    if "蛋白质" not in response or "热量" not in response:
        print("警告：模型输出缺少关键营养信息")
    return response

# ======================
# 主流程
# ======================
def full_workflow(user_id: str):
    # 获取增强用户画像
    profile = enhance_user_profile(user_id)
    
    # 获取环境数据
    weather = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "temp": random.uniform(10, 25),
        "conditions": random.choice(["晴朗", "多云", "小雨"]),
        "humidity": random.randint(40, 80)
    }
    
    # 构建专业提示
    prompt = construct_enhanced_prompt(weather, profile)
    
    # 生成饮食方案
    plan = generate_enhanced_plan(prompt)
    
    # 存储结果
    save_plan(user_id, plan, 4)
    
    # 打印结果
    print(plan)

if __name__ == "__main__":
    # 初始化测试用户（包含完整画像数据）
    c.execute('''INSERT OR IGNORE INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
             ("PKU_STU_001", 20, "男", 175.0, 68.0, None, 
              "乳糖不耐", "川菜", None, None, None))
    conn.commit()
    
    # 运行完整流程
    full_workflow("PKU_STU_001")
    
    # 查看生成的方案
    print("\n最新饮食计划：")
    print(c.execute("SELECT meal_plan FROM meal_plan ORDER BY date DESC LIMIT 1").fetchone())
