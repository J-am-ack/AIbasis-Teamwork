
# 院系服装知识库扩展
import json
from typing import List, Dict, Any, Optional


from dataclasses import dataclass

@dataclass
class CollegeClothing:
    """院系服装数据类"""
    college: str  # 院系名称
    clothing_type: str  # 服装类型：shirt/hoodie/jacket
    name: str  # 服装名称
    description: str  # 详细描述
    colors: List[str]  # 可选颜色
    suitable_weather: List[str]  # 适合天气：['sunny', 'cloudy', 'cold', 'warm']
    temperature_range: tuple  # 适合温度范围
    style_tags: List[str]  # 风格标签
    formality: int  # 正式程度 1-5 (1最休闲，5最正式)

class CollegeClothingKnowledgeBase:
    """院系服装知识库"""
    
    def __init__(self):
        self.clothing_db = []
        self.init_knowledge_base()
    
    def init_knowledge_base(self):
        """初始化知识库数据"""
        # 示例数据，你可以根据实际情况扩充
        sample_data = [
            # 计算机学院
            CollegeClothing(
                college="计算机学院",
                clothing_type="hoodie",
                name="计算机学院经典连帽衫",
                description="深蓝色连帽卫衣，胸前印有学院LOGO",
                colors=["深蓝色", "黑色", "灰色"],
                suitable_weather=["cloudy", "cold"],
                temperature_range=(5, 20),
                style_tags=["休闲", "学院风", "舒适"],
                formality=2
            ),
            CollegeClothing(
                college="计算机学院",
                clothing_type="shirt",
                name="计算机学院POLO衫",
                description="白色POLO衫，袖口有学院标识",
                colors=["白色", "浅蓝色"],
                suitable_weather=["sunny", "warm"],
                temperature_range=(15, 30),
                style_tags=["商务休闲", "简约", "学院风"],
                formality=3
            ),
            
            # 经济管理学院
            CollegeClothing(
                college="经济管理学院",
                clothing_type="shirt",
                name="经管学院商务衬衫",
                description="浅蓝色商务衬衫，领口绣有学院徽标",
                colors=["浅蓝色", "白色", "浅粉色"],
                suitable_weather=["sunny", "cloudy"],
                temperature_range=(10, 25),
                style_tags=["商务", "正式", "学院风"],
                formality=4
            ),
            CollegeClothing(
                college="经济管理学院",
                clothing_type="jacket",
                name="经管学院西装外套",
                description="深灰色休闲西装外套，内侧有学院标识",
                colors=["深灰色", "藏青色"],
                suitable_weather=["cold", "cloudy"],
                temperature_range=(0, 18),
                style_tags=["商务", "正式", "学院风"],
                formality=5
            ),
            
            # 文学院
            CollegeClothing(
                college="文学院",
                clothing_type="shirt",
                name="文学院文艺衬衫",
                description="米白色棉麻衬衫，胸前有古典文字印花",
                colors=["米白色", "浅卡其色", "淡粉色"],
                suitable_weather=["sunny", "warm"],
                temperature_range=(15, 28),
                style_tags=["文艺", "清新", "学院风"],
                formality=3
            ),
            CollegeClothing(
                college="文学院",
                clothing_type="hoodie",
                name="文学院复古卫衣",
                description="奶茶色复古卫衣，印有经典文学语录",
                colors=["奶茶色", "浅灰色", "米白色"],
                suitable_weather=["cloudy", "cold"],
                temperature_range=(8, 22),
                style_tags=["文艺", "复古", "学院风"],
                formality=2
            ),
            
            # 工学院
            CollegeClothing(
                college="工学院",
                clothing_type="hoodie",
                name="工学院实用连帽衫",
                description="深灰色加厚连帽衫，多个实用口袋设计",
                colors=["深灰色", "黑色", "军绿色"],
                suitable_weather=["cold", "cloudy"],
                temperature_range=(0, 18),
                style_tags=["实用", "运动", "学院风"],
                formality=2
            ),
            CollegeClothing(
                college="工学院",
                clothing_type="jacket",
                name="工学院机能外套",
                description="黑色机能风外套，防风防水，胸前有工学院标识",
                colors=["黑色", "深蓝色", "军绿色"],
                suitable_weather=["cold", "cloudy"],
                temperature_range=(-5, 15),
                style_tags=["机能", "实用", "学院风"],
                formality=3
            ),
            
            CollegeClothing(
                college="信息科学技术学院",
                clothing_type="shirt",
                name="信科POLO衫",
                description="白色POLO衫，袖口有学院标识",
                colors=["白色", "浅蓝色"],
                suitable_weather=["sunny", "warm"],
                temperature_range=(15, 30),
                style_tags=["商务休闲", "简约", "学院风"],
                formality=3
                
                
            )
        ]
        
        self.clothing_db = sample_data
    
    def add_clothing_item(self, clothing: CollegeClothing):
        """添加服装项目到知识库"""
        self.clothing_db.append(clothing)