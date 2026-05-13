import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter

class SuperRAG:
    def __init__(self):
        # 使用效果更好的多语言模型
        print("📂 正在加载本地 Embedding 模型到内存...")
        self.model = SentenceTransformer('shibing624/text2vec-base-chinese')
        self.index = None
        self.documents = []
        # 分段器：把长文档切成 300 字左右的小块，方便 AI 阅读
        self.text_splitter = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50)

    def load_local_standards(self, file_path: str):
        """加载本地的评价标准文本"""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = self.text_splitter.split_text(content)
        self.add_to_index(chunks)
        print(f"📚 已缓存 {len(chunks)} 条教学标准片段到内存")

    def add_to_index(self, texts: list):
        self.documents.extend(texts)
        embeddings = self.model.encode(texts)
        
        dimension = embeddings.shape[1]
        if self.index is None:
            self.index = faiss.IndexFlatL2(dimension)
        
        self.index.add(np.array(embeddings).astype('float32'))

    def query(self, user_text: str, k=3):
        """搜索最匹配的教学建议"""
        if not self.index:
            return []
        query_vec = self.model.encode([user_text])
        _, indices = self.index.search(np.array(query_vec).astype('float32'), k)
        return [self.documents[i] for i in indices[0] if i != -1]

rag_engine = SuperRAG()