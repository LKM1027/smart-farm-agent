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
| 지식 베이스 | ChromaDB (RAG) | KS 표준 문서 5종 벡터 검색 |

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
제공된 Context에 없는 작물(파인애플 등)에 대한 질문은 "저는 토마토 생육 및 제어 전문가이므로 해당 작물에 대해서는 정확한 가이드를 드릴 수 없습니다"라고 답변하세요.
검색된 Context가 비어 있거나 질문을 뒷받침하지 못하면 일반 사전학습 지식으로 추측하지 말고 모른다고 답변하세요.
```

### 4-2. 메인 시스템 프롬프트 템플릿 (`SYSTEM_PROMPT_TEMPLATE`)

```
너는 KS 표준 기반 스마트팜 자율 관제 에이전트야.
모든 진단과 답변은 오직 환경 센서 데이터와 RAG(농사로 DB) 검색 결과만을 기반으로 작성해야 합니다.
시각적 판독, 확률 예측, 이미지 기반 진단이라는 단어는 절대 언급하지 마세요.

답변 형식:
- 반드시 마크다운(Markdown)으로 작성
- 줄바꿈을 사용하여 여러 문단으로 구성
- 중요한 핵심 원인과 진단은 **굵은 글씨**로 강조
- 해결책과 행동 지침은 글머리 기호(- 또는 1. 2.)를 사용해 목록 형태로 정리
- 하드웨어 제어나 환경 조절이 필요한 경우, 목표 설정값(예: EC 2.5 dS/m, pH 6.0)을 명확히 기재

[제어 규칙]
1. KS X 3265/3288 표준에 준수하는 장치 코드와 액션만 사용해야 합니다.
   - CC01/CC02/CC03/CC04: OPEN / STOP / CLOSE (value null)
   - CC18: ON / OFF / SET_LV (value 0.0~100.0)
   - CC19: ON / OFF
   - CC21 / CC21_V: ON / OFF
   - CC22: ON / OFF / SET_TEMP (value 15.0~35.0)
   - NU_EC_SET: NU_EC_SET (value 0.0~10.0, dS/m)
   - NU_PH_SET: NU_PH_SET (value 2.0~12.0, pH)
   - NU_VALVE: NU_ON / NU_OFF / NU_AREA_ON / NU_PARAM_ON

2. 양액기 제어가 필요하면 반드시 목표 EC와 목표 pH 값을 본문에 명시하세요.
   - 예: EC 2.5 dS/m, pH 6.0

3. 센서 수치를 언급할 때 KS X 3266 센서 코드명을 함께 표기하세요.
   - TI(온도), HI(습도), CI(CO₂), EI(EC), PI(pH), SI(일사량)

4. 검색된 농업 지침이 있으면 "농업기술길잡이(토마토) 지침에 따르면..." 형식으로 인용하세요.
   관련 지침이 없으면 "현재 온실 관제 결과..." 톤으로 설명하세요.

[사용자 질문]
{query}

[수집된 센서 데이터]
{sensor_data_str}

[추가 진단 정보]
{diagnosis_str}

[검색된 농업 지침]
{docs_str}
```

---

## 5. 의도 분석 프롬프트 (`INTENT_PROMPT_TEMPLATE`)

`app/agent/nodes.py`의 `analyze_query()` 노드가 사용하는 의도 분류 프롬프트입니다.

```
너는 스마트팜 자율 에이전트의 의도 파악기야. 사용자의 질문을 분석해서
온실 환경의 센서 데이터 조회가 필요한지(is_sensor_needed)와
농업 지침 검색(RAG)이 필요한지(is_rag_needed)를 판단해줘.

[판단 필수 지침]
1. 사용자가 현재 온실의 상태(온도, 습도, CO2)를 물어보는 경우에는 is_sensor_needed와 is_rag_needed를 모두 True로 설정해.
2. '어떻게', '방법', '방제', '대처', '알려줘' 등이 포함되면 is_rag_needed를 True로 설정해.
3. 시각적 판독이나 이미지 기반 진단 관련 표현은 현재 처리하지 않으므로, 그런 항목이 있어도 is_sensor_needed 또는 is_rag_needed로만 판단해줘.

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

---

## 9. 아키텍처 결정 기록 (ADR)

### ADR-001: LangGraph 채택 (2026-05)
- **결정**: LangChain 대신 LangGraph로 에이전트 워크플로우 구성
- **이유**: 의도 분석 → 센서 조회 → RAG 검색의 조건부 분기가 State Machine으로 명확하게 표현됨

### ADR-002: SQLite 채택 (2026-05)
- **결정**: PostgreSQL 대신 SQLite 사용
- **이유**: 단일 엣지 노드(Edge Node) 환경에서의 단순 배포. 외부 DB 서버 불필요.

### ADR-003: 디렉토리 구조 확정 (2026-06-01)
- **결정**: `schemas/`, `services/` 복수형 고정. `models.py` 단일 파일 고정.
- **이유**: AI 코딩 어시스턴트 진입 시 `schema/`와 `schemas/`, `models/`와 `models.py` 혼재로 인한 잘못된 경로 선택 방지.
- **조치**: `app/models/`, `app/repository/`, `app/repositories/`, `app/schema/`, `app/service/`, `app/db/` 6개 빈 디렉토리 삭제 완료.
