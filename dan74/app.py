from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import json
import os
import httpx
from datetime import datetime, timedelta
from openai import OpenAI

app = Flask(__name__)
app.secret_key = 'pku_dining_planner_secret_key'

# 初始化OpenAI客户端
client = OpenAI(
    api_key="sk-c9cc12071c1642e0829f91335ba50c56", 
    base_url="https://api.deepseek.com", 
    http_client=httpx.Client(verify=False)
)

# 加载食堂数据
def load_canteen_data():
    try:
        file_path = os.path.join(os.path.dirname(__file__), '北京大学食堂菜谱数据集-66eb503d54.json')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if not isinstance(data, dict):
                print("食堂数据格式不正确，应为字典")
                return {"canteens": []}
            if "canteens" not in data or not isinstance(data["canteens"], list):
                data["canteens"] = []
                
            for canteen in data.get("canteens", []):
                if isinstance(canteen, dict):
                    if "hours" not in canteen:
                        canteen["hours"] = {
                            "breakfast": "6:30-9:00",
                            "lunch": "10:30-13:30",
                            "dinner": "17:00-19:30"
                        }
                
            return data
    except Exception as e:
        print(f"加载食堂数据失败: {str(e)}")
        return {
            "canteens": [
                {
                    "id": 1,
                    "name": "学一食堂",
                    "location": "第一教学楼附近",
                    "features": ["经济实惠", "品种多样"],
                    "hours": {
                        "breakfast": "6:30-9:00",
                        "lunch": "10:30-13:30",
                        "dinner": "17:00-19:30"
                    },
                    "dishes": []
                },
                {
                    "id": 2,
                    "name": "农园食堂",
                    "location": "农园路",
                    "features": ["特色菜品", "环境优美"],
                    "hours": {
                        "breakfast": "6:30-9:00",
                        "lunch": "10:30-13:30",
                        "dinner": "17:00-19:30"
                    },
                    "dishes": []
                }
            ]
        }

# 加载知识图谱数据
def load_knowledge_graph():
    try:
        file_path = os.path.join(os.path.dirname(__file__), '饮食健康关联知识图谱基础数据库-473840c6d1.json')
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 验证数据格式
            if not isinstance(data, dict):
                print("知识图谱数据格式不正确，应为字典")
                return {"nodes": [], "links": []}
                
            # 确保包含必要的键
            if "nodes" not in data or not isinstance(data["nodes"], list):
                data["nodes"] = []
            if "links" not in data or not isinstance(data["links"], list):
                data["links"] = []
                
            return data
    except Exception as e:
        print(f"加载知识图谱数据失败: {str(e)}")
        return {"nodes": [], "links": []}

# 加载问答数据集
def load_qa_dataset():
    qa_data = []
    qa_files = [
        os.path.join(os.path.dirname(__file__), '饮食健康问答数据集-4f5619f42b.json'),
        os.path.join(os.path.dirname(__file__), '饮食健康问答数据集-7688752c2b.json')
    ]
    for file in qa_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # 检查加载的数据是否为列表
                if isinstance(data, list):
                    # 验证每个条目是否为字典并且包含必要的字段
                    for item in data:
                        if isinstance(item, dict) and 'question' in item and 'answer' in item:
                            qa_data.append(item)
                        elif isinstance(item, str):
                            # 尝试解析字符串为JSON
                            try:
                                item_dict = json.loads(item)
                                if isinstance(item_dict, dict) and 'question' in item_dict and 'answer' in item_dict:
                                    qa_data.append(item_dict)
                            except:
                                qa_data.append({
                                    'question': '健康饮食问题',
                                    'answer': '保持均衡饮食，多吃蔬果，适量运动。',
                                    'topic': '营养知识'
                                })
                elif isinstance(data, dict):
                    if 'qa' in data and isinstance(data['qa'], list):
                        for item in data['qa']:
                            if isinstance(item, dict) and 'question' in item and 'answer' in item:
                                qa_data.append(item)
        except Exception as e:
            print(f"加载问答数据集 {file} 失败: {str(e)}")
    
    if not qa_data:
        qa_data = [
            {
                'question': '什么是健康的饮食习惯？',
                'answer': '健康的饮食习惯包括：定时定量进餐，多吃蔬果，少吃高脂高糖食物，保证蛋白质摄入，多喝水。',
                'topic': '营养知识'
            },
            {
                'question': '大学生应该如何合理安排三餐？',
                'answer': '大学生应该保证早餐的质量，午餐摄入足够的能量，晚餐适量，避免夜宵。可以根据课表安排在就近的食堂就餐。',
                'topic': '营养知识'
            },
            {
                'question': '北大有哪些食堂适合早餐？',
                'answer': '北大的学一食堂、农园食堂、燕南食堂等都提供丰富的早餐选择，包括包子、粥、豆浆、鸡蛋等传统早餐。',
                'topic': '校园饮食'
            }
        ]
    
    return qa_data

# 计算营养需求
def calculate_nutrition_needs(user_info):
    try:
        weight = float(user_info.get('weight', 60))
        height = float(user_info.get('height', 170))
        age = int(user_info.get('age', 20))
        gender = user_info.get('gender', '男')
        activity_level = user_info.get('activity_level', '中等')
        health_goal = user_info.get('health_goal', '保持健康')
        
        # 验证输入数据
        if weight <= 0 or height <= 0 or age <= 0:
            raise ValueError("身高、体重和年龄必须为正数")
        
        # 计算BMI
        bmi = weight / ((height/100) ** 2)
        
        # 计算基础代谢率(BMR) 
        if gender == '男':
            bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
        else:
            bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        
        # 活动水平系数
        activity_multipliers = {
            '久坐': 1.2, 
            '轻度': 1.375,  
            '中等': 1.55,  
            '积极': 1.725,  
            '非常积极': 1.9  
        }
        
        # 计算每日总能量消耗(TDEE)
        tdee = bmr * activity_multipliers.get(activity_level, 1.55)
        
        # 根据健康目标调整热量
        goal_adjustments = {
            '减重': -500,  # 每天减少500卡路里
            '增重': 500,   # 每天增加500卡路里
            '保持健康': 0
        }
        
        daily_calories = tdee + goal_adjustments.get(health_goal, 0)
        
        # 计算宏营养素
        if health_goal == '减重':
            protein_ratio = 0.35  # 35%蛋白质
            fat_ratio = 0.25      # 25%脂肪
            carbs_ratio = 0.40    # 40%碳水
        elif health_goal == '增重':
            protein_ratio = 0.30  # 30%蛋白质
            fat_ratio = 0.25      # 25%脂肪
            carbs_ratio = 0.45    # 45%碳水
        else:
            protein_ratio = 0.30  # 30%蛋白质
            fat_ratio = 0.25      # 25%脂肪
            carbs_ratio = 0.45    # 45%碳水
        
        # 计算各营养素的具体克数
        protein = (daily_calories * protein_ratio) / 4  # 1g蛋白质=4卡路里
        fat = (daily_calories * fat_ratio) / 9         # 1g脂肪=9卡路里
        carbs = (daily_calories * carbs_ratio) / 4     # 1g碳水=4卡路里
        
        # 计算其他营养需求
        fiber = 14 * (daily_calories / 1000)  # 每1000卡路里14g膳食纤维
        water = weight * 30  # 每公斤体重30ml水
        
        # 根据BMI调整建议
        bmi_suggestions = []
        if bmi < 18.5:
            bmi_suggestions.append("您的BMI偏低，建议适当增加能量摄入，注意优质蛋白的补充")
        elif bmi >= 25:
            bmi_suggestions.append("您的BMI偏高，建议控制能量摄入，增加运动量")
        else:
            bmi_suggestions.append("您的BMI在正常范围内，建议保持当前的饮食和运动习惯")
        
        # 添加基于活动水平的建议
        if activity_level in ['久坐', '轻度']:
            bmi_suggestions.append("您的活动量偏低，建议增加日常活动和运动量")
        
        # 添加基于年龄的建议
        if age < 25:
            bmi_suggestions.append("年轻人要注意营养均衡，为身体发育提供充足营养")
        elif age > 50:
            bmi_suggestions.append("随年龄增长，要注意补充钙质和必需营养素")
        
        return {
            'daily_calories': round(daily_calories),
            'protein': round(protein),
            'fat': round(fat),
            'carbs': round(carbs),
            'fiber': round(fiber),
            'water': round(water),
            'bmi': round(bmi, 1),
            'suggestions': bmi_suggestions
        }
    except Exception as e:
        print(f"计算营养需求时出错: {str(e)}")

        return {
            'daily_calories': 2000,
            'protein': 60,
            'fat': 55,
            'carbs': 250,
            'fiber': 25,
            'water': 2000,
            'bmi': 0,
            'suggestions': ["无法计算精确的营养需求，请检查输入数据是否正确"]
        }

# 使用LLM解析课表
def parse_schedule(schedule_text):
    try:
        messages = [
            {"role": "system", "content": """你是一个专业的课表解析助手。请将用户提供的课表信息解析为结构化的JSON格式。
解析要求：
1. 每天的课程必须包含：课程名称(name)、开始时间(start_time)、结束时间(end_time)和地点(location)
2. 返回格式必须是一个字典，key为星期几（如"星期一"），value为该天的课程列表
3. 时间格式统一为24小时制，如"8:00"、"14:30"
4. 如果某一天没有课，对应的value应该是空列表[]
5. 必须包含周一到周日的所有日期，即使没有课程

示例输出格式：
{
    "星期一": [
        {"name": "高等数学", "start_time": "8:00", "end_time": "9:50", "location": "理教101"},
        {"name": "大学英语", "start_time": "10:10", "end_time": "12:00", "location": "人文学院305"}
    ],
    "星期二": [],
    ...其他日期
}"""},
            {"role": "user", "content": f"请将以下课表解析为JSON格式：\n\n{schedule_text}"}
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        
        parsed_schedule = response.choices[0].message.content
        
        # 尝试提取JSON部分
        try:
            # 查找JSON数据的开始和结束位置
            start_idx = parsed_schedule.find('{')
            end_idx = parsed_schedule.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = parsed_schedule[start_idx:end_idx]
                schedule_data = json.loads(json_str)
            else:
                schedule_data = json.loads(parsed_schedule)
            
            # 确保包含所有星期
            days = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            for day in days:
                if day not in schedule_data:
                    schedule_data[day] = []
                elif not isinstance(schedule_data[day], list):
                    schedule_data[day] = []
                else:
                    # 验证每个课程信息的完整性
                    for i, class_info in enumerate(schedule_data[day]):
                        if not isinstance(class_info, dict):
                            schedule_data[day][i] = {
                                "name": "未知课程",
                                "start_time": "00:00",
                                "end_time": "00:00",
                                "location": "未知地点"
                            }
                        else:
                            # 确保所有必要字段都存在
                            required_fields = {
                                "name": "未知课程",
                                "start_time": "00:00",
                                "end_time": "00:00",
                                "location": "未知地点"
                            }
                            for field, default in required_fields.items():
                                if field not in class_info or not class_info[field]:
                                    class_info[field] = default
            
            return schedule_data
            
        except json.JSONDecodeError:
            # 如果解析失败，尝试再次让模型修正
            correction_messages = messages + [
                {"role": "assistant", "content": parsed_schedule},
                {"role": "user", "content": """请修正上述回答，只输出标准的JSON格式数据，不要有任何额外的解释文字。
确保输出格式如下：
{
    "星期一": [
        {"name": "课程名称", "start_time": "08:00", "end_time": "09:50", "location": "地点"},
        ...
    ],
    "星期二": [],
    ...其他日期
}"""}
            ]
            
            correction_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=correction_messages,
                stream=False
            )
            
            corrected_result = correction_response.choices[0].message.content
            # 再次尝试提取JSON
            start_idx = corrected_result.find('{')
            end_idx = corrected_result.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = corrected_result[start_idx:end_idx]
                return json.loads(json_str)
            else:
                return json.loads(corrected_result)
            
    except Exception as e:
        print(f"课表解析错误: {str(e)}")
        # 返回一个空的课表结构
        return {
            "星期一": [], "星期二": [], "星期三": [], "星期四": [], 
            "星期五": [], "星期六": [], "星期日": [],
            "error": "课表解析失败，请检查格式并重试"
        }

# 生成饮食计划
def generate_meal_plan(user_info, schedule, nutrition_needs):
    try:
        canteen_data = load_canteen_data()
        knowledge_graph = load_knowledge_graph()
        
        # 基于课表位置，推荐附近食堂
        # 提取出关键信息，传给LLM
        canteens_summary = []
        for canteen in canteen_data.get('canteens', []):
            canteen_info = {
                "id": canteen.get("id"),
                "name": canteen.get("name"),
                "location": canteen.get("location"),
                "features": canteen.get("features"),
                "dish_count": len(canteen.get("dishes", []))
            }
            canteens_summary.append(canteen_info)
        
        # 提取部分健康知识
        health_knowledge = []
        for node in knowledge_graph.get('nodes', [])[:10]:  # 只取部分示例
            if node.get('type') == "食材":
                health_knowledge.append({
                    "name": node.get("name"),
                    "type": node.get("type"),
                    "subtype": node.get("subtype"),
                    "attributes": node.get("attributes")
                })
        
        # 提取用户的饮食限制和偏好
        dietary_restrictions = user_info.get('dietary_restrictions', '')
        preferences = user_info.get('preferences', '')
        
        # 分析课表，提取每天的课程安排和位置
        schedule_analysis = {}
        days_of_week = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        for day in days_of_week:
            if day in schedule:
                day_schedule = schedule[day]
                classes = []
                
                # 提取当天的课程时间和地点
                for class_info in day_schedule:
                    if isinstance(class_info, dict) and 'start_time' in class_info and 'location' in class_info:
                        classes.append({
                            'start_time': class_info.get('start_time'),
                            'end_time': class_info.get('end_time'),
                            'location': class_info.get('location')
                        })
                
                # 分析早餐、午餐、晚餐的最佳时间和地点
                breakfast_time = "7:30"
                lunch_time = "12:00"
                dinner_time = "18:00"
                
                breakfast_location = "宿舍附近"
                lunch_location = "上午最后一节课的教学楼附近"
                dinner_location = "下午最后一节课的教学楼附近"
                
                # 根据课表调整就餐时间和地点
                morning_classes = [c for c in classes if c.get('start_time', '').split(':')[0] < '12']
                afternoon_classes = [c for c in classes if '12' <= c.get('start_time', '').split(':')[0] < '18']
                evening_classes = [c for c in classes if c.get('start_time', '').split(':')[0] >= '18']
                
                # 调整早餐时间：如果早上有课，提前吃早餐
                if morning_classes:
                    first_class = min(morning_classes, key=lambda x: x.get('start_time', '23:59'))
                    first_class_hour = int(first_class.get('start_time', '8:00').split(':')[0])
                    if first_class_hour <= 9:
                        breakfast_time = f"{first_class_hour - 1}:00"
                        breakfast_location = first_class.get('location', '宿舍附近')
                
                # 调整午餐时间：根据上午和下午的课程安排
                if morning_classes and afternoon_classes:
                    last_morning = max(morning_classes, key=lambda x: x.get('end_time', '00:00'))
                    first_afternoon = min(afternoon_classes, key=lambda x: x.get('start_time', '23:59'))
                    
                    last_morning_end = last_morning.get('end_time', '12:00')
                    first_afternoon_start = first_afternoon.get('start_time', '14:00')
                    
                    # 计算午餐时间窗口
                    lunch_hour = int(last_morning_end.split(':')[0])
                    lunch_minute = int(last_morning_end.split(':')[1])
                    if lunch_minute >= 30:
                        lunch_hour += 1
                        lunch_minute = 0
                    
                    lunch_time = f"{lunch_hour}:{lunch_minute:02d}"
                    lunch_location = last_morning.get('location', '教学楼附近')
                
                # 调整晚餐时间：根据下午的课程安排
                if afternoon_classes:
                    last_afternoon = max(afternoon_classes, key=lambda x: x.get('end_time', '00:00'))
                    last_afternoon_end = last_afternoon.get('end_time', '17:30')
                    
                    dinner_hour = int(last_afternoon_end.split(':')[0])
                    dinner_minute = int(last_afternoon_end.split(':')[1])
                    if dinner_minute >= 30:
                        dinner_hour += 1
                        dinner_minute = 0
                    
                    dinner_time = f"{dinner_hour}:{dinner_minute:02d}"
                    dinner_location = last_afternoon.get('location', '教学楼附近')
                
                schedule_analysis[day] = {
                    'classes': classes,
                    'meals': {
                        'breakfast': {'time': breakfast_time, 'location': breakfast_location},
                        'lunch': {'time': lunch_time, 'location': lunch_location},
                        'dinner': {'time': dinner_time, 'location': dinner_location}
                    }
                }
            else:
                # 周末或无课日的默认安排
                schedule_analysis[day] = {
                    'classes': [],
                    'meals': {
                        'breakfast': {'time': '8:30', 'location': '宿舍附近'},
                        'lunch': {'time': '12:30', 'location': '宿舍附近'},
                        'dinner': {'time': '18:30', 'location': '宿舍附近'}
                    }
                }
        
        messages = [
            {"role": "system", "content": "你是北京大学的专业营养师和饮食规划师，你将基于学生的个人信息、课表和营养需求，为其制定个性化的饮食计划。你需要考虑学生的时间安排、所在位置附近的食堂以及健康营养均衡。每天的饮食计划必须各不相同，要有多样性，并且严格遵守用户的饮食限制和偏好。"},
            {"role": "user", "content": f"""
请为以下北京大学学生制定一周的饮食计划：

个人信息:
{json.dumps(user_info, ensure_ascii=False, indent=2)}

每日营养需求:
{json.dumps(nutrition_needs, ensure_ascii=False, indent=2)}

课表分析:
{json.dumps(schedule_analysis, ensure_ascii=False, indent=2)}

原始课表安排:
{json.dumps(schedule, ensure_ascii=False, indent=2)}

北大食堂信息:
{json.dumps(canteens_summary, ensure_ascii=False, indent=2)}

健康饮食知识:
{json.dumps(health_knowledge, ensure_ascii=False, indent=2)}

用户饮食限制: {dietary_restrictions}
用户饮食偏好: {preferences}

请制定一周（周一至周日）的详细饮食计划，包括：
1. 三餐和零食的具体食物建议（请使用实际食堂中有的菜品）
2. 每餐应在哪个食堂就餐（考虑学生当时的位置和时间）
3. 每天的总热量和营养素摄入估计（蛋白质、脂肪、碳水、膳食纤维）
4. 针对学生健康目标的特别建议
5. 每天的饮食计划必须各不相同，确保饮食多样性
6. 严格遵守用户的饮食限制，例如不能推荐用户明确表示不吃的食物
7. 根据课表安排合理安排就餐时间和地点，特别是考虑课程之间的间隙和位置

结果必须是JSON格式，包含以下结构：
{{
  "weekly_plan": {{
    "星期一": {{
      "早餐": {{"食堂": "", "食物": [], "时间": "", "营养素": {{"热量": 0, "蛋白质": 0, "脂肪": 0, "碳水": 0, "膳食纤维": 0}}}},
      "午餐": {{"食堂": "", "食物": [], "时间": "", "营养素": {{"热量": 0, "蛋白质": 0, "脂肪": 0, "碳水": 0, "膳食纤维": 0}}}},
      "晚餐": {{"食堂": "", "食物": [], "时间": "", "营养素": {{"热量": 0, "蛋白质": 0, "脂肪": 0, "碳水": 0, "膳食纤维": 0}}}},
      "零食": {{"建议": [], "营养素": {{"热量": 0, "蛋白质": 0, "脂肪": 0, "碳水": 0, "膳食纤维": 0}}}},
      "每日总计": {{"热量": 0, "蛋白质": 0, "脂肪": 0, "碳水": 0, "膳食纤维": 0}},
      "饮水量": 0,
      "建议": ""
    }},
    "其他日期...": {{}}
  }},
  "总体建议": "",
  "每周营养总结": {{}}
}}
"""
            }
        ]
        
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
            temperature=0.7,  
            max_tokens=4000  
        )
        
        meal_plan = response.choices[0].message.content
        
        # 提取JSON部分
        try:
            # 尝试定位并提取JSON
            start_idx = meal_plan.find('{')
            end_idx = meal_plan.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = meal_plan[start_idx:end_idx]
                parsed_data = json.loads(json_str)
            else:
                parsed_data = json.loads(meal_plan)
                
            # 验证数据结构
            valid_data = {"weekly_plan": {}, "总体建议": "", "每周营养总结": {}}
            
            # 确保weekly_plan存在且是字典
            if "weekly_plan" in parsed_data and isinstance(parsed_data["weekly_plan"], dict):
                weekly_plan = parsed_data["weekly_plan"]
                for day, meals in weekly_plan.items():
                    if isinstance(meals, dict):
                        required_meals = ['早餐', '午餐', '晚餐', '零食']
                        for meal in required_meals:
                            if meal not in meals or not isinstance(meals[meal], dict):
                                if meal == '零食':
                                    meals[meal] = {
                                        "建议": ["水果", "坚果", "酸奶"],
                                        "营养素": {"热量": 200, "蛋白质": 5, "脂肪": 10, "碳水": 20, "膳食纤维": 3}
                                    }
                                else:
                                    nearby_canteen = "学一食堂"  # 默认食堂
                                    default_time = {"早餐": "7:30", "午餐": "12:00", "晚餐": "18:00"}
                                    
                                    default_foods = {
                                        "早餐": ["豆浆", "鸡蛋", "馒头", "八宝粥"],
                                        "午餐": ["米饭", "清炒青菜", "红烧豆腐", "紫菜汤"],
                                        "晚餐": ["米饭", "炒青菜", "蒸鱼", "紫菜蛋花汤"]
                                    }
                                    
                                    meals[meal] = {
                                        "食堂": nearby_canteen,
                                        "食物": default_foods[meal],
                                        "时间": default_time[meal],
                                        "营养素": {"热量": 500, "蛋白质": 25, "脂肪": 15, "碳水": 65, "膳食纤维": 8}
                                    }
                        
                        for meal in list(meals.keys()):
                            if meal not in required_meals:
                                del meals[meal]
                
                valid_data["weekly_plan"] = weekly_plan
            

            if "总体建议" in parsed_data and isinstance(parsed_data["总体建议"], str):
                valid_data["总体建议"] = parsed_data["总体建议"]
            else:
                valid_data["总体建议"] = "保持均衡饮食，定时定量，多运动少熬夜。建议每天摄入足够的蛋白质、优质碳水和必要的脂肪，保证营养均衡。"
            
            # 确保每周营养总结存在且是字典
            if "每周营养总结" in parsed_data and isinstance(parsed_data["每周营养总结"], dict):
                valid_data["每周营养总结"] = parsed_data["每周营养总结"]
            else:

                valid_data["每周营养总结"] = {
                    "平均每日热量": str(nutrition_needs.get('daily_calories', 2000)),
                    "平均每日蛋白质": str(nutrition_needs.get('protein', 75)),
                    "平均每日脂肪": str(nutrition_needs.get('fat', 60)),
                    "平均每日碳水": str(nutrition_needs.get('carbs', 250)),
                    "平均每日膳食纤维": str(nutrition_needs.get('fiber', 25)),
                    "评估": "饮食计划符合您的健康目标和营养需求，建议遵循执行。"
                }
                
            return valid_data
        except json.JSONDecodeError:
            # 如果解析失败，尝试再次让模型修正
            correction_messages = messages + [
                {"role": "assistant", "content": meal_plan},
                {"role": "user", "content": "请修正上述回答，只输出标准的JSON格式数据，不要有任何额外的解释文字。确保每天的饮食计划各不相同，并且严格遵守用户的饮食限制。"}
            ]
            
            correction_response = client.chat.completions.create(
                model="deepseek-chat",
                messages=correction_messages,
                stream=False
            )
            
            corrected_result = correction_response.choices[0].message.content
            # 再次尝试提取JSON
            start_idx = corrected_result.find('{')
            end_idx = corrected_result.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = corrected_result[start_idx:end_idx]
                parsed_data = json.loads(json_str)
            else:
                parsed_data = json.loads(corrected_result)
                
            # 验证数据结构
            valid_data = {"weekly_plan": {}, "总体建议": "", "每周营养总结": {}}
            if "weekly_plan" in parsed_data and isinstance(parsed_data["weekly_plan"], dict):
                valid_data["weekly_plan"] = parsed_data["weekly_plan"]
            if "总体建议" in parsed_data and isinstance(parsed_data["总体建议"], str):
                valid_data["总体建议"] = parsed_data["总体建议"]
            if "每周营养总结" in parsed_data and isinstance(parsed_data["每周营养总结"], dict):
                valid_data["每周营养总结"] = parsed_data["每周营养总结"]
                
            return valid_data
    except Exception as e:
        print(f"生成饮食计划错误: {str(e)}")
        return {"error": "生成饮食计划失败", "weekly_plan": {}, "总体建议": "", "每周营养总结": {}}

# 获取今日健康贴士
def get_daily_health_tip():
    try:
        knowledge_graph = load_knowledge_graph()
        qa_dataset = load_qa_dataset()
        
        # 从知识图谱和问答数据集中随机选择健康贴士
        tips = []
        
        # 从知识图谱中提取食材相关的健康信息
        for node in knowledge_graph.get('nodes', []):
            if isinstance(node, dict) and node.get('type') == '食材' and 'attributes' in node:
                tip = {
                    'title': f"今日食材推荐：{node.get('name', '健康食材')}",
                    'content': f"特点：{', '.join(node.get('attributes', {}).keys() or ['营养丰富'])}"
                }
                tips.append(tip)
        
        # 从问答数据集中提取营养知识
        for qa in qa_dataset:
            if isinstance(qa, dict) and qa.get('topic') == '营养知识':
                tip = {
                    'title': qa.get('question', '健康饮食小贴士'),
                    'content': qa.get('answer', '保持均衡饮食，适量运动，充足睡眠是健康的基础。')
                }
                tips.append(tip)
        
        # 随机选择一条贴士
        if tips:
            import random
            return random.choice(tips)
        
        return {
            'title': '每日健康小贴士',
            'content': '保持均衡饮食，适量运动，充足睡眠是健康的基础。'
        }
    except Exception as e:
        print(f"获取健康贴士失败: {str(e)}")
        return {
            'title': '每日健康小贴士',
            'content': '保持均衡饮食，适量运动，充足睡眠是健康的基础。'
        }

# 路由
@app.route('/')
def index():
    # 加载食堂数据
    canteens = load_canteen_data().get('canteens', [])
    
    # 获取今日健康贴士
    health_tip = get_daily_health_tip()
    
    # 获取当前年份
    current_year = datetime.now().year
    
    return render_template('index.html', 
                         canteens=canteens,
                         health_tip=health_tip,
                         current_year=current_year)

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if request.method == 'POST':
        try:
            # 获取表单数据
            user_info = {
                'name': request.form.get('name'),
                'age': request.form.get('age'),
                'gender': request.form.get('gender'),
                'height': request.form.get('height'),
                'weight': request.form.get('weight'),
                'activity_level': request.form.get('activity_level'),
                'health_goal': request.form.get('health_goal'),
                'dietary_restrictions': ','.join(request.form.getlist('dietary_restrictions')),
                'preferences': request.form.get('preferences', '')
            }
            
            # 验证必填字段
            required_fields = ['name', 'age', 'gender', 'height', 'weight', 'activity_level', 'health_goal']
            for field in required_fields:
                if not user_info[field]:
                    return jsonify({
                        'success': False,
                        'message': f'请填写{field}字段'
                    })
            
            # 验证年龄、身高和体重的有效性
            try:
                age = int(user_info['age'])
                height = float(user_info['height'])
                weight = float(user_info['weight'])
                
                if age < 16 or age > 100:
                    return jsonify({
                        'success': False,
                        'message': '年龄必须在16到100岁之间'
                    })
                    
                if height < 140 or height > 220:
                    return jsonify({
                        'success': False,
                        'message': '身高必须在140到220厘米之间'
                    })
                    
                if weight < 30 or weight > 150:
                    return jsonify({
                        'success': False,
                        'message': '体重必须在30到150公斤之间'
                    })
            except ValueError:
                return jsonify({
                    'success': False,
                    'message': '请输入有效的数字'
                })
            session['user_info'] = user_info
            
            # 计算营养需求
            nutrition_needs = calculate_nutrition_needs(user_info)
            session['nutrition_needs'] = nutrition_needs
            
            # 返回成功消息
            return jsonify({
                'success': True,
                'message': '个人信息保存成功！'
            })
            
        except Exception as e:
            print(f"保存个人信息时出错: {str(e)}")
            return jsonify({
                'success': False,
                'message': '服务器处理请求时出错，请稍后再试'
            })
    
    # GET 请求处理
    user_info = session.get('user_info')
    edit_mode = 'user_info' in session
    current_year = datetime.now().year
    
    return render_template('profile.html', user_info=user_info, edit_mode=edit_mode, current_year=current_year)

@app.route('/update_profile', methods=['POST'])
def update_profile():
    if 'user_info' in session:
        # 更新用户信息
        user_info = session['user_info']
        
        # 更新各个字段
        user_info['name'] = request.form.get('name')
        user_info['age'] = request.form.get('age')
        user_info['gender'] = request.form.get('gender')
        user_info['height'] = request.form.get('height')
        user_info['weight'] = request.form.get('weight')
        user_info['activity_level'] = request.form.get('activity_level')
        user_info['health_goal'] = request.form.get('health_goal')
        user_info['dietary_restrictions'] = request.form.get('dietary_restrictions')
        user_info['preferences'] = request.form.get('preferences')
        
        # 更新会话中的用户信息
        session['user_info'] = user_info
        
        # 如果有营养需求，重新计算
        if 'nutrition_needs' in session:
            nutrition_needs = calculate_nutrition_needs(user_info)
            session['nutrition_needs'] = nutrition_needs
        
        return redirect(url_for('profile'))
    
    return redirect(url_for('profile'))

@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    session.pop('user_info', None)
    session.pop('nutrition_needs', None)
    session.pop('schedule', None)
    session.pop('meal_plan', None)
    
    return redirect(url_for('index'))

@app.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if request.method == 'POST':
        schedule_text = request.form.get('schedule_text')
        parsed_schedule = parse_schedule(schedule_text)
        
        if 'error' in parsed_schedule:
            return render_template('schedule.html', error=parsed_schedule['error'], current_year=datetime.now().year)
        
        session['schedule'] = parsed_schedule
        return render_template('confirm.html', 
                             user_info=session.get('user_info', {}),
                             schedule=parsed_schedule,
                             nutrition_needs=session.get('nutrition_needs', {}),
                             current_year=datetime.now().year)
    
    return render_template('schedule.html', current_year=datetime.now().year)

@app.route('/confirm', methods=['GET'])
def confirm():
    if 'user_info' not in session or 'schedule' not in session:
        return redirect(url_for('profile'))
    
    return render_template('confirm.html', 
                         user_info=session.get('user_info', {}),
                         schedule=session.get('schedule', {}),
                         nutrition_needs=session.get('nutrition_needs', {}),
                         current_year=datetime.now().year)

@app.route('/generate_recommendation', methods=['POST'])
def generate_recommendation():
    if 'user_info' in session and 'schedule' in session and 'nutrition_needs' in session:
        user_info = session.get('user_info')
        schedule = session.get('schedule')
        nutrition_needs = session.get('nutrition_needs')
        
        # 调用模型生成饮食计划
        meal_plan = generate_meal_plan(user_info, schedule, nutrition_needs)
        session['meal_plan'] = meal_plan
        
        # 重定向到结果页面
        return redirect(url_for('result'))
    else:

        if 'user_info' not in session:
            return redirect(url_for('profile'))
        elif 'schedule' not in session:
            return redirect(url_for('schedule'))
        else:
            return redirect(url_for('index'))

@app.route('/result')
def result():
    # 检查是否已有饮食计划，如果没有则重定向到确认页面
    if 'meal_plan' not in session:
        return redirect(url_for('confirm'))
    
    user_info = session.get('user_info', {})
    schedule = session.get('schedule', {})
    nutrition_needs = session.get('nutrition_needs', {})
    meal_plan = session.get('meal_plan', {})
    
    # 验证 meal_plan 结构
    if not isinstance(meal_plan, dict):
        meal_plan = {"error": "饮食计划格式错误，请重新生成"}
    
    # 验证 weekly_plan 是否存在且是字典
    if 'weekly_plan' not in meal_plan or not isinstance(meal_plan['weekly_plan'], dict):
        meal_plan['weekly_plan'] = {}
        
    # 确保每周营养总结和总体建议存在
    if '每周营养总结' not in meal_plan or not isinstance(meal_plan['每周营养总结'], dict):
        meal_plan['每周营养总结'] = {}
    
    if '总体建议' not in meal_plan or not isinstance(meal_plan['总体建议'], str):
        meal_plan['总体建议'] = "保持均衡饮食，定时定量，多运动少熬夜"
    
    # 获取当前年份
    current_year = datetime.now().year
    
    return render_template('result.html', user_info=user_info, schedule=schedule, 
                         nutrition_needs=nutrition_needs, meal_plan=meal_plan,
                         current_year=current_year)

@app.route('/record_meal', methods=['POST'])
def record_meal():
    try:
        meal_data = request.json
        user_info = session.get('user_info', {})
        user_name = user_info.get('name', 'anonymous')
        
        meal_records_file = f"meal_records_{user_name}.json"
        if os.path.exists(meal_records_file):
            with open(meal_records_file, 'r', encoding='utf-8') as f:
                try:
                    records = json.load(f)
                except:
                    records = {"records": []}
        else:
            records = {"records": []}
        
        # 添加新记录
        meal_data['timestamp'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records["records"].append(meal_data)
        
        # 保存更新后的记录
        with open(meal_records_file, 'w', encoding='utf-8') as f:
            json.dump(records, f, ensure_ascii=False, indent=2)
        
        return jsonify({"status": "success", "message": "饮食记录已保存"})
    except Exception as e:
        print(f"记录饮食失败: {str(e)}")
        return jsonify({"status": "error", "message": f"记录失败: {str(e)}"})

@app.route('/analyze_trends')
def analyze_trends():
    user_info = session.get('user_info', {})
    user_name = user_info.get('name', 'anonymous')
    meal_records_file = f"meal_records_{user_name}.json"
    
    if not os.path.exists(meal_records_file):
        return jsonify({"status": "error", "message": "没有找到饮食记录"})
    
    with open(meal_records_file, 'r', encoding='utf-8') as f:
        records = json.load(f)
    
    grouped_records = {}
    for record in records.get('records', []):
        date = record.get('timestamp', '').split(' ')[0]  # 提取日期部分
        if date not in grouped_records:
            grouped_records[date] = []
        grouped_records[date].append(record)
    
    daily_calories = {}
    for date, day_records in grouped_records.items():
        total_calories = sum(record.get('actual_calories', 0) for record in day_records)
        daily_calories[date] = total_calories
    
    # 使用LLM分析趋势并给出建议
    messages = [
        {"role": "system", "content": "你是一位专业的营养师和饮食分析师，负责分析用户的饮食记录和趋势。请基于用户的实际饮食数据，提供专业的分析和改进建议。"},
        {"role": "user", "content": f"""
请分析以下用户的饮食记录数据：

用户信息:
{json.dumps(user_info, ensure_ascii=False, indent=2)}

营养需求:
{json.dumps(session.get('nutrition_needs', {}), ensure_ascii=False, indent=2)}

每日热量摄入:
{json.dumps(daily_calories, ensure_ascii=False, indent=2)}

详细饮食记录:
{json.dumps(records, ensure_ascii=False, indent=2)}

请提供以下分析:
1. 用户饮食习惯的总体评价
2. 饮食与健康目标的符合程度
3. 需要改进的方面
4. 具体的改进建议

结果应包含饮食趋势分析和个性化建议。
"""
        }
    ]
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        
        analysis_result = response.choices[0].message.content
        return jsonify({"status": "success", "analysis": analysis_result, "daily_calories": daily_calories})
    except Exception as e:
        return jsonify({"status": "error", "message": f"分析失败: {str(e)}"})

@app.route('/adjust_plan', methods=['POST'])
def adjust_plan():
    feedback = request.json.get('feedback', '')
    current_plan = session.get('meal_plan', {})
    user_info = session.get('user_info', {})
    nutrition_needs = session.get('nutrition_needs', {})
    
    # 提取用户的饮食限制和偏好
    dietary_restrictions = user_info.get('dietary_restrictions', '')
    preferences = user_info.get('preferences', '')
    
    messages = [
        {"role": "system", "content": "你是北京大学的专业营养师和饮食规划师，负责根据用户的反馈调整饮食计划。你必须严格遵守用户的饮食限制和偏好，特别是用户明确表示不喜欢或不能吃的食物。"},
        {"role": "user", "content": f"""
请根据用户的反馈调整现有的饮食计划：

用户信息:
{json.dumps(user_info, ensure_ascii=False, indent=2)}

营养需求:
{json.dumps(nutrition_needs, ensure_ascii=False, indent=2)}

用户饮食限制: {dietary_restrictions}
用户饮食偏好: {preferences}

当前饮食计划:
{json.dumps(current_plan, ensure_ascii=False, indent=2)}

用户反馈:
{feedback}

请基于用户反馈调整饮食计划，特别注意：
1. 如果用户指出某些食物不吃或不喜欢，必须将这些食物从计划中完全移除
2. 如果用户要求增加某类食物，应在保证营养均衡的前提下增加
3. 如果用户提出特定的健康目标，应调整计划以支持这些目标
4. 保持饮食的多样性和营养均衡
5. 确保每餐的营养素计算准确，并更新每日总计

请保持JSON格式不变，确保所有营养素数值都经过重新计算。
"""
        }
    ]
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False,
            temperature=0.5  
        )
        
        adjusted_plan = response.choices[0].message.content
        
        # 提取JSON部分
        try:
            # 尝试定位并提取JSON
            start_idx = adjusted_plan.find('{')
            end_idx = adjusted_plan.rfind('}') + 1
            if start_idx != -1 and end_idx != -1:
                json_str = adjusted_plan[start_idx:end_idx]
                adjusted_plan_json = json.loads(json_str)
            else:
                adjusted_plan_json = json.loads(adjusted_plan)
                
            if "不吃" in feedback or "不喜欢" in feedback or "过敏" in feedback:
                disliked_foods = []

                for food in ["鸡蛋", "牛奶", "豆腐", "猪肉", "牛肉", "鸡肉", "海鲜", "辣"]:  # 常见食物
                    if f"不吃{food}" in feedback or f"不喜欢{food}" in feedback or f"{food}过敏" in feedback:
                        disliked_foods.append(food)
                contains_disliked = False
                for day, meals in adjusted_plan_json.get("weekly_plan", {}).items():
                    for meal_type in ["早餐", "午餐", "晚餐", "零食"]:
                        if meal_type in meals:
                            foods = " ".join(meals[meal_type].get("食物", []))
                            for food in disliked_foods:
                                if food in foods:
                                    contains_disliked = True
                                    break
                if contains_disliked:
                    correction_messages = messages + [
                        {"role": "assistant", "content": adjusted_plan},
                        {"role": "user", "content": f"你的调整后的计划仍然包含用户明确表示不喜欢的食物：{', '.join(disliked_foods)}。请再次调整计划，完全移除这些食物，并用其他适合的食物替代，同时保持营养均衡。"}
                    ]
                    
                    correction_response = client.chat.completions.create(
                        model="deepseek-chat",
                        messages=correction_messages,
                        stream=False
                    )
                    
                    corrected_result = correction_response.choices[0].message.content
                    # 再次尝试提取JSON
                    start_idx = corrected_result.find('{')
                    end_idx = corrected_result.rfind('}') + 1
                    if start_idx != -1 and end_idx != -1:
                        json_str = corrected_result[start_idx:end_idx]
                        adjusted_plan_json = json.loads(json_str)
                    else:
                        adjusted_plan_json = json.loads(corrected_result)
            
            # 更新会话中的饮食计划
            session['meal_plan'] = adjusted_plan_json
            
            return jsonify({"status": "success", "adjusted_plan": adjusted_plan_json})
        except json.JSONDecodeError:
            return jsonify({"status": "error", "message": "调整计划格式错误"})
    except Exception as e:
        return jsonify({"status": "error", "message": f"调整失败: {str(e)}"})

@app.route('/ai_assistant', methods=['POST'])
def ai_assistant():
    user_query = request.json.get('query', '')
    
    # 加载食堂和知识图谱数据
    canteens_data = load_canteen_data()
    knowledge_graph = load_knowledge_graph()
    qa_dataset = load_qa_dataset()
    
    # 提取食堂信息
    canteens_info = []
    for canteen in canteens_data.get('canteens', []):
        canteen_info = {
            "id": canteen.get("id"),
            "name": canteen.get("name"),
            "location": canteen.get("location"),
            "features": canteen.get("features", []),
            "popular_dishes": [dish.get("name") for dish in canteen.get("dishes", [])[:5] if "name" in dish],
            "meal_times": {
                "breakfast": "6:30-9:00",
                "lunch": "10:30-13:30",
                "dinner": "17:00-19:30"
            }
        }
        canteens_info.append(canteen_info)
    
    messages = [
        {"role": "system", "content": """你是北京大学的AI营养师，熟悉校园内所有食堂的信息和营养健康知识。
请基于提供的知识图谱、问答数据集和食堂信息，为用户提供准确、专业的健康饮食建议。
回答要点：
1. 如果用户询问特定食堂或就餐地点，请提供详细的食堂信息和推荐
2. 如果用户询问营养或健康问题，请基于知识图谱和问答数据集提供专业建议
3. 如果用户询问特定时间（如早餐、午餐）的推荐，请考虑时间因素给出合适的食堂和食物推荐
4. 回答应简洁明了，直接解决用户的问题
5. 态度友好专业，语气自然"""},
        {"role": "user", "content": f"""基于以下知识库回答用户问题：

北大食堂信息：
{json.dumps(canteens_info, ensure_ascii=False, indent=2)}

知识图谱数据：
{json.dumps(knowledge_graph.get('nodes', [])[:15], ensure_ascii=False, indent=2)}

问答数据集：
{json.dumps(qa_dataset[:10], ensure_ascii=False, indent=2)}

用户问题：{user_query}"""}
    ]
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=False
        )
        
        answer = response.choices[0].message.content
        return jsonify({"status": "success", "answer": answer})
    except Exception as e:
        print(f"AI助手回答失败: {str(e)}")
        return jsonify({"status": "error", "message": f"AI助手回答失败: {str(e)}"})

@app.route('/get_health_tip')
def get_health_tip():
    tip = get_daily_health_tip()
    return jsonify(tip)

@app.route('/ai_chat')
def ai_chat():
    # 获取当前年份
    current_year = datetime.now().year
    return render_template('ai_chat.html', current_year=current_year)

@app.route('/health_tracking')
def health_tracking():
    # 检查用户是否已登录
    if 'user_info' not in session:
        return redirect(url_for('profile'))
    
    # 获取当前年份
    current_year = datetime.now().year
    return render_template('health_tracking.html', current_year=current_year)

@app.route('/health_tips')
def health_tips():
    # 加载知识图谱和问答数据集
    knowledge_graph = load_knowledge_graph()
    qa_dataset = load_qa_dataset()
    
    # 提取健康贴士
    tips = []
    
    # 从知识图谱中提取食材相关的健康信息
    for node in knowledge_graph.get('nodes', [])[:20]:  # 限制数量
        if isinstance(node, dict) and node.get('type') == '食材' and 'attributes' in node:
            tip = {
                'title': f"食材推荐：{node['name']}",
                'content': f"特点：{', '.join(node['attributes'].keys())}",
                'type': 'food'
            }
            tips.append(tip)
    
    # 从问答数据集中提取营养知识
    for qa in qa_dataset[:20]:  
        try:
            if isinstance(qa, dict) and qa.get('topic') == '营养知识':
                tip = {
                    'title': qa.get('question', ''),
                    'content': qa.get('answer', ''),
                    'type': 'qa'
                }
                tips.append(tip)
        except (AttributeError, TypeError):

            continue
    if not tips:
        tips = [
            {
                'title': '健康饮食小贴士',
                'content': '每天应摄入足够的蔬菜和水果，保证膳食纤维的摄入。',
                'type': 'default'
            },
            {
                'title': '饮水建议',
                'content': '每天应饮用1.5-2升水，保持身体水分平衡。',
                'type': 'default'
            },
            {
                'title': '营养均衡',
                'content': '一日三餐应包含碳水化合物、蛋白质和脂肪，保证营养均衡。',
                'type': 'default'
            }
        ]
    
    # 获取当前年份
    current_year = datetime.now().year
    
    # 设置当前页码，默认为1
    current_page = request.args.get('page', 1, type=int)
    
    return render_template('health_tips.html', tips=tips, current_page=current_page, current_year=current_year)

@app.route('/canteen_detail/<canteen_id>')
def canteen_detail(canteen_id):
    # 加载食堂数据
    canteens = load_canteen_data().get('canteens', [])
    
    # 查找指定ID的食堂
    canteen = None
    for c in canteens:
        if str(c.get('id')) == str(canteen_id):
            canteen = c
            break
    
    if not canteen:
        return redirect(url_for('index'))
    
    # 获取当前年份
    current_year = datetime.now().year
    
    return render_template('canteen_detail.html', canteen=canteen, current_year=current_year)

@app.route('/regenerate_meal_plan', methods=['POST'])
def regenerate_meal_plan():
    # 检查是否有必要的信息
    if 'user_info' in session and 'schedule' in session and 'nutrition_needs' in session:
        user_info = session.get('user_info')
        schedule = session.get('schedule')
        nutrition_needs = session.get('nutrition_needs')
        
        # 重新生成饮食计划
        meal_plan = generate_meal_plan(user_info, schedule, nutrition_needs)
        session['meal_plan'] = meal_plan
        
        # 重定向到结果页面
        return redirect(url_for('result'))
    else:
        # 如果缺少必要信息，重定向到适当的页面
        if 'user_info' not in session:
            return redirect(url_for('profile'))
        elif 'schedule' not in session:
            return redirect(url_for('schedule'))
        else:
            return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True) 