import os
import base64
import hashlib
import json
import threading
import time
import logging
import matplotlib
from datetime import datetime
from io import BytesIO
import uuid
from retrying import retry
from dotenv import load_dotenv
from config.settings import config
from config.prompt_utils import prompt_loader
from typing import Dict, Any, List, Optional, ClassVar, Generator, Union
from pydantic import ConfigDict, BaseModel, Field
from modules.info_retrieval import APIManager
from knowledge_base.loader_RAG import KnowledgeLoader
import matplotlib.pyplot as plt
import numpy as np
import redis
from dashscope import Generation
from openai import OpenAI
from camel.agents import ChatAgent
from camel.configs import QwenConfig
from camel.messages import BaseMessage
from camel.models import ModelFactory
from camel.types import ModelPlatformType, RoleType
from time import perf_counter

load_dotenv(dotenv_path='.env.development')

# 配置matplotlib，防止中文乱码和负号
matplotlib.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
matplotlib.rcParams['axes.unicode_minus'] = False

# ---------- 数据模型定义 ----------
class MediaItem(BaseModel):
    type: str = Field(..., description="媒体类型: image|chart|map|diagram")
    content: str = Field(..., description="base64编码的PNG数据")
    description: str
    source: Optional[str] = None
    interactive: bool = False

class GenerationInput(BaseModel):
    session_id: str
    user_query: str
    intent: str
    entities: Dict[str, Any] = {}
    context: Dict[str, Any] = {}
    retrieved_data: Dict[str, Any] = {}
    api_result: Optional[Dict[str, Any]] = None
    media_assets: Dict[str, Any] = {}
    height: Optional[float] = None
    weight: Optional[float] = None
    goal: Optional[str] = None

class GenerationOutput(BaseModel):
    session_id: str
    answer: str
    intent: str
    entities: Dict[str, Any] = {}
    media: List[MediaItem] = []
    feedback_token: str
    sources: List[str] = []
    related_queries: List[str] = []
    timestamp: datetime = Field(default_factory=datetime.now)

class ResultGenerator:
    def __init__(self, config_loader=None, prompt_loader=None, logger=None, redis_client=None):
        self.logger = logger or logging.getLogger('ResultGenerator')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

        self.config = config_loader or config
        self.redis = redis_client or redis.Redis(
            connection_pool=config.redis_pool,
            db=config.REDIS_DB_MAPPING["generator"]
        )
        self.media_path = config.MEDIA_STORAGE_PATH
        os.makedirs(self.media_path, exist_ok=True)
        self.prompt_loader = prompt_loader or prompt_loader
        
        self.agents: Dict[str, ChatAgent] = {}
        self._init_llm_agents()

    def _init_llm_agents(self):
        """初始化所有LLM代理"""
        model_config = config.MODEL_CONFIGS["generation"]

        # 1. 设施查询代理
        facility_model = ModelFactory.create(
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            model_type=model_config["model_name"],
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=model_config.get("temperature", 0.0),
                max_tokens=model_config.get("max_tokens", 512),
                top_p=model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_facility = BaseMessage(
            role_name="Facility Query Assistant",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/facility_query.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "facility_query", "timestamp": datetime.now().isoformat()}
        )
        self.agents["facility_query"] = ChatAgent(
            system_message=system_message_facility,
            model=facility_model
        )

        # 2. 活动查询代理
        event_model_config = config.MODEL_CONFIGS["generation"]
        event_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=event_model_config.get("temperature", 0.0),
                max_tokens=event_model_config.get("max_tokens", 512),
                top_p=event_model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_event = BaseMessage(
            role_name="Event Query Assistant",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/event_query.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "event_query", "timestamp": datetime.now().isoformat()}
        )
        self.agents["event_query"] = ChatAgent(
            system_message=system_message_event,
            model=event_model
        )
        
        # 3. 课程查询代理
        course_model_config = config.MODEL_CONFIGS["generation"]
        course_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=course_model_config.get("temperature", 0.0),
                max_tokens=course_model_config.get("max_tokens", 512),
                top_p=course_model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_course = BaseMessage(
            role_name="Course Query Assistant",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/course_info.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "course_info", "timestamp": datetime.now().isoformat()}
        )
        self.agents["course_info"] = ChatAgent(
            system_message=system_message_course,
            model=course_model
        )

        # 4. 体质测试代理
        physical_test_model_config = config.MODEL_CONFIGS["generation"]
        physical_test_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=physical_test_model_config.get("temperature", 0.0),
                max_tokens=physical_test_model_config.get("max_tokens", 512),
                top_p=physical_test_model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_physical_test = BaseMessage(
            role_name="Physical Test Assistant",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/physical_test.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "physical_test", "timestamp": datetime.now().isoformat()}
        )
        self.agents["physical_test"] = ChatAgent(
            system_message=system_message_physical_test,
            model=physical_test_model
        )

        # 5. 投诉反馈代理 (用于处理反馈，如果需要单独的生成逻辑)
        feedback_model_config = config.MODEL_CONFIGS["generation"]
        feedback_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=feedback_model_config.get("temperature", 0.0),
                max_tokens=feedback_model_config.get("max_tokens", 512),
                top_p=feedback_model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_feedback = BaseMessage(
            role_name="Feedback Processor",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/feedback.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "feedback", "timestamp": datetime.now().isoformat()}
        )
        self.agents["feedback"] = ChatAgent(
            system_message=system_message_feedback,
            model=feedback_model
        )

        # 6. 运动建议代理
        health_model_config = config.MODEL_CONFIGS["generation"]
        health_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=health_model_config.get("temperature", 0.0),
                max_tokens=health_model_config.get("max_tokens", 512),
                top_p=health_model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_health = BaseMessage(
            role_name="Exercise Recommender",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/health_advice.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "health_advice", "timestamp": datetime.now().isoformat()}
        )
        self.agents["health_advice"] = ChatAgent(
            system_message=system_message_health,
            model=health_model
        )

        # 7. 85km课外锻炼代理
        exercise_model_config = config.MODEL_CONFIGS["generation"]
        exercise_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=exercise_model_config.get("temperature", 0.0),
                max_tokens=exercise_model_config.get("max_tokens", 512),
                top_p=exercise_model_config.get("top_p", 1.0),
                stream=True
            ).as_dict()
        )
        system_message_exercise = BaseMessage(
            role_name="Exercise Recommender",
            role_type=RoleType.ASSISTANT,
            content=self.prompt_loader.get_prompt("generation/extra_exercise.jinja2"),
            meta_dict={"module": "result_generator", "sub_agent": "extra_exercise", "timestamp": datetime.now().isoformat()}
        )
        self.agents["extra_exercise"] = ChatAgent(
            system_message=system_message_exercise,
            model=exercise_model
        )


    @retry(wait_fixed=2000, stop_max_attempt_number=3)
    def _call_llm(self, agent_name: str, messages: List[Dict[str, Any]]) -> str:
        """调用指定代理的LLM"""
        agent = self.agents.get(agent_name)
        if not agent:
            self.logger.error(f"未找到代理: {agent_name}")
            raise ValueError(f"未找到代理: {agent_name}")
        
        try:
            user_message_content = messages[0]["content"]
            response = agent.step(
                BaseMessage(
                    role_name="user",
                    role_type=RoleType.USER,
                    content=user_message_content,
                    meta_dict={
                        "module": "result_generator_call_llm", 
                        "agent": agent_name,
                        "timestamp": datetime.now().isoformat()
                    }
                )
            )
            return response.msg.content
        except Exception as e:
            self.logger.error(f"调用LLM失败 (Agent: {agent_name}): {e}")
            raise

    def generate_answer(self, input_data: GenerationInput) -> GenerationOutput:
        start_time = perf_counter()
        self.logger.info(f"Session {input_data.session_id}: 开始生成答案，意图: {input_data.intent}")

        answer_text = "抱歉，无法生成答案。"
        media_items: List[MediaItem] = []
        sources: List[str] = []
        related_queries: List[str] = []

        try:
            # 处理无法识别意图的情况
            if input_data.intent == "unrecognized_intent":
                self.logger.info(f"Session {input_data.session_id}: 意图为 'unrecognized_intent'，加载专用模板。")
                prompt_template_path = "generation/unrecognized_intent.jinja2"
                
                if not self.prompt_loader.template_exists(prompt_template_path):
                    self.logger.error(f"Session {input_data.session_id}: 模板 '{prompt_template_path}' 不存在。")
                    answer_text = "抱歉，系统无法理解您的问题，且相关提示信息缺失。"
                else:
                    answer_text = self.prompt_loader.get_prompt(prompt_template_path)
                
                feedback_token = self._create_feedback_record(input_data, {
                    "output": {
                        "session_id": input_data.session_id,
                        "answer": answer_text,
                        "intent": input_data.intent,
                        "entities": input_data.entities,
                        "media": [],
                        "feedback_token": "",
                        "sources": [],
                        "related_queries": []
                    }
                })
                
                return GenerationOutput(
                    session_id=input_data.session_id,
                    answer=answer_text,
                    intent=input_data.intent,
                    entities=input_data.entities,
                    media=[],
                    feedback_token=feedback_token,
                    sources=[],
                    related_queries=[]
                )

            # 正常意图处理
            agent_name = input_data.intent
            if agent_name not in self.agents:
                self.logger.error(f"Session {input_data.session_id}: 未找到意图 '{agent_name}' 对应的LLM Agent。")
                feedback_token = self._create_feedback_record(input_data, {"error": f"未找到意图 {agent_name} 的Agent"})
                return GenerationOutput(
                    session_id=input_data.session_id,
                    answer="系统内部错误：无法处理此意图。",
                    intent=input_data.intent,
                    entities=input_data.entities,
                    media=[],
                    feedback_token=feedback_token,
                    sources=[],
                    related_queries=[]
                )

            prompt_template_path = f"generation/{agent_name}.jinja2"
            if not self.prompt_loader.template_exists(prompt_template_path):
                self.logger.error(f"Session {input_data.session_id}: 意图 '{agent_name}' 对应的提示词模板 '{prompt_template_path}' 不存在。")
                feedback_token = self._create_feedback_record(input_data, {"error": f"模板 {prompt_template_path} 不存在"})
                return GenerationOutput(
                    session_id=input_data.session_id,
                    answer="抱歉，系统配置不完整，无法为您提供此意图的答案。",
                    intent=input_data.intent,
                    entities=input_data.entities,
                    media=[],
                    feedback_token=feedback_token,
                    sources=[],
                    related_queries=[]
                )

            # 准备Prompt数据
            prompt_data = {
                "user_query": input_data.user_query,
                "retrieved_data": input_data.retrieved_data,
                "api_result": input_data.api_result,
                "entities": input_data.entities,
                "media_assets": input_data.media_assets,
                "height": input_data.height,
                "weight": input_data.weight,
                "goal": input_data.goal
            }
            prompt = self.prompt_loader.get_prompt(prompt_template_path, **prompt_data)
            
            # 调用LLM
            llm_response_content = self._call_llm(agent_name, [{"role": "user", "content": prompt}])
            self.logger.info(f"Session {input_data.session_id}: LLM响应内容已获取。")

            # 解析LLM响应
            try:
                parsed_llm_response = json.loads(llm_response_content)
                answer_text = parsed_llm_response.get("answer", llm_response_content)
                media_items = [MediaItem(**item) for item in parsed_llm_response.get("media", [])]
                sources = parsed_llm_response.get("sources", [])
                related_queries = parsed_llm_response.get("related_queries", [])

                # 处理检索结果中的媒体s
                if isinstance(input_data.retrieved_data, dict):
                    # 从检索数据中提取媒体（兼容RetrievalResult结构）
                    retrieved_media = input_data.retrieved_data.get("data", {}).get("media_assets", [])
                    for asset in retrieved_media:
                        if asset.get("type") == "image" and asset.get("content"):
                            media_items.append(MediaItem(
                                type="image",
                                content=asset["content"],
                                description=asset.get("description", "相关图片"),
                                source=asset.get("metadata", {}).get("source", "知识库")
                            ))

            except json.JSONDecodeError:
                self.logger.warning(f"Session {input_data.session_id}: LLM响应不是有效的JSON，将内容作为纯文本处理。")
                answer_text = llm_response_content
            except Exception as e:
                self.logger.error(f"Session {input_data.session_id}: 解析LLM响应中的媒体资产失败: {e}")
                answer_text = llm_response_content

            feedback_token = self._create_feedback_record(input_data, {
                "output": {
                    "session_id": input_data.session_id,
                    "answer": answer_text,
                    "intent": input_data.intent,
                    "entities": input_data.entities,
                    "media": [item.model_dump() for item in media_items],
                    "feedback_token": "",
                    "sources": sources,
                    "related_queries": related_queries
                }
            })

            return GenerationOutput(
                session_id=input_data.session_id,
                answer=answer_text,
                intent=input_data.intent,
                entities=input_data.entities,
                media=media_items,
                feedback_token=feedback_token,
                sources=sources,
                related_queries=related_queries
            )

        except Exception as e:
            self.logger.error(f"Session {input_data.session_id}: 生成答案时发生意外错误: {e}")
            feedback_token = self._create_feedback_record(input_data, {"error": str(e)})
            return GenerationOutput(
                session_id=input_data.session_id,
                answer="非常抱歉，系统内部出现错误，请稍后再试。",
                intent=input_data.intent,
                entities=input_data.entities,
                feedback_token=feedback_token,
                sources=[]
            )

    def _create_feedback_record(self, input_data: GenerationInput, output_data: Union[Dict, GenerationOutput]) -> str:
        """创建反馈记录"""
        feedback_token = str(uuid.uuid4())
        
        input_dump = input_data.model_dump()
        output_dump = output_data.model_dump() if isinstance(output_data, BaseModel) else output_data

        record = {
            "input": input_dump,
            "output": output_dump,
            "timestamp": datetime.now(),
            "feedback_status": "pending"
        }
        
        self.redis.setex(
            f"feedback:{feedback_token}",
            config.RESULT_EXPIRE,
            json.dumps(record, ensure_ascii=False, default=self._json_serial)
        )
        return feedback_token

    def _json_serial(self, obj):
        """JSON序列化辅助方法"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


    def _update_feedback_record(self, feedback_token: str, updates: dict):
        """更新反馈记录"""
        if data_str := self.redis.get(f"feedback:{feedback_token}"):
            original = json.loads(data_str, object_hook=self._datetime_parser) # 引入 object_hook
            
            # 更新 original 字典
            original.update(updates)

            self.redis.setex(
                f"feedback:{feedback_token}",
                config.RESULT_EXPIRE,
                json.dumps(original, ensure_ascii=False, default=self._json_serial)
            )

    def _datetime_parser(self, dct):
        """用于 json.loads 的 object_hook，尝试将字符串解析为 datetime 对象"""
        for k, v in dct.items():
            if isinstance(v, str):
                try:
                    # 尝试解析 ISO 8601 格式的日期时间字符串
                    dct[k] = datetime.fromisoformat(v)
                except ValueError:
                    pass
        return dct

    def _fig_to_base64(self, fig: plt.Figure) -> str:
        """将matplotlib图形转换为base64编码的PNG图片"""
        buf = BytesIO()
        fig.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        plt.close(fig) # 关闭图形以释放内存
        return img_str

    def _create_pie_chart(self, labels: List[str], sizes: List[float], title: str) -> str:
        """创建并返回饼状图的base64编码字符串"""
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, textprops={'fontsize': 10})
        ax.axis('equal') # Equal aspect ratio ensures that pie is drawn as a circle.
        ax.set_title(title, fontsize=14)
        return self._fig_to_base64(fig)

    def _create_bar_chart(self, x_labels: List[str], y_values: List[float], title: str, xlabel: str, ylabel: str) -> str:
        """创建并返回柱状图的base64编码字符串"""
        fig, ax = plt.subplots(figsize=(8, 6))
        bars = ax.bar(x_labels, y_values, color='skyblue')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14)
        ax.tick_params(axis='x', rotation=45)
        fig.tight_layout() # Adjust layout to prevent labels from overlapping
        
        # Add value labels on top of bars
        for bar in bars:
            yval = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2, yval + 0.05, round(yval, 2), ha='center', va='bottom', fontsize=9)
        
        return self._fig_to_base64(fig)

    def _create_line_chart(self, x_values: List[Any], y_values: List[float], title: str, xlabel: str, ylabel: str) -> str:
        """创建并返回折线图的base64编码字符串"""
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.plot(x_values, y_values, marker='o', linestyle='-', color='green')
        ax.set_xlabel(xlabel, fontsize=12)
        ax.set_ylabel(ylabel, fontsize=12)
        ax.set_title(title, fontsize=14)
        ax.grid(True, linestyle='--', alpha=0.6)
        fig.tight_layout()
        return self._fig_to_base64(fig)
            
    def handle_revision(self, feedback_token: str, suggestions: str) -> GenerationOutput:
        """
        处理用户反馈并尝试重新生成答案。
        """
        self.logger.info(f"处理反馈：{feedback_token}，建议：{suggestions}")
        original_data = self._load_original_result(feedback_token)
        if not original_data:
            self.logger.error(f"未找到原始结果记录：{feedback_token}")
            raise ValueError("原始结果记录不存在或已过期。")

        # 标记为处理中
        if not self.redis.setnx(f"feedback:processing:{feedback_token}", "1"):
            self.logger.warning(f"反馈 {feedback_token} 正在处理中，避免重复操作。")
            return GenerationOutput(
                session_id=original_data["input"]["session_id"],
                answer="您的反馈正在处理中，请稍候。",
                intent=original_data["input"]["intent"],
                entities=original_data["input"]["entities"],
                feedback_token=feedback_token,
                sources=original_data["output"].get("sources", []),
                related_queries=original_data["output"].get("related_queries", [])
            )
        
        try:
            revised_output = self._generate_with_feedback(original_data, suggestions)
            self.logger.info(f"反馈 {feedback_token} 已成功处理并重新生成。")
            self._update_feedback_record(feedback_token, {"feedback_status": "processed", "revised_output": revised_output.model_dump()})
            return revised_output
        except Exception as e:
            self.logger.error(f"处理反馈 {feedback_token} 时发生错误: {e}")
            self._update_feedback_record(feedback_token, {"feedback_status": "failed", "error": str(e)})
            raise
        finally:
            # 清除处理中状态
            self.redis.delete(f"feedback:processing:{feedback_token}")

    def _generate_map_image(self, location: str) -> str:
        """生成地图图片(示例实现)"""
        with plt.style.context('seaborn-whitegrid'):
            fig = plt.figure(figsize=(8, 8), facecolor='white')
            plt.scatter([0], [0], c='red', s=100)
            plt.text(0, 0.1, location, ha='center')
            plt.title("导航地图")
            return self._fig_to_base64(fig)

    # ---------- 反馈相关 ----------
    def _load_original_result(self, feedback_token: str) -> Optional[dict]:
        """从Redis加载原始结果"""
        if data := self.redis.get(f"feedback:{feedback_token}"):
            return json.loads(data)
        return None

    def _update_feedback_record(self, feedback_token: str, updates: dict):
        """更新反馈记录"""
        if data_str := self.redis.get(f"feedback:{feedback_token}"):
            original = json.loads(data_str)
            
            # 更新 original 字典
            original.update(updates)

            # 再次使用 default 参数进行序列化，以防 updates 中包含了 datetime 对象
            self.redis.setex(
                f"feedback:{feedback_token}",
                config.RESULT_EXPIRE,
                json.dumps(original, ensure_ascii=False, default=self._json_serial)
            )

    def _generate_with_feedback(self, original_data: dict, suggestions: str) -> GenerationOutput:
        """基于反馈重新生成结果"""
        agent = self.agents.get(original_data["input"]["intent"])
        if not agent:
            agent = self.agents["general_query"] # 兜底到通用代理
        
        # 构造重新生成提示，包含原始输入和用户建议
        prompt = self.prompt_loader.get_prompt(
            "generation/feedback_re_generate.jinja2",
            original_query=original_data["input"]["original_query"], # 假设原始查询在input里
            original_answer=original_data["output"]["answer"],
            user_suggestions=suggestions,
            retrieved_data=original_data["input"]["retrieved_data"], # 重新传入检索数据
            entities=original_data["input"]["entities"]
        )
        
        llm_response_content = self._call_llm(agent.role_name.name, [{"role": "user", "content": prompt}]) # 代理名可能是 role_name.name
        
        try:
            response_json = json.loads(llm_response_content)
            answer_text = response_json.get("answer", "未能从LLM响应中获取答案。")
            sources = response_json.get("sources", [])
            related_queries = response_json.get("related_queries", [])
        except json.JSONDecodeError:
            self.logger.warning("LLM反馈重新生成响应不是有效的JSON，将内容作为纯文本处理。")
            answer_text = llm_response_content
            sources = original_data["output"].get("sources", [])
            related_queries = original_data["output"].get("related_queries", [])

        # 重新构建 GenerationOutput
        return GenerationOutput(
            session_id=original_data["input"]["session_id"],
            answer=answer_text,
            intent=original_data["input"]["intent"],
            entities=original_data["input"]["entities"],
            media=original_data["output"].get("media", []), # 保持原始媒体资产
            feedback_token=original_data["output"]["feedback_token"], # 使用原始token
            sources=sources,
            related_queries=related_queries
        )