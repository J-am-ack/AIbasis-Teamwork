import os
import base64
import uuid
from config.settings import config
from config.prompt_utils import prompt_loader
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class MediaType(str, Enum):
    MAP = "map"
    CHART = "chart"
    IMAGE = "image"
    VIDEO = "video"

class MediaItem(BaseModel):
    type: MediaType = Field(..., description="媒体类型")
    content: str = Field(..., description="Base64编码的内容数据或URL")
    description: str = Field("", description="无障碍文本描述")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="附加元数据")
    
    @classmethod
    def from_image_file(cls, path: str):
        with open(path, "rb") as f:
            return cls(
                type=MediaType.IMAGE,
                content=base64.b64encode(f.read()).decode(),
                description=f"图片: {os.path.basename(path)}"
            )

class IntentExtractionResult(BaseModel):
    session_id: str = Field(..., description="会话ID")
    intent: str = Field(..., description="识别的意图")
    entities: Dict[str, Any] = Field(default_factory=dict, description="提取的实体")
    confidence: float = Field(..., ge=0.0, le=1.0, description="意图识别置信度")
    is_clarification_needed: bool = Field(False, description="是否需要用户进一步澄清")
    clarification_prompt: Optional[str] = Field(None, description="澄清提示")
    context: Dict[str, Any] = Field(default_factory=dict, description="意图识别的上下文信息")
    user_query: Optional[str] = Field(None, description="原始用户查询") # 确保这个字段也存在

class RetrievalRequest(BaseModel):
    session_id: str
    intent: str = Field(..., description="识别的意图类型")
    entities: Dict[str, Any] = Field(default_factory=dict, description="意图提取的实体")
    original_query: str = Field(..., description="用户原始的查询文本") # <--- 新增此行
    retrieval_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="检索ID") # 如果需要唯一标识
    timestamp: datetime = Field(default_factory=datetime.now, description="请求时间戳")
    context: Dict[str, Any] = Field(default_factory=dict, description="从意图识别传递过来的上下文") # 确保有context字段
    use_web: bool = Field(default=False, description="是否启用网络搜索") # 如果你的检索请求包含是否用网络搜索的标志

class RetrievalResult(BaseModel):
    session_id: str
    data: Dict[str, Any] # 整合后的数据，通常是一个字符串或者更复杂的结构
    media_assets: List[Dict[str, Any]] = Field(default_factory=list) 
    sources: List[str] = Field(default_factory=list)
    cache_key: Optional[str] = None
    context: Dict[str, Any]
    use_web: bool = Field(default=False, description=f"是否启用网络检索（当前配置: {config.WEB_SEARCH_ENABLED}）")

class GenerationInput(BaseModel):
    # 新增健康相关字段
    height: Optional[float] = None
    weight: Optional[float] = None
    goal: Optional[str] = None
    # 确保context包含user_query
    context: Dict[str, Any] = Field(default_factory=lambda: {"user_query": ""})
    # 明确定义 entities 字段
    entities: Dict = Field(default_factory=dict) # 确保 entities 类型正确且有默认值

    @field_validator('entities', mode='before')
    @classmethod
    def handle_empty_entities(cls, v: Optional[Dict]) -> Dict:
        """确保entities字段永远不会是None"""
        return v if v is not None else {}

class FeedbackInput(BaseModel):
    session_id: str
    feedback_token: str = Field(..., description="生成模块返回的追踪令牌")
    rating: Optional[int] = Field(None, ge=1, le=5, description="1-5星评分")
    suggestions: Optional[str] = Field(None, max_length=500, description="修改建议")
    context: Dict[str, Any] = Field(default_factory=dict, description="附加上下文") # 新增 context 字段

class RevisedOutput(BaseModel):
    """修订后的输出"""
    success: bool
    data: Dict[str, Any]
    media: List[MediaItem] = Field(default_factory=list)
    revision_notes: Optional[str] = None