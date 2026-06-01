import os

from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings


class RagService:
    SCORE_THRESHOLD = 0.7
    SEARCH_K = 3

    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(
            model_name="jhgan/ko-sroberta-multitask",
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        self.persist_directory = "./chroma_db"

        if os.path.exists(self.persist_directory):
            self.vectorstore = Chroma(
                persist_directory=self.persist_directory,
                embedding_function=self.embeddings,
            )
            self.retriever = self.vectorstore.as_retriever(
                search_type="similarity_score_threshold",
                search_kwargs={
                    "score_threshold": self.SCORE_THRESHOLD,
                    "k": self.SEARCH_K,
                },
            )
        else:
            print(
                "Warning: ChromaDB가 존재하지 않습니다. "
                "ingest.py를 먼저 실행하여 지식 베이스를 구축해주세요."
            )
            self.vectorstore = None
            self.retriever = None

    def retrieve_docs(self, query: str) -> list[str]:
        """
        Return only documents whose similarity score clears the safety threshold.
        If no document reaches 0.7, this returns an empty list.
        """
        if self.retriever is None:
            return []

        docs = self.retriever.invoke(query)
        return [doc.page_content for doc in docs]
