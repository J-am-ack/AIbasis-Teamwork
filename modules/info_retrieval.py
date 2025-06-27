import json
import re
import os
import requests
import redis
import random
import threading
from datetime import datetime
from config.settings import config
from config.prompt_utils import prompt_loader
from typing import Dict, List, Any, Optional, Union, Generator
from dotenv import load_dotenv
import hashlib
from firecrawl import FirecrawlApp
from camel.agents import ChatAgent, TaskPlannerAgent
from camel.models import ModelFactory
from camel.configs import QwenConfig
from camel.messages import BaseMessage
from camel.retrievers import AutoRetriever
from camel.types import StorageType, EmbeddingModelType, ModelPlatformType, RoleType
from enum import Enum
from infrastructure.shared_schemas import RetrievalRequest, RetrievalResult
import logging
from openai import OpenAI
from retrying import retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from knowledge_base.loader_RAG import KnowledgeLoader

load_dotenv(dotenv_path='.env.development')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("SportsRetrieval")

class SportsRetrievalAgent:
    def __init__(self, knowledge_loader: KnowledgeLoader):
        self.logger = logging.getLogger('SportsRetrievalAgent')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)

        self.knowledge_loader = knowledge_loader
        self.prompt_loader = prompt_loader
        self.api_manager = APIManager()

        self.retrieved_docs_cache = {}
        
        # 初始化LLM用于生成查询和整合结果
        self.llm_retrieval_agent = self._init_llm_retrieval_agent()
        self.executor = ThreadPoolExecutor(max_workers=config.RETRIEVAL_WORKERS)

        self.web_search_enabled = config.WEB_SEARCH_ENABLED
        if self.web_search_enabled and config.FIRECRAWL_API_KEY:
            self.firecrawl_app = FirecrawlApp(api_key=config.FIRECRAWL_API_KEY)
        else:
            self.firecrawl_app = None
            if self.web_search_enabled:
                self.logger.warning("Web search enabled but FIRECRAWL_API_KEY is not set. Web search will not function.")


    def _init_llm_retrieval_agent(self):
        model_config = config.MODEL_CONFIGS["retrieval"]
        
        # 按照您提供的正确格式创建模型
        qwen_model = ModelFactory.create(
            model_type=model_config["model_name"],
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL,
            api_key=config.DASHSCOPE_API_KEY,
            url=config.DASHSCOPE_BASE_URL,
            model_config_dict=QwenConfig(
                temperature=model_config.get("temperature", 0.0),
                max_tokens=model_config.get("max_tokens", 2048), # 检索模型通常需要更多token
                top_p=model_config.get("top_p", 1.0)
            ).as_dict()
        )
        
        # 创建系统消息
        system_message = BaseMessage(
            role_name="Retrieval Assistant", # 代理角色名称
            role_type=RoleType.ASSISTANT,    # 代理角色类型
            content=self.prompt_loader.get_prompt("retrieval/system.jinja2"), # 从模板加载内容
            meta_dict={
                "module": "info_retrieval",
                "timestamp": datetime.now().isoformat()
            }
        )

        # 创建 ChatAgent
        agent = ChatAgent(
            system_message=system_message,
            model=qwen_model
        )
        return agent
    
    @retry(wait_fixed=2000, stop_max_attempt_number=3)
    def _call_llm(self, messages: List[Dict[str, Any]]) -> str:
        try:
            # 这里的 messages 列表通常只有一个元素，例如 [{"role": "user", "content": "..."}]
            # 需要从这个字典中提取 'content'，并补充 'role_type' 和 'meta_dict'
            user_message_content = messages[0]["content"]

            # 确保提供 role_type 和 meta_dict
            response = self.llm_retrieval_agent.step(
                BaseMessage(
                    role_name="user",           # 已有
                    role_type=RoleType.USER,    # <--- 新增此行：明确指定为 USER 角色类型
                    content=user_message_content, # 已有
                    meta_dict={
                        "module": "info_retrieval_agent",
                        "timestamp": datetime.now().isoformat()
                    } # <--- 新增此行：提供一个空的或简单的 meta_dict
                )
            )
            return response.msg.content
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            raise

    def _generate_search_query(self, query: str) -> str:
        prompt = self.prompt_loader.get_prompt("retrieval/generate_search_query.jinja2", user_query=query)
        response = self._call_llm([{"role": "user", "content": prompt}])
        return response.strip()

    def _search_web(self, query: str, intent: str = None) -> Dict[str, Any]:
        """通用网络检索方法（兼容Firecrawl最新API）"""
        if not self.web_search_enabled or not self.firecrawl_app:
            return {
            "data": [], 
                "sources": [], 
                "status": "disabled",
                "metadata": {"query": query}
            }
    
        try:       
            # 调用Firecrawl API（最新规范）
            response = self.firecrawl_app.search(
                query,
                limit=config.HYPER_PARAMS["rag"]["top_k"], 
                options={
                    "timeout": config.RETRIEVAL_TIMEOUT * 1000,
                    "sort": "date" if intent == "physical_test" else None,
                    "domain": "edu.cn" if intent == "course_info" else None
                }  # 指定返回markdown格式
            )
        
            # 标准化结果
            processed = {
                "data": [],
                "sources": [],
                "status": "success",
                "metadata": {
                    "query": query,
                    "result_count": len(response.get("data", [])),
                    "api_used": "firecrawl"
                }
            }
        
            for item in response.get("data", []):
                content = item.get("markdown") or f"{item.get('title', '')}\n{item.get('content', '')}"
                processed["data"].append({
                    "content": content,
                    "metadata": {
                        "source": item.get("url"),
                        "score": item.get("score", 0),
                        **item.get("metadata", {})
                    }
                })
                processed["sources"].append(item.get("url"))
        
            return processed
        
        except Exception as e:
            self.logger.error(f"Firecrawl检索失败: {str(e)}")
            return {
                "data": [],
                "sources": [],
                "status": "error",
                "error": str(e),
                "metadata": {"query": query}
            }

    def _retrieve_from_knowledge_base(self, query: str) -> Dict[str, Any]:
        """返回结构严格保持：
        {
            "data": List[Dict],         # 文本结果
            "media_assets": Dict,       # 媒体资源
            "context": Dict             # 保留query上下文
        }"""
        self.logger.info(f"Retrieving from knowledge base for: {query}")
        try:
            raw_docs = self.knowledge_loader.retrieve(query)
        
            # 确保返回统一结构
            if isinstance(raw_docs, dict):  # 新格式
                return {
                    "data": raw_docs.get("data", []),
                    "media_assets": raw_docs.get("media_assets", {}),
                    "context": {"query": query}
                }
            else:  # 兼容旧格式
                text_results = []
                media_assets = {}
                for doc in raw_docs if raw_docs else []:
                    if isinstance(doc, dict):
                        text_results.append({
                            "content": doc.get("content", doc.get("text", "")),
                            "metadata": doc.get("metadata", {})
                        })
                        if doc.get("metadata", {}).get("type") == "image":
                            media_assets[f"image_{len(media_assets)}"] = {
                                "type": "image",
                                "content": doc.get("content", ""),
                                "metadata": doc.get("metadata", {})
                            }
            
                return {
                    "data": text_results,
                    "media_assets": media_assets,
                    "context": {"query": query}
                }
            
        except Exception as e:
            logger.error(f"知识库检索失败: {e}")
            return {
                "data": [],
                "media_assets": {},
                "context": {"query": query}
            }
            
    def _is_image_match(self, query: str, metadata: Dict) -> bool:
        """新增的匹配逻辑（不影响主函数结构）"""
        # 方法1：关键词匹配（优先使用JSON中的keywords字段）
        query_terms = set(query.lower().split())
        json_keywords = set(k.lower() for k in metadata.get("keywords", []))
        if query_terms & json_keywords:
            return True
    
        # 方法2：描述字段匹配（兼容旧数据）
        description = metadata.get("description", "").lower()
        if any(term in description for term in query_terms):
            return True
        
        return False

    def _call_external_api(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        if not config.EXTERNAL_APIS["enable_external_apis"]:
            self.logger.info("External APIs are disabled.")
            return {}

        api_result = self.api_manager.call_api(intent, entities)
        if api_result:
            self.logger.info(f"Called external API for intent '{intent}', result: {api_result}")
        else:
            self.logger.warning(f"No external API result for intent '{intent}' with entities {entities}.")
        return api_result

    def _integrate_results(self, user_query: str, kb_data: str, web_data: str, api_data: str) -> Dict[str, Any]:
        prompt = self.prompt_loader.get_prompt(
            "retrieval/integrate_results.jinja2",
            user_query=user_query,
            kb_data=kb_data,
            web_data=web_data,
            api_data=api_data
        )
        integrated_content = self._call_llm([{"role": "user", "content": prompt}])
        
        # 尝试从LLM响应中解析结构化数据（如果LLM被设计为生成JSON）
        try:
            parsed_data = json.loads(integrated_content)
            return parsed_data
        except json.JSONDecodeError:
            self.logger.warning("LLM did not return valid JSON for integration. Returning raw content.")
            return {"content": integrated_content}

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        # 1. 保持原有无法识别意图的快速返回
        if request.intent == "unrecognized_intent":
            self.logger.info(f"Session {request.session_id}: 意图为 'unrecognized_intent'，跳过所有检索。")
            return RetrievalResult(
                session_id=request.session_id,
                data={"status": "empty", "message": "未找到相关结果"},
                media_assets=[],
                sources=self._get_sources(request.intent),
                cache_key=hashlib.md5(request.original_query.encode()).hexdigest(),
                context={"user_query": request.original_query, "retrieved_kb_data": "", "retrieved_web_data": "", "retrieved_api_data": {}},
                use_web=False
            )

        # 2. 并行执行所有检索任务（保持原有并发逻辑）
        futures = []
        future_map = {}
    
        # 知识库检索（必须执行）
        kb_future = self.executor.submit(self._retrieve_from_knowledge_base, request.original_query)
        futures.append(kb_future)
        future_map[kb_future] = "kb"
    
        # 外部API调用（必须执行）
        api_future = self.executor.submit(self._call_external_api, request.intent, request.entities)
        futures.append(api_future)
        future_map[api_future] = "api"
    
        # 网络检索（条件执行）
        use_web_search = False
        if self.web_search_enabled and self.firecrawl_app:
            use_web_search = True
            search_query_future = self.executor.submit(self._generate_search_query, request.original_query)
            try:
                search_query = search_query_future.result(timeout=config.EXTERNAL_API_TIMEOUT)
                web_search_future = self.executor.submit(
                    self._search_web, 
                    search_query,
                    request.intent
                )
                futures.append(web_search_future)
                future_map[web_search_future] = "web"
            except Exception as e:
                self.logger.error(f"生成搜索查询失败: {e}")
                use_web_search = False
    
        # 3. 收集结果（保持原有错误处理）
        kb_data = ""
        web_data = ""
        api_data = {}
        media_assets = {}
        web_sources = []
    
        for future in as_completed(futures, timeout=config.RETRIEVAL_TIMEOUT):
            try:
                result = future.result()
                task_type = future_map[future]
            
                if task_type == "kb":
                    if isinstance(result, dict):
                        kb_data = "\n".join([doc.get("content", "") for doc in result.get("data", [])])
                        media_assets = result.get("media_assets", {})
                    else:
                        kb_data = str(result)
                    
                elif task_type == "api":
                    api_data = result if isinstance(result, dict) else {}
                    if api_data and "image_url" in api_data:
                        media_assets["api_image"] = {
                            "type": "image",
                            "content": api_data["image_url"],
                            "description": "API返回图片"
                        }
                        
                elif task_type == "web":
                    if isinstance(result, dict):
                        web_data = "\n".join([doc.get("content", "") for doc in result.get("data", [])])
                        web_sources = result.get("sources", [])
                    else:
                        web_data = str(result)
                    
            except Exception as e:
                self.logger.error(f"处理 {task_type} 任务失败: {e}", exc_info=True)

        # 4. 智能结果整合（保持原有格式）
        integrated_data = self._integrate_results(
            user_query=request.original_query,
            kb_data=kb_data,
            web_data=web_data,
            api_data=json.dumps(api_data)
        )
    
        # 5. 决定最终数据源优先级
        final_sources = self._get_sources(request.intent)
        if not kb_data and web_sources:  # 只有本地无结果且网络有结果时
            final_sources = ["网络检索"] + web_sources
        
        return RetrievalResult(
            session_id=request.session_id,
            data=integrated_data,
            media_assets=list(media_assets.values()),
            sources=final_sources,
            cache_key=hashlib.md5(request.original_query.encode()).hexdigest(),
            context={
                "user_query": request.original_query,
                "retrieved_kb_data": kb_data,
                "retrieved_web_data": web_data,
                "retrieved_api_data": api_data,
                "is_web_fallback": bool(not kb_data and web_data)  # 新增标记
            },
            use_web=use_web_search
        )
    
    def _get_sources(self, intent: str) -> List[str]:
        # 示例来源映射
        sources_map = {
            "facility_query": ["PKU Sports Facilities Database"],
            "event_query": ["PKU Event Calendar"],
            "course_info": ["PKU Sports Course Catalog"],
            "query_rule": ["PKU Sports Rules and Regulations"],
            "feedback": ["PKU Runner System"],
            "health_advice": ["Sports Committee"],
            "physical_test": ["PKU"],
            "extra_exercise": [],
            "unrecognized_intent": ["Internal System Response"]
        }
        return sources_map.get(intent, ["Multiple Sources"])
    
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.executor.shutdown(wait=True)

class APIManager:
    def __init__(self):
        self.logger = logging.getLogger('APIManager')
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
        self.api_configs = config.EXTERNAL_APIS

    def call_api(self, intent: str, entities: Dict[str, Any]) -> Dict[str, Any]:
        api_url = None
        if intent == "facility_query" and self.api_configs.get("facility_api_url"):
            api_url = self.api_configs["facility_api_url"]
        elif intent == "event_query" and self.api_configs.get("event_api_url"):
            api_url = self.api_configs["event_api_url"]
        elif intent == "course_info" and self.api_configs.get("course_api_url"):
            api_url = self.api_configs["course_api_url"]
        elif intent == "physical_test" and self.api_configs.get("physical_test_api_url"):
            api_url = self.api_configs["physical_test_api_url"]

        if not api_url:
            self.logger.info(f"No external API configured for intent: {intent}")
            return {}

        try:
            self.logger.info(f"Calling external API: {api_url} with entities: {entities}")
            response = requests.get(api_url, params=entities, timeout=config.EXTERNAL_API_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.Timeout:
            self.logger.error(f"External API call timed out: {api_url}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error calling external API {api_url}: {e}")
        return {}


class RetrievalBroker:
    def __init__(self, knowledge_loader):
        self.redis = redis.Redis(
            connection_pool=config.redis_pool,
            db=config.REDIS_DB_MAPPING["broker"]
        )
        self.retriever = SportsRetrievalAgent(knowledge_loader)
        self.input_channel = config.RETRIEVAL_REQUEST_CHANNEL
        self.output_result_prefix = config.RETRIEVAL_RESULT_PREFIX

    def start_listening(self):
        pubsub = self.redis.pubsub()
        pubsub.subscribe(self.input_channel)
        
        logger.info(f"RetrievalBroker 正在监听频道: {self.input_channel}")
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    request = RetrievalRequest(**json.loads(message['data']))
                    logger.info(f"RetrievalBroker 收到请求: Session {request.session_id}")
                    result = self.retriever.retrieve(request)
                    
                    self.redis.publish(
                        f"{self.output_result_prefix}{request.session_id}",
                        result.model_dump_json()
                    )
                    logger.info(f"RetrievalBroker 已发布结果: Session {request.session_id}")
                except Exception as e:
                    logger.error(f"RetrievalBroker 处理消息失败: {e}", exc_info=True)