import os
import re

def load_system_prompts(md_filename="AGENTS.md"):
    """
    AGENTS.md 파일을 파싱하여 토마토 전용 프롬프트와 메인 프롬프트를 추출합니다.
    """
    # 프로젝트 루트 디렉토리를 기준으로 경로 설정 (실행 환경에 맞게 조정 필요)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_path = os.path.join(base_dir, md_filename)
    
    if not os.path.exists(md_path):
        # 파일이 없을 경우 최소한의 안전(Fallback) 프롬프트 반환
        print(f"[Warning] {md_path} 파일을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
        return "", "질문에 답변해주세요.\n[사용자 질문]\n{query}\n[수집된 센서 데이터]\n{sensor_data_str}\n[추가 진단 정보]\n{diagnosis_str}\n[검색된 농업 지침]\n{docs_str}"

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # ### 4-1 블록 하단의 ```(코드블록) 안의 텍스트 추출
    tomato_match = re.search(r"### 4-1.*?```\n?(.*?)\n?```", content, re.DOTALL)
    tomato_prompt = tomato_match.group(1).strip() if tomato_match else ""

    # ### 4-2 블록 하단의 ```(코드블록) 안의 텍스트 추출
    main_match = re.search(r"### 4-2.*?```\n?(.*?)\n?```", content, re.DOTALL)
    main_prompt = main_match.group(1).strip() if main_match else ""

    return tomato_prompt, main_prompt