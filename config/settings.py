import os
import logging
import redis

from enum import Enum
from dotenv import load_dotenv
from typing import Dict, Any, Optional

load_dotenv()

class Env(str, Enum):
    PROD = "production"
    DEV = "development"

class Settings:
    ENV: Env = Env(os.getenv("APP_ENV", "development"))
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = os.getenv("PORT", 5000)

    DEBUG = False
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    # 确保所有模块使用的Redis DB都在这里定义
    REDIS_DB_MAPPING: Dict[str, int] = {
        "broker": 0,
        "cache": 1,
        "feedback": 2,
        "session": 3,
        "intent": 4,
        "retrieval": 5,
        "generator": 6,
    }

    # 意图类型定义
    INTENT_TYPES: Dict[str, Dict[str, Any]] = {
        "facility_query": {
            "name": "设施查询",
            "description": "用户询问关于体育设施（如体育馆、游泳池、跑道等）的信息，例如开放时间、位置、预订方式等。",
            "keywords": ["邱德拔", "康美乐", "五四", "二体", "理教地下", "游泳池", "羽毛球场", "乒乓球场", "预定", "开放时间", "在哪里", "篮球场", "预约"],
            "examples": ["邱德拔什么时候开门", "篮球场怎么预订", "羽毛球馆现在有空位吗"]
        },
        "event_query": {
            "name": "活动/赛事查询",
            "description": "用户询问关于体育赛事、活动（如篮球赛、足球赛、健身活动等）的信息，例如时间、地点、参与方式、结果等。",
            "keywords": ["北大杯", "五四长跑", "赛事", "报名", "夜奔", "新生杯", "时间", "地点", "结果", "参与"],
            "examples": ["这周四的夜奔是什么主题", "五四长跑怎么报名", "昨天的北大杯足球赛结果是什么"]
        },
        "course_info": {
            "name": "课程查询",
            "description": "用户询问关于体育课程（如篮球课、游泳课、健身指导等）的信息，例如课程内容、时间、费用、报名方式等。",
            "keywords": ["课程", "老师", "教学", "学习", "上课地点", "上课时间"],
            "examples": ["游泳课在哪上", "排球课的上课时间"]
        },
        "physical_test": {
            "name": "身体素质测试",
            "description": "用户询问关于身体素质测试或相关标准的信息。",
            "keywords": ["体测", "身体素质", "标准", "测试", "1000米", "800m", "引体向上", "跳远", "仰卧起坐", "准备考试", "如何提高"],
            "examples": ["体测有什么项目", "大二男生引体向上的标准是什么", "如何准备1000米考试"]
        },
        "feedback": {
            "name": "反馈",
            "description": "用户提供关于助手的反馈、建议或报告问题。",
            "keywords": ["反馈", "建议", "维修", "不好用", "投诉", "态度差", "bug", "改进"],
            "examples": ["这个助手不太好用", "我有一个建议", "这里好像有个bug", "某场馆工作人员服务太差，给我学校相关部门的电话，我要反映情况"]
        },
        "health_advice": {
            "name": "运动建议",
            "description": "用户寻求关于特定运动、健身计划或健康生活方式的建议。",
            "keywords": ["建议", "怎么运动", "计划", "健身", "锻炼", "食谱", "减肥", "增肌"],
            "examples": ["我想减肥，有什么运动建议", "如何制定健身计划", "推荐一些增肌的训练"]
        },
        "extra_exercise": {
            "name": "课外锻炼",
            "description": "用户寻求关于课外锻炼的要求、规则以及使用软件遇到困难时的解决办法。",
            "keywords": ["85km", "PKU Runeer", "乐动力", "课外锻炼", "里程奖励", "闪退", "配速", "跑步位置"],
            "examples": ["85km必须在五四跑吗", "使用PKU Runner时软件总是闪退，该怎么解决", "85km要求配速是多少"],
            "entities": {
            "info_type": {  # 专门提取细分类别
                "requirements": ["要求", "标准", "配速多少"],
                "rules": ["注意", "禁止", "违规"],
                "rewards": ["里程奖励"],
                "app_usage": ["怎么用", "闪退", "异常", "PKU Runner", "乐动力"],
                "feedback": ["反馈", "管理员", "联系"]
            }
        }
        },
        "unrecognized_intent": {
            "description": "系统未能识别的用户意图，作为兜底策略",
            "examples": [],
            "keywords": []
        }
    }

    INTENT_EXPIRE: int = int(os.getenv("INTENT_EXPIRE_SECONDS", 3600))
    RESULT_EXPIRE: int = int(os.getenv("RESULT_EXPIRE_SECONDS", 3600)) # 最终结果缓存过期时间
    RETRIEVAL_TIMEOUT: int = int(os.getenv("RETRIEVAL_TIMEOUT", 30)) # 检索结果等待超时时间

    FAISS_INDEX_PATH: str = os.getenv("FAISS_INDEX_PATH", "./knowledge_base/faiss_index")
    KNOWLEDGE_BASE_PATH: str = os.getenv("KNOWLEDGE_BASE_PATH", "./knowledge_base")
    MEDIA_STORAGE_PATH: str = os.getenv("MEDIA_STORAGE_PATH", "./media_assets")
    CDN_BASE_URL: str = os.getenv("CDN_BASE_URL", "https://cdn.example.com/sports")

    DASHSCOPE_API_KEY: str = os.getenv("DASHSCOPE_API_KEY")
    DASHSCOPE_BASE_URL: str = os.getenv("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    FIRECRAWL_API_KEY: str = os.getenv("FIRECRAWL_API_KEY")

    EXTERNAL_APIS: Dict[str, Any] = {
        "enable_external_apis": False,  # 默认关闭
        "facility_api_url": "http://localhost:8001/api/facilities",
        "event_api_url": "http://localhost:8002/api/events",
        "course_api_url": [
            "https://dean.pku.edu.cn/service/web/courseSearch.php",
            "https://pe.pku.edu.cn/jyjx/tykc1.htm",
        ],
        "physical_test_api_url": [
            "http://localhost:8004/api/physical_tests",                                  
        ],
        "health_advice_api_url": "http://localhost:8005/api/health_advice",
        "extra_exercise_api_url": "http://localhost:8006/api/extra_exercise",
        "feedback_api_url": "http://localhost:8007/api/feedback"
    }

    EXTERNAL_API_TIMEOUT: int = int(os.getenv("EXTERNAL_API_TIMEOUT", 5))

    MODEL_CONFIGS: Dict[str, Dict[str, Any]] = {
        "intent": {
            "model_name": os.getenv("INTENT_MODEL_NAME", "qwen-max"),
            "temperature": float(os.getenv("INTENT_MODEL_TEMP", 0.0)),
            "top_p": float(os.getenv("INTENT_MODEL_TOP_P", 0.9)),
            "max_tokens": 1024,
            "stream": True
        },
        "retrieval": {
            "model_name": os.getenv("RETRIEVAL_MODEL_NAME", "qwen-max"),
            "temperature": float(os.getenv("RETRIEVAL_MODEL_TEMP", 0.1)),
            "top_p": float(os.getenv("RETRIEVAL_MODEL_TOP_P", 0.9)),
            "max_tokens": 2048,
            "stream": True
        },
        "generation": {
            "model_name": os.getenv("GENERATION_MODEL_NAME", "qwen-plus"),
            "temperature": float(os.getenv("GENERATION_MODEL_TEMP", 0.7)),
            "top_p": float(os.getenv("GENERATION_MODEL_TOP_P", 0.9)),
            "max_tokens": 2048,
            "stream": True
        }
    }

    RETRIEVAL_WORKERS: int = int(os.getenv("RETRIEVAL_WORKERS", 5))

    WEB_SEARCH_ENABLED: bool = os.getenv("WEB_SEARCH_ENABLED", "false").lower() == "true"
    INTENT_API_URL: Optional[str] = os.getenv("INTENT_API_URL")
    INTENT_TIMEOUT: int = int(os.getenv("INTENT_TIMEOUT", 5))
 
    EMBEDDING_CONFIG: Dict[str, Any] = {
        "model_name": os.getenv("EMBEDDING_MODEL_NAME", "text-embedding-v2"),
        "api_key": os.getenv("DASHSCOPE_API_KEY"),
    }

    # 规定可以输出图片的意图类型
    MEDIA_INTENTS = [
        "facility_query",  # 场馆查询
        "event_query",     # 活动查询
    ]

    RETRIEVAL_REQUEST_CHANNEL: str = os.getenv("RETRIEVAL_REQUEST_CHANNEL", "retrieval_requests")
    RETRIEVAL_RESULT_PREFIX: str = os.getenv("RETRIEVAL_RESULT_PREFIX", "retrieval_result:")

    HYPER_PARAMS: Dict[str, Dict[str, Any]] = {
        "cache": {
            "intent_expiry": int(os.getenv("INTENT_CACHE_EXPIRY", 3600)), # 示例值：1小时，你可以调整
            "retrieval_expiry": int(os.getenv("RETRIEVAL_CACHE_EXPIRY", 7200)), # 如果有的话
            "retrieval_expiry": int(os.getenv("RETRIEVAL_CACHE_EXPIRY", 7200)),
        },
        "security": {
            "banned_keywords": [
                ## 需要将txt文件中的内容转移到这里
            ],
            "max_input_length": 100,
        },
        "intent": {
            "local_match_threshold": 0.7,
            "api_confidence_threshold": 0.5,
            "llm_confidence_threshold": 0.6,
            "cache_expiration_minutes": 60
        },
        "retrieval": {
            "timeout": 15,
            "top_k": 3,
            "min_score": 0.7
        },
        "generation": {
            "timeout": 30
        },
        "feedback": {
            "process_timeout": 10
        },
        "rag": {
            "top_k": int(os.getenv("HP_RAG_TOP_K", 5)),
            "min_score": float(os.getenv("HP_RAG_MIN_SCORE", 0.7)),
            "use_ivf_index": os.getenv("HP_RAG_USE_IVF_INDEX", "false").lower() == "true",
            "nlist": int(os.getenv("HP_RAG_NLIST", 100)),
            "nprobe": int(os.getenv("HP_RAG_NPROBE", 32)),
            "chunk_size": 512,  # 分块大小
            "overlap": 50,      # 块间重叠
            "retrieval_strategy": "hybrid"  # vector/keyword/hybrid
        },
        "media": {
            "max_size_mb": 5,  # 图片大小限制
            "thumbnail_dimensions": [512, 512],  # 缩略图尺寸
            "min_similarity": 0.65,  # 语义匹配阈值
            "cache_ttl": 86400,  # 媒体缓存时间(秒)
            "keyword_match_threshold": 1  # 至少匹配1个关键词
        },
        "feedback": {
            "rating_alert_threshold": int(os.getenv("HP_FEEDBACK_RATING_ALERT_THRESHOLD", 2))
        },
        "security": {
            "banned_keywords": [
                "打架", "斗殴", "群殴", "欺凌", "霸凌", "暴力", "殴打", "攻击", "伤害",
                "武器", "刀具", "枪支", "自残", "自杀", "威胁", "恐吓", "虐待", "禁药", "兴奋剂",
                "作弊", "替考", "代考", "贿赂", "代跑", "买通", "赌博", "赌球", "假赛", "操控比赛",
                "违规", "作弊码", "外挂",
                "种族歧视", "性别歧视", "地域歧视", "学历歧视", "黑鬼", "白皮", "娘娘腔", "胖子", "傻子", "残疾人",
                "骚扰", "性骚扰", "猥亵", "调戏", "侮辱", "诽谤", "人身攻击", "歧视", "偏见", "脏话", "粗口", "粗鄙", "下流",
                "毒品", "吸毒", "贩毒", "盗窃", "偷窃", "抢劫", "非法", "违禁", "管制物品",
                "色情", "裸露", "黄", "招嫖", "援交",
                "酒", "喝酒", "醉酒", "烟", "吸烟", "酒吧", "夜店", "网吧", "翻墙", "逃课",
                "黑客", "破解", "攻击", "病毒", "木马", "隐私泄露", "个人信息", "钓鱼", "诈骗",
                "投降", "放弃", "认输", "消极比赛", "敷衍", "不正当竞争", "裁判不公", "暴力倾向", "极端情绪",
                "习近平", "东大", "毛泽东", "六四", "宗教", "政治", "煽动", "游行示威"
            ],
            "max_query_length": int(os.getenv("HP_SECURITY_MAX_QUERY_LENGTH", 200)),
            "keyword_blocklist_path": os.getenv("HP_SECURITY_KEYWORD_BLOCKLIST_PATH", "./config/security_blocklist.json")
        }
    }

    redis_pool: Any = None

    def __init__(self):
        pass

    @classmethod
    def apply_env_overrides(cls):
        for key, value in list(cls.__dict__.items()):
            if not key.startswith('__') and not callable(value) and not isinstance(value, (Dict, Enum)):
                env_key = key.upper()
                env_val = os.getenv(env_key)
                if env_val is not None:
                    try:
                        if isinstance(value, bool):
                            setattr(cls, key, env_val.lower() == "true")
                        elif isinstance(value, int):
                            setattr(cls, key, int(env_val))
                        elif isinstance(value, float):
                            setattr(cls, key, float(env_val))
                        else:
                            setattr(cls, key, env_val)
                    except ValueError:
                        logging.warning(f"Failed to convert env var {env_key} to expected type for {key}. Keeping original type.")
        
        for config_name, sub_config in cls.MODEL_CONFIGS.items():
            for key, value in list(sub_config.items()):
                env_key = f"MODEL_{config_name.upper()}_{key.upper()}"
                env_val = os.getenv(env_key)
                if env_val is not None:
                    try:
                        if isinstance(value, bool):
                            cls.MODEL_CONFIGS[config_name][key] = env_val.lower() == "true"
                        elif isinstance(value, (int, float)):
                            cls.MODEL_CONFIGS[config_name][key] = type(value)(env_val)
                        else:
                            cls.MODEL_CONFIGS[config_name][key] = env_val
                    except ValueError:
                        logging.warning(f"Failed to convert env var {env_key} to expected type for {key}. Keeping original type.")
        
        for key, value in list(cls.EMBEDDING_CONFIG.items()):
            env_key = f"EMBEDDING_{key.upper()}"
            env_val = os.getenv(env_key)
            if env_val is not None:
                try:
                    if isinstance(value, bool):
                        cls.EMBEDDING_CONFIG[key] = env_val.lower() == "true"
                    elif isinstance(value, (int, float)):
                        cls.EMBEDDING_CONFIG[key] = type(value)(env_val)
                    else:
                        cls.EMBEDDING_CONFIG[key] = env_val
                except ValueError:
                    logging.warning(f"Failed to convert env var {env_key} to expected type for {key}. Keeping original type.")

        for key, value in list(cls.EXTERNAL_APIS.items()):
            env_key = f"EXTERNAL_APIS_{key.upper()}"
            env_val = os.getenv(env_key)
            if env_val is not None:
                try:
                    if isinstance(value, bool):
                        cls.EXTERNAL_APIS[key] = env_val.lower() == "true"
                    elif isinstance(value, (int, float)):
                        cls.EXTERNAL_APIS[key] = type(value)(env_val)
                    else:
                        cls.EXTERNAL_APIS[key] = env_val
                except ValueError:
                    logging.warning(f"Failed to convert env var {env_key} to expected type for {key}. Keeping original type.")

        for category in cls.HYPER_PARAMS:
            for param_key, param_value in list(cls.HYPER_PARAMS[category].items()): # 使用list()来迭代字典的副本
                env_key = f"HP_{category.upper()}_{param_key.upper()}"
                env_val = os.getenv(env_key)
                if env_val is not None:
                    try:
                        cls.HYPER_PARAMS[category][param_key] = type(param_value)(env_val)
                    except ValueError:
                        logging.warning(f"Failed to convert env var {env_key} to expected type for {param_key}. Keeping original type.")

config = Settings()
config.apply_env_overrides()

if not Settings.redis_pool:
    Settings.redis_pool = redis.ConnectionPool.from_url(
        config.REDIS_URL,
        db=config.REDIS_DB_MAPPING["broker"],
        decode_responses=True
    )