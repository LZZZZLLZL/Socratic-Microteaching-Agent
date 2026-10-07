# ==========================================================================
# 学思践悟 — 课程标准 RAG 检索引擎
#
# 设计要点：
#   1. 离线优先：向量模型已缓存时直接本地加载，不再联网做版本校验，
#      避免在无网络（如评委演示现场）时卡住甚至启动失败
#   2. 优雅降级：向量模型缺失或加载失败时，自动退化为关键词检索，
#      保证课标检索功能始终可用，进程不会因缺模型而崩溃
#   3. 懒加载：首次检索时才初始化向量模型，缩短后端启动时间
# ==========================================================================

import os
import re
from typing import List, Optional

# 设备内存不足或驱动异常时，避免 sentence-transformers 直接崩溃
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# 关键：禁用联网检查，已缓存的模型直接离线加载
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    import faiss  # type: ignore
    _FAISS_AVAILABLE = True
except Exception:  # noqa: BLE001
    faiss = None
    _FAISS_AVAILABLE = False
    print("[RAG] faiss 不可用，向量检索将退化为关键词检索")

try:
    from sentence_transformers import SentenceTransformer  # type: ignore
    _ST_AVAILABLE = True
except Exception:  # noqa: BLE001
    SentenceTransformer = None
    _ST_AVAILABLE = False
    print("[RAG] sentence-transformers 不可用，向量检索将退化为关键词检索")

EMBEDDING_MODEL = "shibing624/text2vec-base-chinese"


class SuperRAG:
    """课程标准检索：向量检索优先，关键词检索兜底"""

    def __init__(self):
        self.index = None
        self.documents: List[str] = []
        self._dedupe_keys: set = set()  # 已收录内容的归一化键，用于去重
        self.model = None
        self._model_tried = False
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

    # ------------------------------------------------------------------
    # 向量模型懒加载
    # ------------------------------------------------------------------
    def _ensure_model(self) -> bool:
        """确保向量模型可用，返回是否成功"""
        if self.model is not None:
            return True
        if self._model_tried:
            return False
        self._model_tried = True

        if not (_ST_AVAILABLE and _FAISS_AVAILABLE):
            return False

        try:
            print(f"[RAG] 加载向量模型 {EMBEDDING_MODEL} …")
            self.model = SentenceTransformer(EMBEDDING_MODEL, local_files_only=True)
            print("[RAG] 向量模型加载完成")
            return True
        except Exception as e:  # noqa: BLE001
            # 缓存缺失或网络不可达时，退化为关键词检索
            print(f"[RAG] 向量模型加载失败，改用关键词检索: {e}")
            self.model = None
            return False

    # ------------------------------------------------------------------
    # 建库
    # ------------------------------------------------------------------
    def load_local_standards(self, file_path: str):
        """加载本地课程标准文本并建立索引"""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        chunks = [c for c in self.text_splitter.split_text(content) if c.strip()]
        self.add_to_index(chunks)
        print(f"[RAG] 已缓存 {len(chunks)} 条教学标准片段（库内共 {len(self.documents)} 条）")

    def add_to_index(self, texts: List[str]):
        """加入索引；重复内容会被跳过，避免同一段课标被检索命中多次"""
        if not texts:
            return

        # 全局去重：与已有 documents 比对，只加入新内容
        existing = set(self._dedupe_keys)
        fresh: List[str] = []

        for t in texts:
            key = self._norm_key(t)
            if not key or key in existing:
                continue
            existing.add(key)
            fresh.append(t)
            self._dedupe_keys.add(key)

        if not fresh:
            return

        self.documents.extend(fresh)
        # 向量索引在首次检索时按需构建（见 _build_index）
        self.index = None

    @staticmethod
    def _norm_key(text: str) -> str:
        """把文本归一化为用于去重的键（忽略标点与空白）"""
        return re.sub(r"[\s，。！？；：、,.!?;:（）()《》“”\"']", "", text or "")

    def _build_index(self):
        """为所有 documents 构建向量索引"""
        if not self.documents or not self._ensure_model():
            return
        try:
            embeddings = self.model.encode(self.documents, show_progress_bar=False)
            embeddings = np.array(embeddings).astype("float32")
            dimension = embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(embeddings)
            print(f"[RAG] 向量索引构建完成（{len(self.documents)} 条）")
        except Exception as e:  # noqa: BLE001
            print(f"[RAG] 向量索引构建失败，改用关键词检索: {e}")
            self.index = None

    # ------------------------------------------------------------------
    # 检索
    # ------------------------------------------------------------------
    def query(self, user_text: str, k: int = 3) -> List[str]:
        """检索最匹配的课程标准片段（结果已去重，不会返回重复条目）"""
        if not self.documents:
            return []

        hits: List[str] = []

        # 1) 向量检索
        if self.index is None:
            self._build_index()

        if self.index is not None and self.model is not None:
            try:
                query_vec = self.model.encode([user_text], show_progress_bar=False)
                query_vec = np.array(query_vec).astype("float32")
                # 多取一些候选，去重后仍能凑够 k 条
                fetch = min(max(k * 3, k), len(self.documents))
                _, indices = self.index.search(query_vec, fetch)
                hits = [self.documents[i] for i in indices[0] if 0 <= i < len(self.documents)]
            except Exception as e:  # noqa: BLE001
                print(f"[RAG] 向量检索失败，改用关键词检索: {e}")
                hits = []

        # 2) 关键词检索兜底
        if not hits:
            hits = self._keyword_search(user_text, max(k * 3, k))

        return self._dedupe(hits)[:k]

    @staticmethod
    def _dedupe(items: List[str]) -> List[str]:
        """
        去除重复与高度重合的检索结果。

        重复来源有两处：
          1. 向量索引里可能同时存在内容相同的 chunk（多次 load 过标准文件）
          2. 相邻 chunk 有 50 字重叠，检索时会被同时命中

        这里用「归一化后的正文」做精确去重，再用前缀包含关系过滤
        高度重合的相邻片段，避免同一段课标在结果里出现两次。
        """
        seen: set = set()
        unique: List[str] = []

        for raw in items:
            if not raw:
                continue
            # 归一化：去掉标点与空白后再比较，容忍细微格式差异
            key = re.sub(r"[\s，。！？；：、,.!?;:（）()《》“”\"']", "", raw)

            if not key or key in seen:
                continue

            # 若与已收录条目高度重合（一条包含另一条），跳过
            if any(key in s or s in key for s in seen if len(s) > 20):
                continue

            seen.add(key)
            unique.append(raw)

        return unique

    def _keyword_search(self, user_text: str, k: int) -> List[str]:
        """基于中文字符重合度的朴素关键词检索"""
        query_chars = set(re.findall(r"[\u4e00-\u9fff]", user_text or ""))
        if not query_chars:
            return self.documents[:k]

        scored = []
        for doc in self.documents:
            doc_chars = set(re.findall(r"[\u4e00-\u9fff]", doc))
            if not doc_chars:
                continue
            overlap = len(query_chars & doc_chars)
            # 归一化，避免长文本天然占优
            score = overlap / (len(query_chars) ** 0.5)
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [doc for _, doc in scored[:k]]

    def query_related_standard(self, user_text: str, top_k: int = 2) -> List[str]:
        """供 main.py 调用的课标检索"""
        return self.query(user_text, k=top_k)


rag_engine = SuperRAG()
