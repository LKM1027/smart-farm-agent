import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from app.core.config import settings

class RagService:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="jhgan/ko-sroberta-multitask",
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        self.persist_directory = "./chroma_db"
        
        # 구축된 ChromaDB 로드
        if os.path.exists(self.persist_directory):
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings
            )
        else:
            print("Warning: ChromaDB가 존재하지 않습니다. ingest.py를 먼저 실행하여 지식 베이스를 구축해주세요.")
            self.vectorstore = None

    def retrieve_docs(self, query: str) -> list[str]:
        """
        주어진 질의를 기반으로 관련된 농업 지식 문서를 검색합니다.
        가장 유사도가 높은 상위 3개의 문서 조각을 반환합니다.
        """
        if self.vectorstore is None:
            return []
            
        # 질의와 가장 유사한 문서 3개(k=3) 검색
        docs = self.vectorstore.similarity_search(query, k=3)
        
        # Document 객체에서 텍스트(page_content)만 추출하여 리스트로 반환
        return [doc.page_content for doc in docs]
