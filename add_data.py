import sqlite3
import json
from datetime import datetime

def add_single_item_v2(db_path: str = "clothing_db.sqlite", item_data: dict = None):
    """添加单个服装项目到数据库（v2版本，包含温度和天气字段）"""
    if item_data is None:
        # 示例数据
        item_data = {
            'name': '医学院实验室防护服',
            'description': '医学实验专用，安全防护功能齐全',
            'style': '功能性',
            'color': '白色',
            'season': '四季',
            'temp_min': 18,
            'temp_max': 25,
            'weather_conditions': ['晴天', '多云', '阴天'],  # 列表格式
            'image_url': 'https://example.com/medical-protection.jpg',
            'tags': ['医学', '防护', '实验'],
            'college': '医学院'
        }
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 将tags和weather_conditions列表转换为JSON字符串
        tags_json = json.dumps(item_data['tags'], ensure_ascii=False)
        weather_json = json.dumps(item_data['weather_conditions'], ensure_ascii=False)
        
        cursor.execute('''
        INSERT INTO clothing_items 
        (name, description, style, color, season, temp_min, temp_max, 
         weather_conditions, image_url, tags, college)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            item_data['name'],
            item_data['description'],
            item_data['style'],
            item_data['color'],
            item_data['season'],
            item_data['temp_min'],
            item_data['temp_max'],
            weather_json,
            item_data['image_url'],
            tags_json,
            item_data['college']
        ))
        
        conn.commit()
        item_id = cursor.lastrowid
        print(f"成功添加新项目，ID: {item_id}")
        print(f"项目名称: {item_data['name']}")
        print(f"温度范围: {item_data['temp_min']}°C - {item_data['temp_max']}°C")
        print(f"适用天气: {', '.join(item_data['weather_conditions'])}")
        
        conn.close()
        return item_id
        
    except sqlite3.Error as e:
        print(f"添加数据失败: {e}")
        return None