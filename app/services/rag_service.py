import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

class RagService:
    SEARCH_K = 5
    MAX_DISTANCE = 0.45  # Chroma 기본 L2 거리 기준 (작을수록 유사함, 필요에 따라 수치 조절)

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="intfloat/multilingual-e5-large",
            model_kwargs={"device": "cpu"},
            encode_kwargs={},
        )

        self.persist_directory = "./chroma_db"

        if os.path.exists(self.persist_directory):
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
            )
        else:
            print("❌ ChromaDB 없음")
            self.vectorstore = None

    def retrieve_docs(self, query: str):
        if self.vectorstore is None:
            return []

        query = f"query: {query}"

        results = self.vectorstore.similarity_search_with_score(
            query, k=self.SEARCH_K
        )

        filtered_docs = []

        for doc, score in results:
            print(f"[RAG] L2 distance={score:.4f}")

            # ✅ L2 거리는 낮을수록 좋으므로 작거나 같을 때만 통과
            if score <= self.MAX_DISTANCE:
                filtered_docs.append({
                    "content": doc.page_content,
                    "metadata": doc.metadata
                })

        if not filtered_docs:
            return []

        return filtered_docs