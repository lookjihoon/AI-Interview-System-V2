# AI 모의 면접 시스템 V2: RAG Pipeline 상세 분석 

본 문서는 백엔드 코드(`ai_service.py`, `seed_qna.py`, `candidate.py` 등)에 구현된 RAG(Retrieval-Augmented Generation) 파이프라인의 핵심 기술 스택과 설정값을 파악한 기술 명세입니다.

---

## 1. 데이터 파싱 및 Chunking 전략 📄

일반적인 RAG 시스템이 거대한 문서를 무작위로 쪼개는 것과 달리, 본 시스템은 **"면접"이라는 특수한 도메인**에 맞춰 파싱 및 청킹(Chunking) 전략을 채택했습니다.

- **이력서 (PDF) 파싱**: 
  - `routers/interview.py` (및 `candidate.py`) 내의 `parse_pdf()` 함수에서 `langchain_community.document_loaders`의 **`PyPDFLoader`**를 사용해 원문 텍스트를 통째로 추출합니다.
  - 추출된 텍스트는 인위적인 `RecursiveCharacterTextSplitter` 모듈 등을 통한 고정된 Chunk Size/Overlap 분할을 거치지 않습니다. 대신, LLM 프롬프트 주입 시 상위 K줄(Skill Lines 5줄 등)만 정규표현식으로 끊어내어 Context 길이를 관리합니다.
- **면접 질문 및 직무(JD) 데이터**:
  - `seed_qna.py`에서 `qna_data.json`의 QnA 쌍을 로드할 때, 개별 **'질문 문장' 자체가 하나의 자연스러운 청크(Chunk)**로 취급됩니다.
  - 데이터는 50개 단위(`batch_size = 50`)로 배치 처리되어 임베딩되며, 별도의 오버랩(Overlap) 수치는 존재하지 않습니다.

---

## 2. 임베딩(Embedding) 및 DB 적재 (Vector Store) 🧮

문자열을 다차원 벡터 공간으로 변환해 관계성(의미)을 맵핑하는 작업은 오프라인 오픈소스 생태계를 적극 활용합니다.

- **임베딩 모델 세부 설정**:
  - `sentence-transformers/all-mpnet-base-v2` 모델이 적용되어 있습니다. (호출 객체: `HuggingFaceEmbeddings`)
  - **정규화 수치**: `encode_kwargs={'normalize_embeddings': True}`가 명시되어 있어 코사인 유사도 연산 속도를 극대화합니다.
  - 생성되는 **벡터 차원(Dimension)**은 **768차원**입니다.
- **pgvector 적재 흐름**:
  - 데이터베이스인 PostgreSQL은 `main.py` 부트스트랩 과정에서 `CREATE EXTENSION IF NOT EXISTS vector` 쿼리를 통해 활성화됩니다.
  - `models.py`의 `QuestionBank` 테이블 내 `embedding = Column(Vector(768))` 컬럼에 다이렉트로 적재되며, `pgvector.sqlalchemy`가 Python List 배열을 네이티브 벡터 타입으로 자동 치환(`embedding=embedding`)해줍니다.

---

## 3. 유사도 검색 (Retrieval / Top-K) 🔍

지원자가 답변을 마친 후, RAG 파이프라인은 정적 질문이 아닌 **"현재 대화 맥락과 가장 잘 맞는 후속 질문"**을 Vector DB에서 동적으로 탐색합니다.

- **스마트 쿼리 형성 (`_build_rag_query`)**:
  - 질문 검색을 위한 쿼리 문자열 조합: `[Job Title]` + `[사용자 답변에서 추출한 핵심 키워드 최대 5개(형태소 및 불용어 필터링)]` + `[JD 요건 키워드 Top 8]` + `[이력서 스킬 Top 5 Line]`
  - 불필요한 서술어를 모두 날리고 고밀도 키워드 스트링을 구축하여 텍스트 노이즈를 억제합니다.
- **유사도 연산 및 추출량 (Metric & Top-K)**:
  - **Cosine Distance (코사인 거리)** 연산이 선별 모듈(`ai_service.py` 508라인 부근) 단위 구문에 탑재되어 있습니다: `order_by(QuestionBank.embedding.cosine_distance(query_embedding))`
  - **Top-K 설정값**: `stmt.limit(1)`을 사용하여 가장 유사도(적합성)가 높은 **단 1개의 컨텍스트(Question)**만 가져옵니다. 
  - **하드 디듀플리케이션(Exclusion)**: `NOT IN` 절을 사용하여, 현재 세션 DB에 이미 `question_id`로 기록된(이전 턴에 물어본) 질문의 ID는 무조건 배제시켜 동일 질문 출현을 막습니다.

---

## 4. 프롬프트 주입 및 환각(Hallucination) 억제 장치 🧠

추출된 RAG 컨텍스트(기본 질문 1개)는 날것 그대로 출력되지 않고, **Local LLM (`exaone3.5`)**의 언어적 윤색을 거칩니다. (초매개변수: `temperature=0.2`, `num_predict=200`)

이 과정에서 텍스트 환각과 앵무새 같은 기계적 화법을 억제하기 위한 심층적인 **Prompt Engineering 제약 조건**이 부여되어 있습니다 (`_personalise_question` 내부).

1. **[ANTI-GASLIGHTING RULE - 가스라이팅/환각 방지]**:
   - `[이력서 원문]` 변수가 주입됩니다.
   - LLM에게 *"만약 추출된 질문 기술 키워드가 이력서 원문에 없다면, '이력서에 ~을 하셨다고 적혀있는데' 라고 조작하지 말고, '만약 ~상황이 주어진다면 어떻게 대처하시겠습니까?' 형태의 가정형으로 우회하라"*라는 엄격한 룰이 삽입되어 무에서 유를 창조하는 환각을 원천 차단합니다.
2. **[PRONOUN CONVERSION RULE - 대명사 치환]**:
   - 후보자의 기존 답변(`last_answer`) 내역에 담긴 1인칭 대명사("저는", "제가")를 그대로 복사하여 묻는 것을 문법적으로 금지하고, 3인칭/2인칭 형태로 우아하게 전환토록 유도합니다.
3. **[SEMANTIC ANTI-REPETITION - 의미적 중복 차단]**:
   - RAG DB에서 추출된 문장이, 과거 던진 `[이전 질문 목록]` 리스트의 문맥과 '개념적으로 유사한가?'를 스스로 묻게 만듭니다. (*"Would answering one question also answer the other?"*)
   - 만약 YES일 경우, 프롬프트 단에서 폐기하고 이력서/JD에서 아예 다른 각도의 화두를 즉석에서 생성하게 강제합니다.
4. **결과 포맷 통제**:
   - 오직 한 문장의 질문만 출력하며, 종결 어미를 `~하셨나요?`, `~주시겠어요?`로 강제해 비즈니스 한국어 존댓말을 유지시킵니다.
   - 응답 결과에 '요.' 가 중복 생성되는 글리치(`...주시겠어요?요.`) 등을 막기 위한 파이썬 자체의 정규화(Strip) 후처리가 동반됩니다.
