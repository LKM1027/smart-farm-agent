import os
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

def test_chroma_db():
    print("1. 임베딩 모델 로드 중...")
    embeddings = HuggingFaceEmbeddings(
        model_name="intfloat/multilingual-e5-large",
        model_kwargs={"device": "cpu"},
        encode_kwargs={},
    )

    db_path = "./chroma_db"
    if not os.path.exists(db_path):
        # 만약 app 디렉토리 내부에서 실행할 경우를 대비해 상위 디렉토리도 확인
        db_path = "../chroma_db"
        if not os.path.exists(db_path):
            print(f"❌ 오류: '{db_path}' 폴더가 존재하지 않습니다. DB 생성이 안 된 것 같습니다.")
            return

    print(f"2. ChromaDB 연결 중... ({db_path})")
    vectorstore = Chroma(
        persist_directory=db_path,
        embedding_function=embeddings
    )

    # 테스트할 질문 (E5 모델은 검색 시 'query: ' 접두사 필수)
    raw_query = "토마토의 적정 온도는 어떻게 되나요?"
    query = f"query: {raw_query}"
    print(f"\n🔍 검색어: '{query}'")
    
    # similarity_search_with_score는 거리를 반환 (L2 거리 기준 낮을수록 유사)
    try:
        results = vectorstore.similarity_search_with_score(query, k=5)
        
        if not results:
            print("❌ DB에 저장된 문서가 0건이거나, 검색 결과가 없습니다.")
            return

        print("\n=== 📊 검색 결과 및 유사도 점수 (L2 Distance) ===")
        print("💡 점수가 낮을수록(0에 가까울수록) 더 유사한 문서입니다.")
        for i, (doc, score) in enumerate(results):
            print(f"[{i+1}위] L2 Distance 점수: {score:.4f}")
            
            preview = doc.page_content[:150].replace('\n', ' ')
            print(f"문서 내용 (앞부분 150자): {preview}...")
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ 검색 중 에러 발생: {e}")

if __name__ == "__main__":
    test_chroma_db()