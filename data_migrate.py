import os
import sqlite3
import json




def rebuild_database_fresh(db_path: str = "clothing_db.sqlite"):
    """完全重建数据库，删除旧数据"""
    
    # 方法1: 直接删除数据库文件（推荐）
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"已删除旧数据库文件: {db_path}")
    
    # 创建新的数据库连接
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("开始创建全新的数据库...")
        
        # 创建新的clothing_items表（v2版本）
        cursor.execute('''
        CREATE TABLE clothing_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            style TEXT,
            color TEXT,
            season TEXT,
            temp_min INTEGER,
            temp_max INTEGER,
            weather_conditions TEXT,
            image_url TEXT,
            tags TEXT,
            college TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        print("✅ 创建了新的clothing_items表")
        
        # 插入完整的示例数据
        sample_data = [
            {
                'name': '信息科学技术学院"线条小狮"T恤',
                'description': '简约设计，动画人物很可爱',
                'style': '休闲',
                'color': '白色',
                'season': '春夏',
                'temp_min': 20,
                'temp_max': 36,
                'weather_conditions': json.dumps(['晴天', '多云'], ensure_ascii=False),
                'image_url': 'https://example.com/cs-tshirt.jpg',
                'tags': json.dumps(['攻城狮', '线条', '纯棉'], ensure_ascii=False),
                'college': '信息科学技术学院'
            },
            {
                'name': '信科线条小狮"北京大风版"',
                'description': '紧跟时事（qwq),以及很可爱',
                'style': '随性',
                'color': '白色',
                'season': '春夏',
                'temp_min': 15,
                'temp_max': 25,
                'weather_conditions': json.dumps(['晴天', '多云', '阴天'], ensure_ascii=False),
                'image_url': 'https://example.com/business-polo.jpg',
                'tags': json.dumps(['动漫', '随性', 'T-shirt'], ensure_ascii=False),
                'college': '信息科学技术学院'
            },
            {
                'name': '香农纪念衫',
                'description': '纪念香农',
                'style': '正式',
                'color': '灰色/白色',
                'season': '春夏',
                'temp_min': 20,
                'temp_max': 35,
                'weather_conditions': json.dumps(['晴天', '多云', '阴天'], ensure_ascii=False),
                'image_url': 'https://example.com/sport-hoodie.jpg',
                'tags': json.dumps(['正式', '科技', '有型'], ensure_ascii=False),
                'college': '信息科学技术学院'
            },
            {
                'name': '俺狮',
                'description': '独特艺术设计，展现创意风格，二次元',
                'style': '时尚',
                'color': '彩色',
                'season': '春夏',
                'temp_min': 18,
                'temp_max': 38,
                'weather_conditions': json.dumps(['晴天', '多云'], ensure_ascii=False),
                'image_url': 'https://example.com/art-tshirt.jpg',
                'tags': json.dumps(['艺术', '创意', '二次元'], ensure_ascii=False),
                'college': '信息科学技术学院'
            },
            {
                'name': '夏日攻城狮',
                'description': '海滩上的攻城狮',
                'style': '简约',
                'color': '白色',
                'season': '春夏',
                'temp_min': 20,
                'temp_max': 35,
                'weather_conditions': json.dumps(['晴天', '多云'], ensure_ascii=False),
                'image_url': 'https://example.com/engineering-jacket.jpg',
                'tags': json.dumps(['简约','舒适','可爱'], ensure_ascii=False),
                'college': '信息科学技术学院'
            },
            
        ]
        
        # 插入所有示例数据
        for item in sample_data:
            cursor.execute('''
            INSERT INTO clothing_items 
            (name, description, style, color, season, temp_min, temp_max, 
             weather_conditions, image_url, tags, college)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['name'], item['description'], item['style'],
                item['color'], item['season'], item['temp_min'], item['temp_max'],
                item['weather_conditions'], item['image_url'], item['tags'], item['college']
            ))
        
        conn.commit()
        print(f"✅ 成功插入了{len(sample_data)}条完整的示例数据")
        print("✅ 数据库重建完成！")
        
    except sqlite3.Error as e:
        print(f"❌ 数据库重建失败: {e}")
        conn.rollback()
    finally:
        conn.close()



def verify_rebuild(db_path: str = "clothing_db.sqlite"):
    """验证重建后的数据库"""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表结构
        print("\n=== 数据库结构验证 ===")
        cursor.execute("PRAGMA table_info(clothing_items);")
        columns = cursor.fetchall()
        for col in columns:
            print(f"  {col[1]} ({col[2]})")
        
        # 检查数据数量
        cursor.execute("SELECT COUNT(*) FROM clothing_items;")
        count = cursor.fetchone()[0]
        print(f"\n总记录数: {count}")
        
        # 显示所有记录
        print("\n=== 所有数据记录 ===")
        cursor.execute("""
        SELECT id, name, college, temp_min, temp_max, weather_conditions 
        FROM clothing_items 
        ORDER BY id;
        """)
        items = cursor.fetchall()
        
        for item in items:
            weather_list = json.loads(item[5]) if item[5] else []
            weather_str = ', '.join(weather_list)
            print(f"ID {item[0]}: {item[1]}")
            print(f"  学院: {item[2]}")
            print(f"  温度: {item[3]}°C - {item[4]}°C")
            print(f"  天气: {weather_str}\n")
        
        conn.close()
        print("✅ 数据库验证完成！")
        return True
        
    except Exception as e:
        print(f"❌ 数据库验证失败: {e}")
        return False


if __name__ == "__main__":

    

    rebuild_database_fresh()

    
    # 验证结果
    verify_rebuild()