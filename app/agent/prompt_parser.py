import os
import re

def load_system_prompts(md_filename="AGENTS.md"):
    """
    AGENTS.md 파일을 파싱하여 토마토 전용 프롬프트, 메인 프롬프트, 
    상황별 지시사항 및 제약 사항들을 추출합니다.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    md_path = os.path.join(base_dir, md_filename)
    
    # 기본값 설정
    prompts = {
        "tomato_prompt": "",
        "main_prompt": "질문에 답변해주세요.\n[사용자 질문]\n{query}\n[수집된 센서 데이터]\n{sensor_data_str}\n[추가 진단 정보]\n{diagnosis_str}\n[검색된 농업 지침]\n{docs_str}",
        "rag_success_instruction": "",
        "rag_failure_instruction": "",
        "runtime_constraints": ""
    }

    if not os.path.exists(md_path):
        print(f"[Warning] {md_path} 파일을 찾을 수 없습니다. 기본 프롬프트를 사용합니다.")
        return prompts

    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 정규식을 사용해 섹션별 코드 블록 추출 함수
    def extract_section(section_num):
        match = re.search(fr"### {section_num}.*?```\n?(.*?)\n?```", content, re.DOTALL)
        return match.group(1).strip() if match else ""

    prompts["tomato_prompt"] = extract_section("4-1")
    prompts["main_prompt"] = extract_section("4-2")
    prompts["rag_success_instruction"] = extract_section("4-3")
    prompts["rag_failure_instruction"] = extract_section("4-4")
    prompts["runtime_constraints"] = extract_section("4-5")

    return prompts