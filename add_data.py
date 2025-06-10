import sqlite3
import json
from datetime import datetime

def add_single_item_v2(db_path: str = "clothing_db.sqlite", item_data: dict = None):
    """添加单个服装项目到数据库（v2版本，包含温度和天气字段）"""
    if item_data is None:
        # 示例数据
        item_data = {
            'name': '传播',
            'description': 'T-shirt',
            'style': '复古，经典',
            'color': '黑色',
            'season': '春夏',
            'temp_min': 15,
            'temp_max': 35,
            'weather_conditions': ['晴天', '多云', '阴天'], 
            'image_url': 'https://example.com/medical-protection.jpg',
            'tags': ['繁体','方正','传播'],
            'college':  '新闻与传播学院'
    
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
    
def add_multiple_items_v2(db_path: str = "clothing_db.sqlite", items_list: list = None):
    """批量添加多个服装项目（v2版本）"""
    if items_list is None:
        # 示例批量数据
        items_list = [
            {
                'name': '文学院复古毛衣',
                'description': '文艺复古风格，温暖舒适',
                'style': '复古',
                'color': '米色',
                'season': '秋冬',
                'temp_min': 5,
                'temp_max': 15,
                'weather_conditions': ['晴天', '多云', '阴天'],
                'image_url': 'https://example.com/literature-sweater.jpg',
                'tags': ['文艺', '复古', '毛衣'],
                'college': '文学院'
            },
            {
                'name': '理学院实验外套',
                'description': '实验室专用，防化学试剂',
                'style': '功能性',
                'color': '蓝色',
                'season': '四季',
                'temp_min': 15,
                'temp_max': 25,
                'weather_conditions': ['晴天', '多云', '阴天', '小雨'],
                'image_url': 'https://example.com/science-lab-coat.jpg',
                'tags': ['实验', '防护', '功能性'],
                'college': '理学院'
            },
            {
                'name': '音乐学院演出服',
                'description': '正式演出专用，优雅大方',
                'style': '正式',
                'color': '黑色',
                'season': '四季',
                'temp_min': 18,
                'temp_max': 24,
                'weather_conditions': ['晴天', '多云', '阴天'],
                'image_url': 'https://example.com/music-performance.jpg',
                'tags': ['演出', '正式', '优雅'],
                'college': '音乐学院'
            },
            {
                'name': '建筑学院工地背心',
                'description': '工地实习专用，安全醒目',
                'style': '功能性',
                'color': '荧光黄',
                'season': '春夏秋',
                'temp_min': 10,
                'temp_max': 35,
                'weather_conditions': ['晴天', '多云', '阴天'],
                'image_url': 'https://example.com/architecture-vest.jpg',
                'tags': ['安全', '工地', '醒目'],
                'college': '建筑学院'
            }
        ]
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        added_count = 0
        for item in items_list:
            tags_json = json.dumps(item['tags'], ensure_ascii=False)
            weather_json = json.dumps(item['weather_conditions'], ensure_ascii=False)
            
            cursor.execute('''
            INSERT INTO clothing_items 
            (name, description, style, color, season, temp_min, temp_max,
             weather_conditions, image_url, tags, college)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['name'],
                item['description'],
                item['style'],
                item['color'],
                item['season'],
                item['temp_min'],
                item['temp_max'],
                weather_json,
                item['image_url'],
                tags_json,
                item['college']
            ))
            added_count += 1
        
        conn.commit()
        print(f"成功批量添加 {added_count} 个项目")
        
        conn.close()
        return added_count
        
    except sqlite3.Error as e:
        print(f"批量添加数据失败: {e}")
        return 0

def add_from_csv_v2(db_path: str = "clothing_db.sqlite", csv_file: str = "clothing_data_v2.csv"):
    """从CSV文件导入数据（v2版本）"""
    import csv
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        with open(csv_file, 'r', encoding='utf-8') as file:
            csv_reader = csv.DictReader(file)
            added_count = 0
            
            for row in csv_reader:
                # 处理tags字段（假设CSV中是逗号分隔的字符串）
                if 'tags' in row and row['tags']:
                    tags_list = [tag.strip() for tag in row['tags'].split(',')]
                    tags_json = json.dumps(tags_list, ensure_ascii=False)
                else:
                    tags_json = json.dumps([])
                
                # 处理weather_conditions字段
                if 'weather_conditions' in row and row['weather_conditions']:
                    weather_list = [weather.strip() for weather in row['weather_conditions'].split(',')]
                    weather_json = json.dumps(weather_list, ensure_ascii=False)
                else:
                    weather_json = json.dumps([])
                
                # 处理温度字段
                temp_min = int(row.get('temp_min', 0)) if row.get('temp_min') else 0
                temp_max = int(row.get('temp_max', 30)) if row.get('temp_max') else 30
                
                cursor.execute('''
                INSERT INTO clothing_items 
                (name, description, style, color, season, temp_min, temp_max,
                 weather_conditions, image_url, tags, college)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    row.get('name', ''),
                    row.get('description', ''),
                    row.get('style', ''),
                    row.get('color', ''),
                    row.get('season', ''),
                    temp_min,
                    temp_max,
                    weather_json,
                    row.get('image_url', ''),
                    tags_json,
                    row.get('college', '')
                ))
                added_count += 1
        
        conn.commit()
        print(f"从CSV文件成功导入 {added_count} 个项目")
        
        conn.close()
        return added_count
        
    except FileNotFoundError:
        print(f"CSV文件 {csv_file} 不存在")
        return 0
    except Exception as e:
        print(f"从CSV导入数据失败: {e}")
        return 0
    

if __name__  == "__main__":
    add_single_item_v2()
    