import redis
import json
import logging
import time
from datetime import datetime
from typing import Optional, Union
from pydantic import BaseModel
from infrastructure.shared_schemas import IntentExtractionResult, RetrievalRequest, RetrievalResult # 导入 RetrievalRequest, RetrievalResult
from config.settings import config

logger = logging.getLogger('message_broker')
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

class MessageBroker:
    def __init__(self):
        self.redis = redis.Redis(
            connection_pool=config.redis_pool,
            db=config.REDIS_DB_MAPPING["broker"],
            decode_responses=True
        )
        self.intent_channel = "intent_updates"
        self.retrieval_request_channel = "retrieval_requests" # 新增：检索请求频道
        self.retrieval_result_prefix = "retrieval_result:" # 新增：检索结果前缀
        self.result_prefix = "final_result:" # 用于最终结果缓存
        self.session_db = redis.Redis(
            connection_pool=config.redis_pool,
            db=config.REDIS_DB_MAPPING["session"], # 使用新的会话数据库
            decode_responses=True
        )


    def publish_intent(self, intent: IntentExtractionResult) -> bool:
        try:
            self.redis.setex(
                f"intent:{intent.session_id}",
                config.RESULT_EXPIRE,
                intent.model_dump_json()
            )
            self.redis.publish(
                self.intent_channel,
                json.dumps({
                    "session_id": intent.session_id,
                    "timestamp": datetime.now().isoformat()
                })
            )
            return True
        except Exception as e:
            logger.error(f"发布意图失败: {str(e)}", exc_info=True)
            return False

    def listen_for_intent(self, session_id: str, timeout: int = 5) -> Optional[IntentExtractionResult]:
        try:
            # 监听特定session_id的意图更新，通常意图结果是直接缓存而不是发布
            # 这里的逻辑更像是去检查缓存，或者等待一个信号，表示意图已处理
            # 简化为直接从Redis获取缓存
            if intent_data := self.redis.get(f"intent:{session_id}"):
                return IntentExtractionResult.model_validate_json(intent_data)
        except Exception as e:
            logger.error(f"监听意图失败: {str(e)}")
        return None

    def publish_retrieval_request(self, request: RetrievalRequest) -> bool:
        """发布检索请求到指定频道"""
        try:
            self.redis.publish(
                self.retrieval_request_channel,
                request.model_dump_json() # Pydantic V2 方法
            )
            logger.info(f"发布检索请求: Session {request.session_id}")
            return True
        except Exception as e:
            logger.error(f"发布检索请求失败: {str(e)}", exc_info=True)
            return False

    def listen_for_retrieval_result(self, session_id: str, timeout: int = 30) -> Optional[RetrievalResult]:
        """
        监听并获取特定session_id的检索结果。
        通过一个专属频道实现阻塞式等待。
        """
        channel_name = f"{self.retrieval_result_prefix}{session_id}"
        pubsub = self.redis.pubsub()
        pubsub.subscribe(channel_name)
        
        logger.info(f"监听检索结果频道: {channel_name} (超时: {timeout}秒)")
        start_time = time.time()
        while time.time() - start_time < timeout:
            message = pubsub.get_message(timeout=1) # 短暂阻塞，避免CPU空转
            if message and message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    return RetrievalResult.model_validate(data)
                except Exception as e:
                    logger.error(f"解析检索结果消息失败: {message['data']}, 错误: {e}")
                    return None
            time.sleep(0.1) # 小等待，防止忙循环
        logger.warning(f"Session {session_id}: 等待检索结果超时。")
        return None

    def cache_result(self, session_id: str, result: Union[dict, BaseModel]) -> bool:
        """统一缓存方法（兼容Pydantic V2）"""
        try:
            serialized = (
                result.model_dump_json()
                if isinstance(result, BaseModel)
                else json.dumps(result, ensure_ascii=False)
            )
            return self.redis.setex(
                f"{self.result_prefix}{session_id}",
                config.RESULT_EXPIRE,
                serialized
            )
        except Exception as e:
            logger.error(f"缓存失败: {str(e)}", exc_info=True)
            return False

    def get_cached_result(self, session_id: str) -> Optional[dict]:
        """获取缓存结果（自动JSON解析）"""
        try:
            if data := self.redis.get(f"{self.result_prefix}{session_id}"):
                return json.loads(data)
        except Exception as e:
            logger.error(f"获取缓存结果失败: {str(e)}", exc_info=True)
        return None