import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

def main():
    load_dotenv()
    
    pdf_path = "data/pdfs/농사로_농업기술길잡이_토마토.pdf"
    print(f"[{pdf_path}] 파일 로딩 중...")
    
    if not os.path.exists(pdf_path):
        print(f"오류: {pdf_path} 파일을 찾을 수 없습니다.")
        return

    # 1. 문서 로드
    loader = PyPDFLoader(pdf_path)
    documents = loader.load()
    
    # 2. 텍스트 분할
    print("문서 분할 중...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50
    )
    docs = text_splitter.split_documents(documents)
    print(f"총 {len(docs)}개의 문서 조각(chunk)으로 분할되었습니다.")
    
    # 3. 임베딩 및 벡터 DB 저장
    print("임베딩 생성 및 ChromaDB에 저장 중...")
    embeddings = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sroberta-multitask",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    persist_directory = "./chroma_db"
    
    # 로컬 모델은 API 제한이 없으므로 배치/대기 없이 한 번에 저장합니다.
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    print("완료! 지식 데이터가 ./chroma_db 폴더에 영구 저장되었습니다.")

if __name__ == "__main__":
    main()
