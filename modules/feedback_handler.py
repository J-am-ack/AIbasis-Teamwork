import json
import threading
import redis
import logging
from config.settings import config
from config.prompt_utils import prompt_loader
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime
from openai import OpenAI
from .ans_generator import ResultGenerator
from infrastructure.message_broker import MessageBroker

class FeedbackData(BaseModel):
    """标准化反馈数据结构"""
    session_id: str = Field(..., description="关联的会话ID")
    feedback_token: str = Field(..., description="反馈追踪令牌")
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5星评分")
    suggestions: Optional[str] = Field(None, max_length=500, description="修改建议")
    context: Dict[str, Any] = Field(default_factory=dict, description="附加上下文")

class FeedbackHandler:
    def __init__(self, broker: MessageBroker, config_loader, prompt_loader, logger, redis_client): 
        # 将传入的参数存储为实例属性
        self.redis = redis_client      # <--- 确保 redis_client 被存储
        self.broker = broker
        self.config_loader = config_loader
        self.prompt_loader = prompt_loader
        self.logger = logger 

        # 复用生成器实例，并传递所有必需的参数
        self.generator = ResultGenerator(
            config_loader=self.config_loader,
            prompt_loader=self.prompt_loader,
            logger=self.logger, 
            redis_client=self.redis
        )
        self.feedback_expiry_seconds = config.RESULT_EXPIRE

    def process_feedback(self, feedback: FeedbackData) -> Dict[str, Any]:
        """
        处理用户反馈全流程：
        1. 存储原始反馈
        2. 触发重新生成（如有建议）
        3. 返回处理结果
        """
        try:
            # 1. 存储基础反馈
            self._store_feedback(feedback)
            
            # 2. 处理建议型反馈
            if feedback.suggestions:
                threading.Thread(
                    target=self._handle_suggestion,
                    args=(feedback,),
                    daemon=True
                ).start()
                return {"status": "suggestion_queued"}
                
            # 3. 处理评分型反馈
            if feedback.rating:
                self._analyze_rating(feedback)
                return {"status": "rating_recorded"}
                
            return {"status": "feedback_saved"}
            
        except Exception as e:
            self.logger.error(f"反馈处理失败: {str(e)}", exc_info=True)
            return {"error": str(e)}

    def get_revision(self, feedback_token: str) -> Optional[Dict[str, Any]]:
        """获取修订后的结果（阻塞式）"""
        try:
            if data := self.redis.get(f"feedback:revised:{feedback_token}"):
                return json.loads(data)
                
            # 检查是否正在处理
            if self.redis.exists(f"feedback:processing:{feedback_token}"):
                return {"status": "processing"}
                
            return None
        except Exception as e:
            self.logger.error(f"获取修订失败: {str(e)}")
            return None

    # ---------- 私有方法 ----------
    def _store_feedback(self, feedback: FeedbackData):
        """存储反馈数据（带时间戳）"""
        feedback_dict = feedback.model_dump_json()
        feedback_dict["timestamp"] = datetime.now().isoformat()

        if self.redis.hexists(f"feedback:session:{feedback.session_id}", feedback.feedback_token):
            self.logger.warning("重复反馈已忽略")
            return
        
        self.redis.hset(
            f"feedback:session:{feedback.session_id}",
            feedback.feedback_token,
            json.dumps(feedback_dict)
        )

    def _handle_suggestion(self, feedback: FeedbackData):
        """处理用户建议并重新生成结果"""
        try:
            # 标记处理中状态
            self.redis.setex(f"feedback:processing:{feedback.feedback_token}", 300, "1")
        
            # 获取原始结果（原有逻辑）
            original = self.redis.get(f"feedback:{feedback.feedback_token}")
            if not original:
                raise ValueError("原始结果已过期")
            
            # 存储修订结果
            self.redis.setex(
                f"feedback:revised:{feedback.feedback_token}",
                config.HYPER_PARAMS["feedback"]["feedback_ttl"],  # 24小时有效期
                json.dumps(revised)
            )
            
            # 更新反馈记录
            self.redis.hset(
                f"feedback:session:{feedback.session_id}",
                f"{feedback.feedback_token}:revised",
                "1"
            )
            
        except Exception as e:
            self.logger.error(f"建议处理失败: {str(e)}")
            raise
        finally:
            # 清除处理中状态
            self.redis.delete(f"feedback:processing:{feedback.feedback_token}")

        try:
            revised = self.generator.handle_revision(
                feedback_token=feedback.feedback_token,
                suggestions=feedback.suggestions
            )
        except TimeoutError:
            self.logger.error("生成模块调用超时")
            return {"status": "timeout"}

    def _analyze_rating(self, feedback: FeedbackData):
        """分析评分数据（示例实现）"""
        # 记录评分趋势
        self.redis.zincrby(
            "feedback:ratings",
            feedback.rating,
            f"session:{feedback.session_id}"
        )
        
        # 低评分预警
        if feedback.rating <= config.HYPER_PARAMS["feedback"]["rating_alert_threshold"]:
            self._trigger_alert(feedback)

    def _trigger_alert(self, feedback: FeedbackData):
        """触发低分警报"""
        try:
            alert_msg = self.prompt_loader.get_prompt(
                "feedback/alert.jinja2",
                rating=feedback.rating,
                session_id=feedback.session_id,
                context=feedback.context  # 假设存在context属性
            )
            self.redis.publish("feedback:alerts", alert_msg)
        except Exception as e:
            self.logger.error(f"触发低分警报失败: {str(e)}")