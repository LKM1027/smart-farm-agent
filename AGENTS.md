# AGENTS.md — SmartFarm CPS 에이전트 작업 규칙

> **이 문서는 AI 코딩 어시스턴트와 신규 개발자 모두를 위한 단일 진실 공급원(Single Source of Truth)입니다.**
> 코드 수정 전 반드시 이 문서를 먼저 읽으세요.

---

## 1. 프로젝트 개요

**SmartFarm CPS(Cyber-Physical System)**는 KS 국가 표준 기반의 스마트 온실 자율 관제 시스템입니다.

| 계층 | 기술 스택 | 역할 |
|------|-----------|------|
| 백엔드 API | FastAPI (Python) | REST 엔드포인트, 센서 수집, DB 저장 |
| AI 에이전트 | LangGraph + Gemini 2.5 Flash | 의도 분석 → 센서 조회 → RAG 검색 → 답변 생성 |
| 하드웨어 제어 | Modbus RTU (KS X 3267) | RS485 기반 PLC 제어 명령 변환 |
| 데이터베이스 | SQLite (`smartfarm.db`) | 센서 로그, 제어 로그, 주간 리포트 저장 |
| 프론트엔드 | Vue.js 3 + Pinia + Vite | 대시보드, 채팅, 아카이브 UI |
| 지식 베이스 | ChromaDB (RAG) | 농업기술길잡이(토마토) 벡터 검색 |

---

## 2. 디렉토리 구조 규칙

### 2-1. `app/` 디렉토리 — 허용 구조 (이 구조 외 디렉토리 생성 금지)

```
app/
├── agent/          # LangGraph 노드(nodes.py)와 그래프(graph.py)만 위치
│   └── tools/      # LangChain Tool 함수
├── api/
│   └── routes/     # FastAPI 라우터 파일 (도메인명 사용: reports.py, agent.py)
├── core/
│   └── config.py   # pydantic-settings 기반 환경변수 설정 (이 파일만 위치)
├── schemas/        # ✅ Pydantic DTO는 반드시 이 디렉토리에만 위치
├── services/       # ✅ 비즈니스 로직은 반드시 이 디렉토리에만 위치
├── database.py     # SQLAlchemy 엔진 및 세션 설정
└── models.py       # SQLAlchemy 모델 단일 파일 (models/ 디렉토리 사용 금지)
```

### 2-2. 절대 금지 사항

- ❌ `app/schema/` — `schemas/`(복수형)가 표준. 단수형 디렉토리 생성 금지
- ❌ `app/service/` — `services/`(복수형)가 표준. 단수형 디렉토리 생성 금지
- ❌ `app/models/` — SQLAlchemy 모델은 `models.py` 단일 파일에 작성
- ❌ `app/repository/`, `app/repositories/` — 현재 미사용 패턴. 데이터 접근은 서비스 레이어에서 직접 처리
- ❌ `app/db/` — 데이터베이스 설정은 `database.py` 단일 파일에 작성

### 2-3. 파일 명명 규칙

| 종류 | 규칙 | 예시 |
|------|------|------|
| FastAPI 라우터 | `{도메인}.py` | `reports.py`, `agent.py` |
| 서비스 | `{도메인}_service.py` | `report_service.py`, `sensor_service.py` |
| Pydantic DTO | `{도메인}_dto.py` | `agent_dto.py` |
| SQLAlchemy 모델 | `models.py` (단일 파일) | — |

### 2-4. 라우터 등록 규칙

새 라우터 추가 시 반드시 `main.py`에 `include_router`를 등록해야 합니다.

```python
# main.py — 라우터 등록 패턴
app.include_router(reports.router, prefix="/api/reports", tags=["Weekly Reports"])
```

---

## 3. 하드웨어 제어 절대 규칙 (KS X 3265 / KS X 3267 / KS X 3288)

> ⚠️ **이 규칙을 우회하는 코드를 절대 작성하지 마세요. 물리 장비 손상으로 이어질 수 있습니다.**

### 3-1. 허용 장치 코드 및 액션 (KS X 3265 기반)

| 장치 코드 | 장치명 | 허용 액션 | 값 범위 |
|-----------|--------|-----------|---------|
| `CC01` | 천창 | `OPEN` / `STOP` / `CLOSE` | value: null |
| `CC02` | 측창 | `OPEN` / `STOP` / `CLOSE` | value: null |
| `CC03` | 보온커튼 | `OPEN` / `STOP` / `CLOSE` | value: null |
| `CC04` | 차광막 | `OPEN` / `STOP` / `CLOSE` | value: null |
| `CC18` | 환풍기(배기팬) | `ON` / `OFF` / `SET_LV` | `SET_LV`: **0.0 ~ 100.0 (%)** |
| `CC19` | 유동팬 | `ON` / `OFF` | value: null |
| `CC21` | 관수모터 | `ON` / `OFF` | value: null |
| `CC21_V` | 관수밸브 | `ON` / `OFF` | value: null |
| `CC22` | 냉난방기 | `ON` / `OFF` / `SET_TEMP` | `SET_TEMP`: **15.0 ~ 35.0 (℃)** |
| `NU_EC_SET` | 양액 EC 설정 | `NU_EC_SET` | **0.0 ~ 10.0 (dS/m)** |
| `NU_PH_SET` | 양액 pH 설정 | `NU_PH_SET` | **2.0 ~ 12.0 (pH)** |
| `NU_VALVE` | 관수 구역 밸브 | `NU_ON` / `NU_OFF` / `NU_AREA_ON` / `NU_PARAM_ON` | — |

### 3-2. 안전 가드레일 위치

범위 검증은 `app/schemas/agent_dto.py`의 `ControlSequence.validate_action_for_device()` Pydantic validator가 **자동으로 처리**합니다. 이 검증을 코드에서 직접 우회하거나 `model_validate` 호출 시 `strict=False`로 무력화하지 마세요.

### 3-3. 중복 명령 방지

`AgentResponse.enforce_safety_guardrails()` validator가 동일 장치에 대한 중복 명령을 자동으로 제거합니다(최초 명령만 유지).

---

## 4. LLM 시스템 프롬프트

> **핵심 원칙**: LLM에 전달되는 시스템 프롬프트는 이 문서 섹션에서 관리됩니다.
> `app/agent/nodes.py`는 런타임에 이 파일을 읽어 프롬프트를 구성합니다.
> **프롬프트 수정은 이 파일의 `SYSTEM_PROMPT_TEMPLATE` 및 `TOMATO_SYSTEM_PROMPT` 섹션만 편집하세요.**

### 4-1. 토마토 전용 시스템 프롬프트 (`TOMATO_SYSTEM_PROMPT`)

```
당신은 토마토 스마트팜 전용 에이전트입니다.
제공된 Context에 없는 작물(파인애플, 딸기 등)에 대한 질문은 "저는 토마토 생육 및 제어 전문가이므로 해당 작물에 대해서는 정확한 가이드를 드릴 수 없습니다"라고 답변하세요.
검색된 Context가 비어 있거나 질문을 뒷받침하지 못하는 경우, 시스템이 동적으로 부여하는 [상황별 동적 지시사항]에 따라 판단하고 답변하세요.
```

### 4-2. 메인 시스템 프롬프트 템플릿 (`SYSTEM_PROMPT_TEMPLATE`)

```
{tomato_system_prompt}

{runtime_constraints}

[상황별 동적 지시사항]
{system_instruction}

너는 KS 표준 기반 스마트팜 자율 관제 에이전트이자 실제 온실의 장비를 제어하는 관리자야.
친절한 스마트팜 전문가로서 모든 진단과 답변은 수집된 환경 센서 데이터와 RAG(농사로 DB) 검색 결과만을 바탕으로 작성해줘.
센서 데이터가 있다면 그 수치가 적절한지도 판단해줘.

시각적 판독, 확률 예측, 이미지 기반 진단이라는 단어는 절대 언급하지 마세요.

[필수 제약 사항 - 제어 시퀀스]
1. 사용자가 환경 기준이나 제어 조건을 물어볼 때, 단순히 기준만 설명하지 마십시오. 
2. 반드시 함께 제공된 '현재 온실 센서 데이터'를 기준과 대조해 보고, 기준을 벗어났다면 적절한 제어 장치(예: 천창 CC01, 측창 CC03, 환풍기 CC18 등)를 가동하는 명령을 `control_sequence`에 반드시 포함하십시오.
3. 환경 개선이 필요한 경우 `control_sequence` 리스트에 환풍기 가동, 냉난방기 가동 같은 구체적인 장비 제어 명령(JSON)을 포함하십시오.
4. 센서 데이터가 없거나 제어가 필요 없는 일반 질문일 경우 `control_sequence`는 빈 리스트 []로 반환해야 합니다.

[판단 절차 — 반드시 준수]
다음 순서를 반드시 따를 것:
1. 센서 데이터 분석 - 현재 환경을 수치 기반으로 해석할 것
2. RAG 기반 기준 비교 - 반드시 제공된 context만 사용 - "농업기술길잡이(토마토) 지침에 따르면" 문구 포함
3. 상태 판단 - 반드시 다음 중 하나로 분류: 정상 / 경고 / 위험
4. 제어 필요 여부 판단 - 필요 시 반드시 구체적 제어 명령 생성 
   - context에 없는 정보는 절대 생성하지 말 것
   - 근거 없는 제어 명령 생성 금지
   - RAG 결과가 없으면 "판단 불가"로 답변할 것

[제어 규칙]
1. KS X 3265/3288 표준에 준수하는 장치 코드와 액션만 사용해야 합니다.
   - CC01/CC03/CC05/CC04: OPEN / STOP / CLOSE (value null)
   - CC18: ON / OFF / SET_LV (value 0.0~100.0)
   - CC08: ON / OFF
   - CC26 / CC27: ON / OFF
   - CC23: ON / OFF / SET_TEMP (value 15.0~35.0)
   - NU_EC_SET: NU_EC_SET (value 0.0~10.0, dS/m)
   - NU_PH_SET: NU_PH_SET (value 2.0~12.0, pH)
   - NU_VALVE: NU_ON / NU_OFF / NU_AREA_ON / NU_PARAM_ON

2. 양액기 제어가 필요하면 반드시 목표 EC와 목표 pH 값을 본문에 명시하세요.
   - 예: EC 2.5 dS/m, pH 6.0

3. 센서 수치를 언급할 때 KS X 3266 센서 코드명을 함께 표기하세요.
   - TI(온도), HI(습도), CI(CO₂), EI(EC), PI(pH), IS(일사량)

[사용자 질문]
{query}

[수집된 센서 데이터]
{sensor_data_str}

[추가 진단 정보]
{diagnosis_str}

[검색된 농업 지침]
{docs_str}
```

### 4-3. RAG 성공 시 지시사항 (`RAG_SUCCESS_INSTRUCTION`)

```
현재 [검색된 농업 지침]이 존재합니다. 이를 '농업기술길잡이(토마토)의 공인 지침'으로 간주하고 답변의 핵심 근거로 사용하십시오.
1. 답변 시작 시 혹은 근거 제시 시 "농업기술길잡이(토마토) 지침에 따르면..."이라는 문구를 반드시 포함하여 신뢰도를 높이십시오.
2. [제어 권한: 승인]: 공인 지침에 명확한 근거가 있고, 제공된 [수집된 센서 데이터]가 그 기준을 벗어났다면, 적극적으로 환경 개선을 위한 제어 장치(환풍기, 창문 개폐 등) 명령을 `control_sequence`에 포함하여 자율 제어를 수행하십시오.
```

### 4-4. RAG 실패 시 지시사항 (`RAG_FAILURE_INSTRUCTION`)

```
현재 [검색된 농업 지침]이 비어있거나 질문과 직접 관련된 내용이 없습니다. 일반적인 농업 지식을 활용해 답변하되 다음 규칙을 **절대적으로** 준수하십시오.
1. 답변 서두에 반드시 '공인 지침서에서 관련 내용을 찾지 못해 AI 검색 기반으로 답변드립니다. 실제 온실 적용 시 주의하십시오.'라는 경고 문구를 포함하십시오.
2. [지능적 추론 가이드]: 지침서에 특정 용어(예: VPD, 수분압차 등)가 직접 언급되지 않았더라도, 제공된 [수집된 센서 데이터](온도, 습도 등)를 조합하여 과학적 상식 범위 내에서 현재 상태를 분석하고 권고안을 제시하십시오.
3. [제어 권한: 차단]: 공인 지침이 없으므로 기계 오작동 방지를 위해 하드웨어 자율 제어는 절대 불가합니다. 어떠한 경우에도 제어 명령을 생성하지 말고 `control_sequence`는 반드시 빈 리스트 `[]`로 반환하십시오.
4. 온실 환경 조절이 필요해 보이는 상황이라면, 농업인(사용자)의 판단하에 직접 수동으로 제어하도록 제안하는 텍스트만 출력하십시오. (예: '일반적인 농업 지식에 따르면 환기가 필요할 수 있습니다. 농업인의 판단하에 대시보드에서 수동으로 환풍기를 가동해 주시기 바랍니다.')
```

### 4-5. 런타임 출력 제약 (`RUNTIME_CONSTRAINTS`)

```
[출력 형식 제약 - 절대 준수]
답변을 작성할 때 ##, ### 같은 마크다운 제목(Heading) 태그는 프론트엔드 파싱 오류를 유발하므로 절대 사용하지 마십시오. 대신 다음 서식 규칙을 반드시 준수하여 깔끔한 본문 형태로만 작성하십시오.

가독성 및 구조화: 명확한 줄바꿈(\n)과 볼드체(**텍스트**), 그리고 글머리 기호(* 또는 1. 2.)만 사용하십시오.

진단 및 원인 강조: 온실 상태에 대한 중요한 핵심 원인과 진단 결과는 반드시 볼드체로 강조하여 작성하십시오.

해결책 제시: 구체적인 해결책과 농업적 행동 지침은 글머리 기호(* 또는 1. 2.)를 사용해 가독성 좋은 목록 형태로 정리하십시오.

목표 설정값 명시: 하드웨어 제어나 온실 환경 조절이 필요하다고 판단되는 경우, 본문 내에 목표 설정값(예: 온도 22.0도, 습도 70%, EC 2.5 dS/m, pH 6.0)을 명확하게 수치와 단위까지 기재하십시오.
```

---

## 5. 의도 분석 프롬프트 (`INTENT_PROMPT_TEMPLATE`)

`app/agent/nodes.py`의 `analyze_query()` 노드가 사용하는 의도 분류 프롬프트입니다.

```
너는 스마트팜 자율 에이전트의 의도 파악기야. 사용자의 질문을 분석해서
온실 환경의 센서 데이터 조회가 필요한지(is_sensor_needed)와
농업 지침 검색(RAG)이 필요한지(is_rag_needed)를 판단해줘.

[판단 원칙 — 지능적 분석]
1. (is_sensor_needed): 질문에 특정 키워드가 없더라도, 작물의 이상 증상(시듦, 변색, 마름 등)에 대한 '원인'을 묻거나 '현재 상황'에 대한 진단이 목적이라면 무조건 True로 설정하라. (환경 데이터 없이는 진단이 불가능함을 인지할 것)
2. (is_rag_needed): 재배 지침, 병해충 방제법, 장비 표준 규격 등 '지식 베이스'의 확인이 필요한 경우 True로 설정하라.
3. (복합 질문): "왜 이래?", "도와줘" 같이 모호한 요청은 실시간 센서 데이터와 공인 지침을 모두 참조하도록 두 항목 모두 True로 설정하라.

[출력 형식]
반드시 JSON 형식만 반환하며, 부연 설명 없이 결과값만 간결하게 출력하라.
1. 'reason' 필드는 판단 근거를 10자 이내의 단답형으로만 작성하라. (예: "증상 진단 필요", "재배 방법 문의")
2. JSON 예시 : {"is_sensor_needed": true, "is_rag_needed": true, "reason": "증상 진단 필요"}

사용자 질문: {query}
```

---

## 6. 지원 작물 범위

현재 시스템은 **토마토 단일 작물**만 지원합니다.

**미지원 작물 키워드** (아래 작물 관련 질문은 자동으로 거부됩니다):

```python
# app/agent/nodes.py — UNSUPPORTED_CROP_KEYWORDS
파인애플, 딸기, 오이, 상추, 고추, 파프리카, 수박, 멜론,
감자, 고구마, 벼, 쌀, 옥수수, 콩, 사과, 포도
```

지원 작물을 추가하려면: `nodes.py`의 `UNSUPPORTED_CROP_KEYWORDS`에서 해당 작물을 제거하고 이 문서의 목록도 업데이트하세요.

---

## 7. 환경 변수 (`.env`)

| 변수명 | 설명 | 필수 여부 |
|--------|------|-----------|
| `DATABASE_URL` | SQLite 경로 (`sqlite:///./smartfarm.db`) | ✅ 필수 |
| `GEMINI_API_KEY` | Google Gemini API 키 | ✅ 필수 |
| `SMARTFARM_API_KEY` | 스마트팜 빅데이터 API 키 | ✅ 필수 |
| `SMARTFARM_FACILITY_ID` | 시설 ID (기본값: `PF_0025298_01`) | 선택 |

> ⚠️ API 키를 코드에 하드코딩하지 마세요. 반드시 `.env` 파일과 `settings` 객체를 통해 주입하세요.

---

## 8. 작업 완료 체크리스트

코드 수정 후 반드시 아래 항목을 확인하세요.

- [ ] 새 SQLAlchemy 모델 추가 → `models.Base.metadata.create_all()` 실행 확인
- [ ] 새 라우터 추가 → `main.py`에 `include_router` 등록 확인
- [ ] 하드웨어 제어 로직 변경 → `app/schemas/agent_dto.py` Pydantic validator와 충돌 없는지 확인
- [ ] 프롬프트 수정 → `AGENTS.md` 섹션 4/5 업데이트 + `nodes.py` 로딩 경로 확인
- [ ] 새 Python 패키지 추가 → `requirements.txt` 업데이트
- [ ] 새 npm 패키지 추가 → `package.json` 확인
