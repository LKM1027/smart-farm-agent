import os
import shutil

from langchain_community.document_loaders import PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma


PDF_PATH = "data/pdfs/농사로_농업기술길잡이_토마토.pdf"
PERSIST_DIR = "./chroma_db"


def clean_text(text: str) -> str:
    """
    PDF 깨짐 최소화 + embedding 품질 개선용 최소 전처리
    """
    text = text.replace("\n", " ")
    text = " ".join(text.split())

    # 표/숫자 노이즈 최소화 (과도 제거는 금지)
    text = text.replace("  ", " ")

    return text


def main():
    print(f"[LOAD] {PDF_PATH}")

    if not os.path.exists(PDF_PATH):
        print("❌ PDF 파일 없음")
        return

    # 1. PDF 로드
    loader = PyMuPDFLoader(PDF_PATH)
    documents = loader.load()
    print(f"✅ pages: {len(documents)}")

    # 2. 전처리 + passage prefix + 메타데이터 정제
    cleaned_docs = []
    for i, doc in enumerate(documents):
        text = clean_text(doc.page_content)

        # ✅ 핵심: E5 passage prefix
        text = "passage: " + text

        doc.page_content = text
        doc.metadata = {
            "page": i + 1,
            "source": "농업기술길잡이_토마토",
        }
        cleaned_docs.append(doc)

    # 3. 한국어 기준 chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=[
            "\n\n",
            "\n",
            "다.",
            "다 ",
            ". ",
            " ",
        ],
    )

    docs = splitter.split_documents(cleaned_docs)
    print(f"✅ chunks: {len(docs)}")

    # 4. 임베딩 모델 (검색용 최적)
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        model_kwargs={"device": "cpu"},
        encode_kwargs={},  # normalize 금지
    )

    # 5. 기존 DB 삭제 (중요)
    if os.path.exists(PERSIST_DIR):
        shutil.rmtree(PERSIST_DIR)
        print("🧹 기존 DB 삭제")

    # 6. Chroma 저장
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=PERSIST_DIR,
    )

    print("🎉 완료: Chroma DB 구축됨")

    # ✅ 디버깅용 (반드시 한 번 확인)
    test_query = "query: 토마토 적정 온도는?"
    results = vectorstore.similarity_search_with_score(test_query, k=5)

    print("\n[DEBUG] similarity test")
    for i, (doc, score) in enumerate(results):
        print(f"{i+1}. score={score:.4f}")
        print(doc.page_content[:120])
        print("-" * 50)


if __name__ == "__main__":
    main()
