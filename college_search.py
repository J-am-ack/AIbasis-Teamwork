import sqlite3
import json
from typing import List, Dict, Optional
import random




class ClothingDBQuery:
    def __init__(self, db_path: str = "clothing_db.sqlite"):
        self.db_path = db_path
        
        # # 检查表结构（调试用）
        # columns = db_path.check_table_structure()
        # print("表的列:", columns)
        
    def get_connection(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def search_clothing_by_college_and_keywords(self, college: str = None, keywords: List[str] = None, limit: int = 5) -> List[Dict]:
        """根据院系和关键词搜索院衫"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 构建搜索条件
            conditions = []
            params = []
            
            # 院系条件
            if college:
                conditions.append("college = ?")
                params.append(college)
            
            # 关键词条件
            if keywords:
                keyword_conditions = []
                for keyword in keywords:
                    keyword_conditions.append(
                        "(name LIKE ? OR description LIKE ? OR style LIKE ? OR color LIKE ?)"
                    )
                    params.extend([f"%{keyword}%"] * 4)
                
                if keyword_conditions:
                    conditions.append(f"({' OR '.join(keyword_conditions)})")
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            query = f"""
            SELECT id, name, description, style, color, season, temp_min,temp_max,weather_conditions, image_url, tags, college
            FROM clothing_items 
            WHERE {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # 转换为字典格式
            clothing_items = []
            for row in results:
                item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else [],
                'college':row[11] if len(row) > 11 else None
                }
                clothing_items.append(item)
                
            return clothing_items
            
        except sqlite3.Error as e:
            print(f"数据库查询错误: {e}")
            return []
        finally:
            conn.close()
    
    def get_clothing_by_college(self, college: str, limit: int = 3) -> List[Dict]:
        """根据院系获取院衫"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT id, name, description, style, color, season,temp_min,temp_max,weather_conditions, image_url, tags, college
            FROM clothing_items 
            WHERE college = ?
            ORDER BY RANDOM()
            LIMIT ?
            """
            
            cursor.execute(query, [college, limit])
            results = cursor.fetchall()
            
            clothing_items = []
            for row in results:
                item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else [],
                'college':row[11] if len(row) > 11 else None
                }
                clothing_items.append(item)
                
            return clothing_items
            
        except sqlite3.Error as e:
            print(f"数据库查询错误: {e}")
            return []
        finally:
            conn.close()
    
    def get_random_clothing_by_college(self, college: str, count: int = 1) -> List[Dict]:
        """随机获取指定院系的院衫"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT id, name, description, style, color, season, temp_min,temp_max,weather_conditions, image_url, tags, college
            FROM clothing_items 
            WHERE college = ?
            ORDER BY RANDOM()
            LIMIT ?
            """
            
            cursor.execute(query, [college, count])
            results = cursor.fetchall()
            
            clothing_items = []
            for row in results:
                item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else [],
                'college':row[11] if len(row) > 11 else None
                }
                clothing_items.append(item)
                
            return clothing_items
            
        except sqlite3.Error as e:
            print(f"数据库查询错误: {e}")
            return []
        finally:
            conn.close()
    
    def search_clothing_by_keywords(self, keywords: List[str], limit: int = 5) -> List[Dict]:
        """根据关键词搜索院衫（不限院系）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 构建搜索条件
            keyword_conditions = []
            params = []
            
            for keyword in keywords:
                keyword_conditions.append(
                    "(name LIKE ? OR description LIKE ? OR style LIKE ? OR color LIKE ?)"
                )
                params.extend([f"%{keyword}%"] * 4)
            
            where_clause = " OR ".join(keyword_conditions) if keyword_conditions else "1=1"
            
            query = f"""
            SELECT id, name, description, style, color, season, temp_min,temp_max,weather_conditions,image_url, tags, college
            FROM clothing_items 
            WHERE {where_clause}
            ORDER BY RANDOM()
            LIMIT ?
            """
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # 转换为字典格式
            clothing_items = []
            for row in results:
                item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else [],
                'college':row[11] if len(row) > 11 else None
                }
                clothing_items.append(item)
                
            return clothing_items
            
        except sqlite3.Error as e:
            print(f"数据库查询错误: {e}")
            return []
        finally:
            conn.close()
    
    def get_random_clothing(self, count: int = 1) -> List[Dict]:
        """随机获取院衫"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            query = """
            SELECT id, name, description, style, color, season,temp_min,temp_max,weather_conditions, image_url, tags, college
            FROM clothing_items 
            ORDER BY RANDOM()
            LIMIT ?
            """
            
            cursor.execute(query, [count])
            results = cursor.fetchall()
            
            clothing_items = []
            for row in results:
                item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else [],
                'college':row[11] if len(row) > 11 else None
                }
                clothing_items.append(item)
                
            return clothing_items
            
        except sqlite3.Error as e:
            print(f"数据库查询错误: {e}")
            return []
        finally:
            conn.close()
    
    def check_table_structure(self):
        """检查表结构 - 调试用"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA table_info(clothing_items);")
            columns = cursor.fetchall()
            print("表结构:")
            for col in columns:
                print(f"  {col[1]} ({col[2]})")
            return [col[1] for col in columns]
        except sqlite3.Error as e:
            print(f"检查表结构错误: {e}")
            return []
        finally:
            conn.close()
    
    def add_college_column_if_not_exists(self):
        """如果college列不存在，则添加它"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # 检查列是否存在
            cursor.execute("PRAGMA table_info(clothing_items);")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'college' not in columns:
                cursor.execute("ALTER TABLE clothing_items ADD COLUMN college TEXT;")
                conn.commit()
                print("已添加college列到表中")
            else:
                print("college列已存在")
                
        except sqlite3.Error as e:
            print(f"添加列错误: {e}")
        finally:
            conn.close()

class ClothingMatcher:
    def __init__(self, db_query: ClothingDBQuery):
        self.db_query = db_query
    
    def extract_keywords_from_qwen_response(self, qwen_response: str) -> List[str]:
        """从Qwen回复中提取关键词"""
        # 简单的关键词提取，可以根据需要使用更复杂的NLP方法
        keywords = []
        
        # 定义关键词映射
        keyword_mapping = {
            '休闲': ['休闲', 'casual'],
            '正式': ['正式', 'formal', '商务'],
            '运动': ['运动', 'sport', '健身'],
            '夏季': ['夏天', '夏季', '热', '短袖'],
            '冬季': ['冬天', '冬季', '冷', '长袖', '厚'],
            '春秋': ['春天', '秋天', '薄'],
            '黑色': ['黑', '黑色'],
            '白色': ['白', '白色'],
            '蓝色': ['蓝', '蓝色'],
            '红色': ['红', '红色'],
            'T恤': ['T恤', 't恤', 'tshirt'],
            '衬衫': ['衬衫', '衬衣'],
            '卫衣': ['卫衣', '连帽衫'],
            '外套': ['外套', '夹克']
        }
        
        response_lower = qwen_response.lower()
        for category, terms in keyword_mapping.items():
            for term in terms:
                if term.lower() in response_lower:
                    keywords.append(category)
                    break
        
        return list(set(keywords))  # 去重
    
    def select_matching_clothing(self, qwen_response: str, user_query: str = "") -> Optional[Dict]:
        """根据Qwen回复和用户查询选择匹配的院衫"""
        # 从Qwen回复中提取关键词
        qwen_keywords = self.extract_keywords_from_qwen_response(qwen_response)
        
        # 从用户查询中提取关键词
        user_keywords = self.extract_keywords_from_qwen_response(user_query)
        
        # 合并关键词
        all_keywords = list(set(qwen_keywords + user_keywords))
        
        if not all_keywords:
            # 如果没有关键词，随机选择一个
            clothing_items = self.db_query.get_random_clothing(1)
            return clothing_items[0] if clothing_items else None
        
        # 根据关键词搜索
        clothing_items = self.db_query.search_clothing_by_keywords(all_keywords, limit=3)
        
        if not clothing_items:
            # 如果没找到匹配的，尝试按类别搜索
            for keyword in all_keywords:
                items = self.db_query.get_clothing_by_category(keyword, limit=1)
                if items:
                    return items[0]
            
            # 最后随机选择
            random_items = self.db_query.get_random_clothing(1)
            return random_items[0] if random_items else None
        
        # 返回最匹配的一个
        return clothing_items[0]
    

    
    def select_matching_clothing_by_college(self, ai_response: str, user_query: str = "", college: str = None) -> Optional[Dict]:
        """根据AI回复、用户查询和院系信息选择匹配的院衫"""
        # 从AI回复中提取关键词
        ai_keywords = self.extract_keywords_from_response(ai_response)
        
        # 从用户查询中提取关键词
        user_keywords = self.extract_keywords_from_response(user_query)
        
        # 合并关键词
        all_keywords = list(set(ai_keywords + user_keywords))
        
        # 根据院系和关键词搜索
        clothing_items = self.db_query.search_clothing_by_college_and_keywords(
            college=college,
            keywords=all_keywords,
            limit=3
        )
        
        if not clothing_items:
            # 如果没找到匹配的，尝试只按院系搜索
            if college:
                clothing_items = self.db_query.get_clothing_by_college(college, limit=1)
            
            # # 如果还是没有，按关键词搜索（不限院系）
            # if not clothing_items and all_keywords:
            #     clothing_items = self.db_query.search_clothing_by_keywords(all_keywords, limit=1)
            
            # 最后随机选择该院系的
            # if not clothing_items:
            #     if college:
            #         clothing_items = self.db_query.get_random_clothing_by_college(college, 1)
            #     else:
            #         clothing_items = self.db_query.get_random_clothing(1)
        
        return clothing_items[0] if clothing_items else None
    
    def extract_keywords_from_response(self, response: str) -> List[str]:
        """从回复中提取关键词"""
        keywords = []
        
        # 定义关键词映射
        keyword_mapping = {
            '休闲': ['休闲', 'casual', '轻松', '随意'],
            '正式': ['正式', 'formal', '商务', '职业', '工作'],
            '运动': ['运动', 'sport', '健身', '跑步', '锻炼'],
            '约会': ['约会', '浪漫', '甜美', '温柔'],
            '聚会': ['聚会', '派对', 'party', '社交'],
            '夏季': ['夏天', '夏季', '热', '短袖', '清爽'],
            '冬季': ['冬天', '冬季', '冷', '长袖', '厚', '保暖'],
            '春秋': ['春天', '秋天', '薄', '过渡'],
            '黑色': ['黑', '黑色'],
            '白色': ['白', '白色'],
            '蓝色': ['蓝', '蓝色'],
            '红色': ['红', '红色'],
            'T恤': ['T恤', 't恤', 'tshirt'],
            '衬衫': ['衬衫', '衬衣'],
            '卫衣': ['卫衣', '连帽衫', 'hoodie'],
            '外套': ['外套', '夹克', 'jacket']
        }
        
        response_lower = response.lower()
        for category, terms in keyword_mapping.items():
            for term in terms:
                if term.lower() in response_lower:
                    keywords.append(category)
                    break
        
        return list(set(keywords))  # 去重
    
    def format_clothing_recommendation(self, clothing_item: Dict) -> str:
        """格式化院衫推荐信息"""
        if not clothing_item:
            return "抱歉，暂时没有找到合适的院衫推荐。"
        
        recommendation = f"""
**{clothing_item['name']}**
- 所属学院：{clothing_item.get('college', '未知')}
- 风格：{clothing_item['style']}
- 颜色：{clothing_item['color']}
- 适合季节：{clothing_item['season']}
- 适宜温度：{clothing_item['temp_min']}°C - {clothing_item['temp_max']}°C
- 适宜天气：{clothing_item['weather_conditions']}


{clothing_item['description']}
"""
        
        if clothing_item.get('tags'):
            recommendation += f"\n🏷️ 标签：{', '.join(clothing_item['tags'])}"

            
        return recommendation
    
    
    
    def format_clothing_recommendation(self, clothing_item: Dict) -> str:
        """格式化院衫推荐信息"""
        if not clothing_item:
            return "抱歉，暂时没有找到合适的院衫推荐。"
        
        recommendation = f"""
🎯 **院衫推荐**

**{clothing_item['name']}**
- 风格：{clothing_item['style']}
- 颜色：{clothing_item['color']}
- 适合季节：{clothing_item['season']}
- 适宜温度：{clothing_item['temp_min']}°C - {clothing_item['temp_max']}°C
- 适宜天气：{clothing_item['weather_conditions']}

{clothing_item['description']}
"""
        
        if clothing_item.get('tags'):
            recommendation += f"\n标签：{', '.join(clothing_item['tags'])}"
        

            
        return recommendation
    
    def get_clothing_by_category(self, category: str, limit: int = 3) -> List[Dict]:
        """根据类别获取院衫"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT id, name, description, style, color, season, temp_min,temp_max,weather_conditions, image_url, tags
        FROM clothing_items 
        WHERE style LIKE ? OR tags LIKE ?
        ORDER BY RANDOM()
        LIMIT ?
        """
        
        cursor.execute(query, [f"%{category}%", f"%{category}%", limit])
        results = cursor.fetchall()
        conn.close()
        
        clothing_items = []
        for row in results:
            item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else []
            }
            clothing_items.append(item)
            
        return clothing_items
    
    def get_random_clothing(self, count: int = 1) -> List[Dict]:
        """随机获取院衫"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        query = """
        SELECT id, name, description, style, color, season, temp_min,temp_max,weather_conditions,image_url, tags
        FROM clothing_items 
        ORDER BY RANDOM()
        LIMIT ?
        """
        
        cursor.execute(query, [count])
        results = cursor.fetchall()
        conn.close()
        
        clothing_items = []
        for row in results:
            item = {
                'id': row[0],
                'name': row[1],
                'description': row[2],
                'style': row[3],
                'color': row[4],
                'season': row[5],
                'temp_min': row[6],
                'temp_max':row[7],
                'weather_conditions':row[8],
                'image_url': row[9],
                'tags': json.loads(row[10]) if row[10] else []
            }
            clothing_items.append(item)
            
        return clothing_items