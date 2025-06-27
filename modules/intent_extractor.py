import os
import sys
import json
import uuid
import logging
import hashlib
import re
import redis
import requests
import unicodedata
import time 
from typing import Optional, Any, Dict, List, Tuple
from time import perf_counter
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from config.settings import config
from config.prompt_utils import prompt_loader
from openai import OpenAI
from camel.configs import QwenConfig # 重新添加 QwenConfig 因为 _call_llm 可能间接用到
from camel.models import ModelFactory # 重新添加 ModelFactory 因为 _call_llm 可能间接用到
from camel.types import ModelPlatformType, RoleType # 重新添加 ModelPlatformType 和 RoleType
from camel.agents import ChatAgent
from camel.messages import BaseMessage
from infrastructure.shared_schemas import IntentExtractionResult, RetrievalRequest

load_dotenv(dotenv_path='.env.development')

# 初始化日志
logger = logging.getLogger('intent_extractor')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

# ---------- SecurityFilter 类定义 ----------
class SecurityFilter:
    def __init__(self):
        self.banned_keywords = config.HYPER_PARAMS["security"].get("banned_keywords", [])
        self.max_length = config.HYPER_PARAMS["security"].get("max_input_length", 200)

    def is_safe(self, text: str) -> bool:
        if len(text) > self.max_length:
            logger.warning(f"用户输入超出最大长度限制: {self.max_length} 字符。")
            return False
        for keyword in self.banned_keywords:
            if keyword.lower() in text.lower():
                logger.warning(f"检测到禁用关键词: '{keyword}'。")
                return False
        return True
    
# ---------- 装饰器定义 ----------
def log_execution_time(func):
    """记录函数执行时间的装饰器。"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = perf_counter()
        result = func(*args, **kwargs)
        end_time = perf_counter()
        logger.info(f"函数 {func.__name__} 执行耗时: {end_time - start_time:.4f} 秒")
        return result
    return wrapper

# ---------- IntentExtractor 类定义 ----------
class IntentExtractor:
    def __init__(self, agent: ChatAgent): # 明确指定 agent 类型
        self.agent = agent  # 这是 CamelAgent 实例
        self.logger = logging.getLogger('intent_extractor')
        self.security_filter = SecurityFilter()
        self.redis = redis.Redis(connection_pool=config.redis_pool, db=config.REDIS_DB_MAPPING["intent"])
        self.cache_expiry = config.HYPER_PARAMS["cache"]["intent_expiry"]
        # 用于缓存LLM意图识别结果，避免重复调用
        self.llm_cache_db = redis.Redis(
            connection_pool=config.redis_pool,
            db=config.REDIS_DB_MAPPING["intent"], # 使用意图识别专用DB
            decode_responses=True
        )

    def _build_prompt(self, text: str, context: Dict[str, Any]) -> str:
        """
        构建用于意图识别的系统提示。
        """
        system_prompt = prompt_loader.get_prompt(
            "intent/intent_system.jinja2",
            user_query=text,
            current_date=datetime.now().strftime("%Y-%m-%d"),
            role="专业的校园体育信息助手"
        )
        return system_prompt

    def _check_local_rules(self, text: str) -> Optional[Dict[str, Any]]:
        """根据预设关键词规则进行意图识别（优先级高于LLM）"""
        for intent_name, intent_data in config.INTENT_TYPES.items():
            keywords = intent_data.get("keywords", [])
            if any(kw.lower() in text.lower() for kw in keywords):
                return {
                    "intent": intent_name,
                    "confidence": 0.9,  # 本地规则高置信度
                    "entities": {},
                    "source": "local_rules"
            }
        return None

    def _call_llm(self, session_id: str, system_prompt: str, user_query: str) -> str:
        """
        调用大型语言模型进行意图识别。
        """
        self.logger.info(f"Session {session_id}: 调用LLM进行意图识别...")
        
        # CamelAgent需要BaseMessage
        sys_msg = BaseMessage(
            role_name="System", 
            role_type=RoleType.ASSISTANT, 
            content=system_prompt,
            meta_dict={  # 添加必要的meta_dict参数
                "module": "intent_extractor",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        )

        usr_msg = BaseMessage(
            role_name="User", 
            role_type=RoleType.USER, 
            content=user_query,
            meta_dict={  # 添加必要的meta_dict参数
                "module": "intent_extractor",
                "session_id": session_id,
                "timestamp": datetime.now().isoformat()
            }
        )

        # 重置agent，确保每次新的对话从干净状态开始
        self.agent.reset()
        
        # 发送系统消息
        self.agent.step(sys_msg) 
        
        # 发送用户消息并获取响应
        response = self.agent.step(usr_msg)
        
        # 处理响应 - 适应新的ChatAgentResponse对象
        if response and hasattr(response, 'msg'):
            llm_response_content = response.msg.content
            self.logger.info(f"Session {session_id}: LLM原始响应: {llm_response_content[:200]}...")
            return llm_response_content
        else:
            self.logger.error(f"Session {session_id}: LLM没有返回有效响应。")
            return ""

    def safe_parse_json(self, session_id: str, text: str) -> Optional[Dict[str, Any]]:
        """安全地解析JSON字符串，如果失败则返回None并记录错误。"""
        try:
            # 尝试找到第一个和最后一个大括号，以处理LLM可能输出额外文本的情况
            json_match = re.search(r'\{.*\}', text.strip(), re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                parsed_data = json.loads(json_str)
                # 简单验证是否是字典
                if isinstance(parsed_data, dict):
                    return parsed_data
                else:
                    self.logger.error(f"Session {session_id}: JSON解析成功但结果不是字典。原始内容: {text}")
                    return None
            else:
                self.logger.error(f"Session {session_id}: 无法在LLM响应中找到有效的JSON结构。原始内容: {text}")
                return None
        except json.JSONDecodeError as e:
            self.logger.error(f"Session {session_id}: safe_parse_json 失败: {e}. 原始内容: '{text}'")
            return None
        except Exception as e:
            self.logger.error(f"Session {session_id}: safe_parse_json 发生意外错误: {e}. 原始内容: '{text}'")
            return None

    def _process_llm_response(self, session_id: str, llm_response_content: str) -> IntentExtractionResult:
        """
        处理LLM的原始响应，尝试解析为IntentExtractionResult。
        如果解析失败，则返回一个默认的 unrecognized_intent 结果。
        """
        parsed_data = self.safe_parse_json(session_id, llm_response_content)
        
        if parsed_data:
            intent = parsed_data.get("intent")
            entities = parsed_data.get("entities", {})
            confidence = float(parsed_data.get("confidence", 0.0))
            # 确保置信度在有效范围内
            confidence = max(0.0, min(1.0, confidence)) 
            
            # 确保意图是有效的，如果不是则默认为unrecognized_intent
            if intent not in config.INTENT_TYPES:
                self.logger.warning(f"Session {session_id}: LLM识别出未知意图 '{intent}'，默认为 'unrecognized_intent'。")
                intent = "unrecognized_intent"
                confidence = 0.0 # 未知意图降低置信度

            result = IntentExtractionResult(
                session_id=session_id,
                intent=intent,
                entities=entities,
                confidence=confidence
            )
            self.logger.info(f"Session {session_id}: LLM意图识别结果: {result.intent} (Confidence: {result.confidence:.2f})")
            return result
        else:
            # 如果解析失败，返回一个明确的 'unrecognized_intent' 结果
            self.logger.warning(f"Session {session_id}: LLM响应无法解析为JSON，默认为 'unrecognized_intent'。原始内容: {llm_response_content}")
            return IntentExtractionResult(
                session_id=session_id,
                intent="unrecognized_intent",
                entities={},
                confidence=0.0
            )

    def _cache_llm_result(self, session_id: str, user_input_hash: str, result: IntentExtractionResult):
        """缓存LLM意图识别结果。"""
        try:
            self.llm_cache_db.setex(
                f"llm_intent_cache:{user_input_hash}",
                self.cache_expiry,
                result.model_dump_json() # 使用pydantic model_dump_json
            )
            self.llm_cache_db.setex(
                f"session_llm_intent:{session_id}", # 缓存会话ID到LLM结果哈希的映射
                self.cache_expiry,
                user_input_hash
            )
            self.logger.debug(f"Session {session_id}: LLM意图结果已缓存。")
        except Exception as e:
            self.logger.error(f"Session {session_id}: 缓存LLM意图结果失败: {e}")

    def _get_cached_llm_result(self, session_id: str, user_input_hash: str) -> Optional[IntentExtractionResult]:
        """获取缓存的LLM意图识别结果。"""
        try:
            cached_data = self.llm_cache_db.get(f"llm_intent_cache:{user_input_hash}")
            if cached_data:
                result = IntentExtractionResult.model_validate_json(cached_data) # 使用pydantic model_validate_json
                self.logger.info(f"Session {session_id}: 从缓存获取LLM意图结果: {result.intent} (Confidence: {result.confidence:.2f})")
                return result
            else:
                return None
        except Exception as e:
            self.logger.warning(f"Session {session_id}: 获取缓存LLM意图结果失败或缓存无效: {e}")
            return None

    def _check_local_rules(self, text: str) -> Optional[Dict[str, Any]]:
        """
        根据预设的关键词规则进行意图识别。
        优先级高于LLM识别，如果命中则直接返回。
        """
        for intent_name, intent_data in config.INTENT_TYPES.items():
            # 排除不需要本地规则匹配的意图，例如 unrecognized_intent, retrieval
            if intent_name in ["unrecognized_intent", "retrieval"]:
                continue

            keywords = intent_data.get("keywords", [])
            for keyword in keywords:
                # 假设关键词匹配不区分大小写
                if keyword.lower() in text.lower():
                    self.logger.debug(f"本地匹配：通过关键词 '{keyword}' 匹配到意图: {intent_name}")
                    return {"intent": intent_name, "confidence": 0.85, "entities": {}, "source": "local_rules"}
        self.logger.debug("本地匹配：未找到匹配的意图。")
        return None

    def _query_online_api(self, text: str) -> Optional[Dict[str, Any]]:
        """
        调用外部API进行意图识别（如果启用）。
        """
        if not config.WEB_SEARCH_ENABLED or not config.INTENT_API_URL:
            self.logger.debug("外部意图API未启用或URL未配置。")
            return None
            
        try:
            self.logger.info(f"尝试调用外部意图API: {config.INTENT_API_URL}")
            resp = requests.post(
                config.INTENT_API_URL,
                json={"text": text},
                timeout=config.INTENT_TIMEOUT
            )
            resp.raise_for_status() # 对HTTP错误状态码抛出异常
            data = resp.json()
            
            return {
                "intent": data.get("intent", "unrecognized_intent"), # 外部API返回的意图
                "confidence": float(data.get("confidence", 0.0)),
                "source": "external_api"
            }
        except requests.exceptions.Timeout:
            self.logger.error(f"调用外部意图API超时: {config.INTENT_API_URL}")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"调用外部意图API时发生错误: {e}")
        except json.JSONDecodeError:
            self.logger.error(f"外部意图API返回的响应不是有效JSON。原始内容: {resp.text}")
        except Exception as e:
            self.logger.error(f"调用外部意图API时发生未知错误: {e}")
        return None

    def _apply_fallback_strategies(self, 
                                   session_id: str, 
                                   user_input: str, 
                                   camel_result: IntentExtractionResult, # 确保这是 IntentExtractionResult 对象
                                   local_result: Optional[Dict[str, Any]],
                                   api_result: Optional[Dict[str, Any]]) -> IntentExtractionResult:
        """
        根据不同的意图识别结果应用回退策略，确定最终意图。
        优先级：本地规则 > 外部API > LLM识别。
        """
        # 1. 优先使用本地规则匹配结果
        if local_result and local_result.get("intent"):
            self.logger.info(f"Session {session_id}: 采用本地规则匹配意图: {local_result['intent']} (Confidence: {local_result['confidence']:.2f})")
            return IntentExtractionResult(
                session_id=session_id,
                intent=local_result["intent"],
                entities=local_result.get("entities", {}),
                confidence=local_result["confidence"]
            )

        # 2. 其次考虑外部API结果（如果启用且置信度满足要求）
        if api_result and api_result.get("intent") and api_result.get("confidence", 0.0) >= config.HYPER_PARAMS["intent"]["api_min_confidence"]:
            self.logger.info(f"Session {session_id}: 采用外部API意图: {api_result['intent']} (Confidence: {api_result['confidence']:.2f})")
            return IntentExtractionResult(
                session_id=session_id,
                intent=api_result["intent"],
                entities=api_result.get("entities", {}),
                confidence=api_result["confidence"]
            )
            
        # 3. 最后考虑LLM识别结果（如果置信度满足要求）
        # 确保 camel_result 是 IntentExtractionResult 对象
        if camel_result and camel_result.confidence >= config.HYPER_PARAMS["intent"]["llm_confidence_threshold"]:
            self.logger.info(f"Session {session_id}: 采用LLM识别意图: {camel_result.intent} (Confidence: {camel_result.confidence:.2f})")
            return camel_result # 直接返回LLM的结果对象
        
        # 4. 所有策略都未命中，返回 'unrecognized_intent'
        self.logger.info(f"Session {session_id}: 所有意图识别策略均未命中，默认为 'unrecognized_intent'。")
        return IntentExtractionResult(
            session_id=session_id,
            intent="unrecognized_intent",
            entities={},
            confidence=0.0,
        )

    @log_execution_time
    def extract_intent(self, session_id: str, user_input: str) -> IntentExtractionResult:
        self.logger.info(f"Session {session_id}: 开始意图识别。")

        # 0. 安全过滤
        if not self.security_filter.is_safe(user_input):
            self.logger.warning(f"Session {session_id}: 用户输入未能通过安全过滤。")
            return IntentExtractionResult(
                session_id=session_id,
                intent="unrecognized_intent", # 安全问题导致无法识别
                entities={},
                confidence=0.0,
                clarification_needed=True,
                clarification_prompt="您的输入包含敏感内容或不符合规范，请重新尝试。"
            )
        
        # 标准化输入
        cleaned_text = unicodedata.normalize('NFKC', user_input).strip()
        user_input_hash = hashlib.sha256(cleaned_text.encode('utf-8')).hexdigest()

        # 1. 优先尝试本地规则匹配
        local_intent_result = self._check_local_rules(cleaned_text)
        if local_intent_result:
            return IntentExtractionResult(
                session_id=session_id,
                intent=local_intent_result["intent"],
                entities=local_intent_result.get("entities", {}),
                confidence=local_intent_result["confidence"]
            )
        
        # 2. 尝试从缓存获取LLM结果
        cached_llm_result = self._get_cached_llm_result(session_id, user_input_hash)
        if cached_llm_result:
            return cached_llm_result

        # 3. 本地规则匹配 (高优先级)
        local_intent_result = self._check_local_rules(cleaned_text)
        if local_intent_result:
            final_result = IntentExtractionResult(
                session_id=session_id,
                intent=local_intent_result['intent'],
                entities=local_intent_result.get('entities', {}),
                confidence=local_intent_result['confidence']
            )
            self._cache_llm_result(session_id, user_input_hash, final_result) # 缓存本地匹配结果
            return final_result

        # 4. LLM 意图识别
        system_prompt = self._build_prompt(text=cleaned_text, context={})
        llm_response_content = self._call_llm(session_id, system_prompt, cleaned_text)
        
        # 处理LLM响应，即使是无效JSON也会返回一个IntentExtractionResult
        camel_llm_result = self._process_llm_response(session_id, llm_response_content)

        # 5. 外部API意图识别 (中优先级)
        api_intent_result = self._query_online_api(cleaned_text)

        # 6. 应用回退策略
        final_result = self._apply_fallback_strategies(
            session_id, 
            user_input, # 传递原始用户输入，如果_apply_fallback_strategies需要
            camel_llm_result, # 传递 IntentExtractionResult 对象
            local_intent_result,
            api_intent_result
        )

        # 缓存最终确认的LLM意图结果
        # original: if final_result.source == "llm_detection": # 只有LLM识别的结果才缓存
        # 修正：`source` 字段只在 `_check_local_rules` 和 `_query_online_api` 中设置。
        # 如果是LLM识别，`source` 默认为空，所以这里需要修改判断逻辑
        # 或者在 IntentExtractionResult 中明确定义 source
        # 为避免引入新的复杂性，且LLM识别是默认或回退方案，我们直接缓存最终结果。
        self._cache_llm_result(session_id, user_input_hash, final_result)

        return final_result