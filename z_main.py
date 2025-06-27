from dotenv import load_dotenv
load_dotenv(dotenv_path='.env.development')

from flask import Flask, request, jsonify, Response, stream_with_context
from modules.intent_extractor import SecurityFilter, IntentExtractor 
from modules.info_retrieval import SportsRetrievalAgent, RetrievalBroker
from modules.ans_generator import GenerationInput, ResultGenerator
from modules.feedback_handler import FeedbackData, FeedbackHandler
from config.prompt_utils import prompt_loader
from infrastructure.message_broker import MessageBroker
from infrastructure.shared_schemas import RetrievalRequest, IntentExtractionResult, RetrievalResult
from knowledge_base.loader_RAG import KnowledgeLoader
import os
import sys
import time
import uuid
import json
import nltk
import threading
from threading import Lock
import logging
from datetime import datetime
from queue import Queue
import redis
from config.settings import config, Env
from typing import Dict, Any, Union, Optional
from camel.agents import ChatAgent
from camel.configs import QwenConfig
from camel.models import ModelFactory
from camel.types import ModelPlatformType, RoleType
from camel.messages import BaseMessage

app = Flask(__name__)


# 创建连接池时指定正确的主机和端口
config.redis_pool = redis.ConnectionPool(
    host='localhost',  # Redis 服务器地址
    port=6379,         # Redis 服务器端口
    db=0,              # 使用的数据库编号
    max_connections=10 # 最大连接数
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('sports_agent_main')

DEBUG_MODE = False

@app.route('/test', methods=['GET'])
def test_connection():
    """用于前端测试连接的后端接口"""
    return jsonify({
        "status": "success",
        "message": "后端服务正常运行",
        "timestamp": datetime.now().isoformat(),
        "active_modules": {
            "redis": check_redis(),          # 需要定义检查函数
            "knowledge_base": check_kb()     # 需要定义检查函数
        }
    })

# 添加辅助检查函数（放在同一文件中）
def check_redis():
    try:
        r = redis.Redis(connection_pool=config.redis_pool)
        return r.ping()
    except:
        return False

def check_kb():
    return os.path.exists(config.KNOWLEDGE_BASE_PATH)

# 为处理异步任务创建线程和队列
task_queue = Queue()
# 存储每个会话的未来结果的字典
session_results: Dict[str, Any] = {}
# 用于保护对 session_results 的访问
session_lock = Lock()

def init_nltk():
    try:
        # 改为使用当前工作目录下的nltk_data
        nltk_data_path = os.path.join(os.getcwd(), "nltk_data")
        os.makedirs(nltk_data_path, exist_ok=True)
        nltk.data.path.append(nltk_data_path)
        
        # 检查并下载必要数据
        required_data = ['punkt', 'averaged_perceptron_tagger']
        for data in required_data:
            try:
                nltk.data.find(f'tokenizers/{data}')
            except LookupError:
                nltk.download(data, download_dir=nltk_data_path, quiet=True)
                
    except Exception as e:
        logger.error(f"NLTK初始化降级处理: {str(e)}")
        # 回退到临时目录
        import tempfile
        nltk.data.path.append(tempfile.gettempdir())
        try:
            nltk.download('punkt', quiet=True)
            nltk.download('averaged_perceptron_tagger', quiet=True)
        except:
            logger.critical("NLTK初始化完全失败，部分功能将受限")
            
def init_system():
    knowledge_loader = KnowledgeLoader()
    
    # 显式加载知识库（如果 __init__ 没有自动加载）
    if not hasattr(knowledge_loader, 'documents') or len(knowledge_loader.documents) == 0:
        knowledge_loader._load_all_knowledge_files()
    
    return knowledge_loader

def init_components():
    
    
    redis_conn = redis.Redis(connection_pool=config.redis_pool)
    redis_conn.ping() # 测试Redis连接

    broker = MessageBroker()

    # 【修改】直接在这里初始化 ChatAgent，替代 create_sports_agent 函数的调用
    logger.info("初始化意图识别的 LLM 代理...")
    model_config = config.MODEL_CONFIGS["intent"]
    try:
        # 使用 ModelFactory.create，严格按照您提供的样例参数
        qwen_model = ModelFactory.create(
            model_type=model_config["model_name"], # 从 model_config 获取
            model_platform=ModelPlatformType.OPENAI_COMPATIBLE_MODEL, # 按照样例使用 OPENAI_COMPATIBLE_MODEL
            api_key=config.DASHSCOPE_API_KEY, # 从 config 获取
            url=config.DASHSCOPE_BASE_URL,    # 从 config 获取
            model_config_dict=QwenConfig(
                temperature=model_config.get("temperature", 0.7),
                max_tokens=model_config.get("max_tokens", 512),
                top_p=model_config.get("top_p", 0.3),
                stream=True
            ).as_dict() # 转换为字典
        )
        logger.info(f"Camel ChatAgent (意图识别) 初始化成功，模型: {model_config['model_name']}")

        # 创建系统消息，严格按照样例格式
        system_message_content = "你是一个专业的意图识别系统。" # 您样例中的 system_message_content
        system_message = BaseMessage(
            role_name="Intent Assistant", # 可以自定义一个合适的角色名
            role_type=RoleType.ASSISTANT,
            content=system_message_content, 
            meta_dict={ # 按照样例添加 meta_dict
                "module": "main_init_intent_agent",
                "intent": "intent_detection", # 表示此agent用于意图检测
                "timestamp": datetime.now().isoformat()
            }
        )

        # 创建 ChatAgent，严格按照样例格式
        sports_agent = ChatAgent(
            system_message=system_message,
            model=qwen_model
        )

    except Exception as e:
        logger.error(f"初始化 Camel ChatAgent 失败: {e}")
        raise

    extractor = IntentExtractor(sports_agent) # 将初始化好的 sports_agent 传递给 IntentExtractor
    knowledge_loader = init_system()
    retriever_agent = SportsRetrievalAgent(knowledge_loader)
    
    retrieval_broker = RetrievalBroker(knowledge_loader)
    retrieval_thread = threading.Thread(target=retrieval_broker.start_listening, daemon=True)
    retrieval_thread.start()
    logger.info("检索代理监听线程已启动。")

    generator = ResultGenerator(
        config_loader=config,
        prompt_loader=prompt_loader,
        logger=logging.getLogger('ResultGenerator'),
        redis_client=redis_conn
    )

    feedback_handler = FeedbackHandler(
        broker=broker,                  
        config_loader=config,          
        prompt_loader=prompt_loader,    
        logger=logging.getLogger('FeedbackHandler'), 
        redis_client=redis_conn         
    )

    return broker, extractor, retriever_agent, generator, feedback_handler

# 初始化所有组件
try:
    broker, intent_extractor, retriever_agent, generator, feedback_handler = init_components()
    logger.info("所有组件初始化完成。")
except Exception as e:
    logger.critical(f"组件初始化失败: {e}", exc_info=True)
    # sys.exit(1) # 退出应用如果初始化失败

# 工作线程函数
def worker():
    while True:
        try:
            session_id, user_input = task_queue.get()
            logger.info(f"Session {session_id}: 工作线程开始处理用户请求。")
            
            # 1. 意图识别
            logger.info(f"会话 {session_id}: 进行意图识别...")
            intent_result: IntentExtractionResult = intent_extractor.extract_intent(session_id, user_input)
            logger.info(f"会话 {session_id}: 意图识别完成，结果: {intent_result.intent}")
            
            retrieval_request = RetrievalRequest(
                    session_id=session_id,
                    user_query=user_input,
                    intent=intent_result.intent,
                    entities=intent_result.entities,
                    original_query=user_input,
                    context={"user_query": user_input}, # 传递用户原始查询作为上下文
                    use_web=config.WEB_SEARCH_ENABLED # 是否启用网络搜索
                )
            broker.publish_retrieval_request(retrieval_request)
            logger.info(f"会话 {session_id}: 已发布检索请求。等待结果...")

                # 等待检索结果，使用新的超时配置
            retrieved_data: Optional[RetrievalResult] = broker.listen_for_retrieval_result(
                    session_id, 
                    timeout=config.HYPER_PARAMS["retrieval"]["timeout"]
                )

            if not retrieved_data:
                logger.warning(f"会话 {session_id}: 等待检索结果超时。将使用默认错误消息。")
                retrieved_data = RetrievalResult(
                    session_id=session_id,
                    user_query=user_input,
                    intent=intent_result.intent,
                    entities=intent_result.entities,
                    original_query=user_input,
                    data={
                        "status": "error",
                        "message": "检索超时，未能获取到相关信息。",
                        "fallback": "请稍后重试或联系管理员"
                    },
                    media_assets={},
                    sources=[],
                    context={}
                )
                    # 缓存一个超时结果，避免前端一直等待
                broker.cache_result(session_id, retrieved_data) 
                    
            logger.info(f"会话 {session_id}: 检索完成，数据摘要: {str(retrieved_data.data)[:100]}...")


            # 3. 答案生成
            logger.info(f"会话 {session_id}: 开始生成答案...")
            # 确保 create_generation_input 传递了所有必要参数
            generation_input = create_generation_input(
                session_id, 
                intent_result.model_dump(),
                retrieved_data.model_dump()
            )
                
            # 【重要修复】直接调用生成器，而不是通过消息队列
            final_output = generator.generate_answer(generation_input)
                
            logger.info(f"会话 {session_id}: 答案生成完成。")

            # 4. 缓存最终结果
            broker.cache_result(session_id, final_output)
            logger.info(f"会话 {session_id}: 最终结果已缓存。")

        except Exception as e:
            logger.error(f"会话 {session_id}: 处理请求时发生错误: {e}", exc_info=True)
            # 确保即使出错也有一个结果返回给前端
            error_result = {
                "session_id": session_id,
                "answer": f"抱歉，处理您的请求时发生了内部错误: {e}",
                "intent": "error",
                "entities": {},
                "media": [],
                "feedback_token": str(uuid.uuid4()),
                "sources": [],
                "related_queries": []
            }
            broker.cache_result(session_id, error_result)
        finally:
            task_queue.task_done()
            logger.info(f"会话 {session_id}: 任务处理完成。")

# 核心映射，从用户的query生成LLM回答
def process_user_query(user_query: str, session_id: str = None) -> dict:
    """端到端处理用户查询的主函数"""
    # 1. 初始化
    session_id = session_id or str(uuid.uuid4())
    
    # 2. 意图识别
    intent_result = intent_extractor.extract_intent(session_id, user_query)
    
    # 3. 信息检索
    retrieval_request = RetrievalRequest(
        session_id=session_id,
        intent=intent_result.intent,
        entities=intent_result.entities,
        original_query=user_query
    )
    retrieved_data = retriever_agent.retrieve(retrieval_request)
    
    # 4. 生成答案
    generation_input = GenerationInput(
        session_id=session_id,
        user_query=user_query,
        intent=intent_result.intent,
        entities=intent_result.entities,
        retrieved_data=retrieved_data.data,
        media_assets=retrieved_data.media_assets if isinstance(retrieved_data.media_assets, dict) else {}, 
        context={"user_query": user_query}
    )
    final_output = generator.generate_answer(generation_input)
    
    # 5. 构造返回结果
    result = {
        "answer": final_output.answer,
        "intent": final_output.intent,
        "media": [item.model_dump() for item in final_output.media],
        "session_id": session_id
    }
    
    # 6. 仅在调试模式下添加额外信息
    if DEBUG_MODE:
        result["debug_info"] = {
            "intent": intent_result.model_dump(),
            "retrieval": retrieved_data.model_dump(),
            "generation_input": generation_input.model_dump()
        }
    
    return result

# 启动工作线程
worker_thread = threading.Thread(target=worker, daemon=True)
worker_thread.start()
logger.info("后台工作线程已启动。")

@app.route('/query', methods=['POST'])
def handle_query():
    try:
        user_input = request.json.get("query", "").strip()
        if not user_input:
            return jsonify({"error": "Empty query"}), 400
        
        # 调用主处理函数
        result = process_user_query(user_input)
        
        # 缓存结果（原逻辑保持不变）
        broker.cache_result(result["session_id"], result)
        
        return jsonify({
            "status": "success",
            "session_id": result["session_id"],
            "result_url": f"/results/{result['session_id']}"
        })
    except Exception as e:
        logger.error(f"处理失败: {e}", exc_info=True)
        return jsonify({
            "error": str(e),
            "intent": "error"
        }), 500


@app.route('/results/<session_id>')
def get_results(session_id: str):
    if result := broker.get_cached_result(session_id):
        return jsonify(result)
    return jsonify({"status": "pending"}), 202

def create_generation_input(session_id: str, intent_data: Dict[str, Any], retrieved_data: Dict[str, Any]) -> GenerationInput:
    intent = intent_data.get("intent", "unrecognized_intent")  
    entities = intent_data.get("entities", {})
    data = retrieved_data.get("data", {})
    context = retrieved_data.get("context", {})
    user_query = context.get("user_query", "未知用户查询")

    # 根据意图类型注入上下文
    if intent == "facility_query" and data.get("facility_info"):
        context["facility_info"] = data["facility_info"]
    
    elif intent == "event_query" and data.get("event_details"):
        context.update({
            "event_time": data["event_details"].get("time"),
            "event_location": data["event_details"].get("location")
        })
    
    elif intent == "course_info" and data.get("course"):
        context["course_schedule"] = data["course"].get("schedule")
    
    elif intent == "physical_test":
        context["test_standards"] = data.get("standards", {})
        # 体测特殊逻辑：合并用户身体数据
        if entities.get("height") and entities.get("weight"):
            context["bmi"] = calculate_bmi(entities["height"], entities["weight"])
    
    elif intent == "health_advice":
        context["health_goal"] = entities.get("goal", "general_fitness")
    
    elif intent == "extra_exercise":
        context["runner_data"] = data.get("running_records", [])
    
    elif intent == "feedback":
        context["feedback_subtype"] = classify_feedback(user_query)
        context["urgent"] = (context["feedback_subtype"] == "complaint")

    return GenerationInput(
        session_id=session_id,
        user_query=user_query,
        intent=intent,
        entities=entities,
        data=data,
        media_assets=retrieved_data.get("media_assets", {}),
        sources=retrieved_data.get("sources", []),
        context=context,
        height=entities.get("height"),
        weight=entities.get("weight"),
        goal=entities.get("goal")
    )

def calculate_bmi(height: float, weight: float) -> float:
    return round(weight / ((height / 100) ** 2), 1)

def classify_feedback(text: str) -> str:
    text = text.lower()
    complaint_keywords = ["投诉", "不满", "差评", "生气"]
    suggestion_keywords = ["建议", "希望", "可以", "应该"]
    
    if any(kw in text for kw in complaint_keywords):
        return "complaint"
    elif any(kw in text for kw in suggestion_keywords):
        return "suggestion"
    return "general"


@app.route('/feedback', methods=['POST'])
def submit_feedback():
    try:
        feedback_data = FeedbackData(**request.json)
        feedback_handler.handle_feedback(feedback_data)
        return jsonify({"message": "反馈已提交"}), 200
    except Exception as e:
        logger.error(f"提交反馈失败: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    init_nltk()
    # 启动 Flask 应用。关闭 reloader 避免多进程问题，正式使用时在这里退出 debug 模式
    app.run(host=config.HOST, port=config.PORT, debug=False, use_reloader=False)