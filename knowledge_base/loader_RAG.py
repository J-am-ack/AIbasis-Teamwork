# -*- coding: utf-8 -*-

import os
import json
import yaml
import logging
import numpy as np

import base64
from io import BytesIO
from PIL import Image
from langdetect import detect, DetectorFactory
# from sentence_transformers import SentenceTransformer
from config.settings import config
from camel.models import ModelFactory
from camel.types import ModelPlatformType, RoleType, EmbeddingModelType, StorageType 
from camel.loaders import UnstructuredIO, create_file_from_raw_bytes
from camel.retrievers import AutoRetriever, VectorRetriever
from camel.storages.vectordb_storages import QdrantStorage
from camel.embeddings import SentenceTransformerEncoder
from dashscope import TextEmbedding
from http import HTTPStatus # 用于检查dashscope返回的状态
from typing import Dict, List, Any, Optional
from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text

logger = logging.getLogger('knowledge_loader')

def get_image_dimensions(file_path: str) -> Dict[str, int]:
    """获取图片尺寸信息"""
    try:
        with Image.open(file_path) as img:
            return {
                "width": img.width,
                "height": img.height,
                "format": img.format
            }
    except Exception as e:
        logger.warning(f"获取图片尺寸失败: {file_path} - {str(e)}")
        return {"width": 0, "height": 0, "format": "unknown"}
    
# 确保语言检测结果一致性
DetectorFactory.seed = 0

'''
# 下载 e5-large-v2 嵌入模型
model = SentenceTransformer("intfloat/e5-large-v2")
model.save("./local_models/e5-large-v2")  # 保存到本地
'''

class KnowledgeLoader:
    def __init__(self):
        self.documents = {} 
        self.logger = logging.getLogger('knowledge_loader')
        # 确保目录存在
        os.makedirs(config.KNOWLEDGE_BASE_PATH, exist_ok=True)
        
        # 1. Loaders 初始化
        self.uio = UnstructuredIO()

        # 2. Embeddings 初始化
        '''
        self.embedding_model = SentenceTransformerEncoder(
            model_name=config.MODEL_CONFIGS["embedding"]
        )
        '''
        self.embedding_model = SentenceTransformerEncoder(model_name='./Models/m3e-base')

        # 3. Storages 初始化
        self.vector_storage = QdrantStorage(
            vector_dim=self.embedding_model.get_output_dim(),
            path="./rag_storage",
            collection_name="北京大学体育信息"
        )

        # 4. Retrievers 初始化
        self.retriever = AutoRetriever(
            embedding_model=self.embedding_model,
            vector_storage_local_path="./rag_storage",
            storage_type=StorageType.QDRANT
        )

        self._load_all_knowledge_files()

        # 初始化媒体资源路径
        self.media_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__), 
            '../../media_assets'
        ))
        if os.path.exists(self.media_path):
            self.logger.info(f"加载媒体资源目录: {self.media_path}")
            self._load_all_knowledge_files(self.media_path)  # 额外加载媒体

    '''    
    def _init_retriever(self) -> AutoRetriever:
        """
        初始化CAMEL AutoRetriever，使用DashScope嵌入模型。
        CAMEL的AutoRetriever会根据embedding_model参数自动创建嵌入模型。
        重要的：确保DASHSCOPE_API_KEY和DASHSCOPE_BASE_URL在环境变量中已设置，
        CAMEL会通过其内部逻辑读取这些变量。
        """
        try:
            # 检查 DashScope API Key 是否已设置
            if not config.DASHSCOPE_API_KEY:
                self.logger.error("未找到 DASHSCOPE_API_KEY。请在 .env 文件中设置。")
                raise ValueError("DASHSCOPE_API_KEY is not set.")
            
            # AutoRetriever 会自动处理 embedding 模型的初始化
            # 这里我们只需要提供模型名称，它会查找对应的配置和环境变量
            retriever = AutoRetriever(
                embedding_model=config.EMBEDDING_CONFIG["model_name"], # 例如 "text-embedding-v2"
                vector_storage_local_path=config.FAISS_INDEX_PATH,
            )
            self.logger.info("AutoRetriever 初始化成功。")
            return retriever
        except Exception as e:
            self.logger.error(f"AutoRetriever 初始化失败: {e}", exc_info=True)
            raise
    '''

    def _load_all_knowledge_files(self, base_path=None):
        """加载指定目录下的所有知识文件"""
        if base_path is None:
            base_path = config.KNOWLEDGE_BASE_PATH
    
        self.logger.info(f"开始加载知识库目录: {base_path}")
        for root, _, files in os.walk(base_path):
            for file in files:
                file_path = os.path.join(root, file)
                self._load_single_file(file_path)
    
    def _init_logger(self):
        """初始化日志记录器"""
        logger = logging.getLogger('knowledge_loader')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(handler)
        return logger

    def _load_single_file(self, file_path: str):        
        """加载单个文件（支持图片+描述JSON）"""

        try:
            # 跳过系统文件和隐藏文件
            if os.path.basename(file_path).startswith('.') or file_path.endswith('.pyc'):
                return None

            # 图片文件处理
            if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                # 读取图片文件
                with open(file_path, 'rb') as f:
                    base64_img = base64.b64encode(f.read()).decode('utf-8')
               
                # 查找对应的JSON描述文件
                json_path = os.path.splitext(file_path)[0] + '.json'
                if os.path.exists(json_path):
                    with open(json_path, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                else:
                    metadata = {
                        "description": os.path.splitext(os.path.basename(file_path))[0],
                        "source": file_path
                    }
                    self.logger.warning(f"图片缺少描述文件: {file_path}")

                return {
                    "doc_id": f"img_{os.path.basename(file_path)}",
                    "content": base64_img,
                    "metadata": {
                        "type": "image",
                        **metadata,
                        "embedding": None  # 可后续填充
                    }
                }
        
            doc_id = os.path.basename(file_path)

            if file_path.lower().endswith('.pdf'):
                # 方案1：使用PyPDF2
                try:
                    with open(file_path, 'rb') as f:
                        reader = PdfReader(f)
                        chunks = [{
                            "text": page.extract_text(),
                            "metadata": {"source": file_path, "page": i}
                        } for i, page in enumerate(reader.pages)]
                except Exception as e:
                    self.logger.warning(f"PyPDF2解析失败，尝试pdfminer: {e}")        
                                
                    # 方案2：使用pdfminer
                    text = extract_text(file_path)
                    chunks = [{"text": text, "metadata": {"source": file_path}}]
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                chunks = [{"text": content, "metadata": {"source": file_path}}]

            processed_docs = []
            for i, chunk in enumerate(chunks):
                processed_docs.append({
                    "doc_id": f"{doc_id}-{i}",
                    "content": chunk["text"] if isinstance(chunk, dict) else str(chunk),
                    "metadata": {
                        "source": file_path,
                        "chunk_id": f"{doc_id}-{i}",
                        **chunk.get("metadata", {})
                    }
                })

            if processed_docs:
                self.documents[doc_id] = {
                    "raw_content": processed_docs,
                    "processed_chunks": processed_docs
                }
                self.logger.info(f"成功加载文件: {file_path}")
                
                # 存储到向量数据库
                self._store_to_vector_db(processed_docs)

            print(f"正在加载文件: {file_path}")  # 确认文件路径正确
            if file_path.endswith('.pdf'):
                text = extract_text(file_path)
                print(f"提取到{len(text)}字符")  # 检查内容是否正常 

        except Exception as e:
            self.logger.error(f"文件加载失败 {file_path}: {str(e)}")
            return None
    
    '''
    def _build_faiss_index(self):
        """构建FAISS索引。"""
        all_chunks = []
        for doc_info in self.documents.values():
            all_chunks.extend(doc_info["processed_chunks"])

        if not all_chunks:
            self.logger.warning("没有文档可供构建索引。FAISS索引将为空。")
            self.retriever.index = None # 确保检索器索引为空
            return
        
        self.logger.info(f"正在为 {len(all_chunks)} 个文档块生成嵌入并构建索引...")

        # 使用 AutoRetriever 的方法来生成嵌入并构建索引
        # AutoRetriever.create_index 会负责生成嵌入和创建 FAISS 索引
        self.retriever.create_index(
            documents=[chunk["content"] for chunk in all_chunks],
            document_metadatas=[chunk["metadata"] for chunk in all_chunks],
            vector_storage_local_path=config.FAISS_INDEX_PATH,
            overwrite=True # 每次启动都重新构建，或者根据需求改为 False
        )
        self.logger.info("FAISS索引已成功构建并保存。")
    '''   

    def _store_to_vector_db(self, chunks: List[Dict[str, Any]]):
        """存储处理后的块到向量数据库"""
        try:
            documents = [chunk["content"] for chunk in chunks]
            metadatas = [chunk["metadata"] for chunk in chunks]
    
            # 检查 retriever 是否初始化
            if not hasattr(self, 'retriever'):
                raise AttributeError("Retriever not initialized. Call _init_retriever() first.")
    
            # 调用检索器存储数据
            results = self.retriever.run_vector_retriever(
                query="dummy_query",
                contents=documents,
                top_k=len(documents),
                similarity_threshold=0.0,
                return_detailed_info=True
            )
    
            # 修改日志记录方式，安全处理结果
            self.logger.info(f"已存储 {len(documents)} 个文档块到向量数据库")
            for i, res in enumerate(results):
                log_content = f"存储内容索引: {i}"
                if isinstance(res, dict):
                    log_content += f", 文本长度: {len(res.get('text', ''))}, 元数据: {res.get('metadata', {})}"
                elif isinstance(res, str):
                    log_content += f", 文本: {res[:50]}..."  # 只显示前50字符
                self.logger.debug(log_content)
            
        except Exception as e:
            self.logger.error(f"存储到向量数据库失败: {e}", exc_info=True)
            raise

    def retrieve(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        try:
            results = self.retriever.run_vector_retriever(
                query=query,
                contents=list(self.documents.keys()),
                top_k=kwargs.get('top_k', 5),
                similarity_threshold=kwargs.get('min_score', 0.35)
            )
    
            formatted_results = []
            for r in results:
                if isinstance(r, dict):
                    content = r.get('content', r.get('text', ''))
                    formatted_results.append({
                        "content": content,
                        "metadata": {
                            "source": r.get('content_path', 'unknown'),
                            "similarity": r.get('similarity_score', 0.0)
                        }
                    })
                elif isinstance(r, str):
                    formatted_results.append({
                        "content": r,
                        "metadata": {
                            "source": "unknown",
                            "similarity": 0.0
                        }
                    })
                
            return formatted_results
        
        except Exception as e:
            self.logger.error(f"检索失败: {e}")
            return []

    def advanced_retrieve(self, query: str, strategy: str = "hybrid") -> Dict:
        """新增高级检索方法（可选）"""
        return self.retriever.retrieve(
            query=query,
            strategy=strategy  # 支持auto/vector/keyword/hybrid
    )
    
    # 保持原有接口方法
    get_document_content = lambda self, doc_id: self.documents.get(doc_id, {}).get("raw_content")