import json
from jinja2 import Environment, FileSystemLoader, StrictUndefined, TemplateNotFound
from pathlib import Path
from typing import Any, Dict
# 导入 config 对象
from config.settings import config # 导入你的配置单例

class PromptLoader:
    def __init__(self):
        template_path = Path(__file__).parent / "prompts"
        self.env = Environment(
            loader=FileSystemLoader(str(template_path)),
            autoescape=True,
            undefined=StrictUndefined  # 严格模式捕获未定义变量
        )
        # 添加必要过滤器
        self.env.filters['tojson'] = lambda x: json.dumps(x, ensure_ascii=False)

    def get_prompt(self, template_name: str, **kwargs) -> str:
        if not template_name.endswith('.jinja2'):
            template_name += '.jinja2'
        
        try:
            template = self.env.get_template(template_name)
            
            render_kwargs = {"config": config} 
            render_kwargs.update(kwargs) # 合并用户传入的 kwargs
            
            return template.render(**render_kwargs)
        
        except TemplateNotFound:
            raise ValueError(f"模板文件不存在: {template_name}")
        
        except Exception as e:
            raise ValueError(f"模板渲染失败: {str(e)}")
        
    def template_exists(self, template_name: str) -> bool:
        """检查模板是否存在"""
        if not template_name.endswith('.jinja2'):
            template_name += '.jinja2'
        try:
            self.env.get_template(template_name)
            return True
        except TemplateNotFound:
            return False
        
# 单例必须显式实例化
prompt_loader = PromptLoader()