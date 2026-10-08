# Ontology Studio v3.3.0 - 2026-10-05

## Ontology quality and interoperability

- Added executable golden-answer regression coverage for all 14 documented competency questions.
- Completed English labels and definitions for 175 named classes and properties, with a CI completeness gate.
- Added a dry-run-first namespace migration utility with backups, placeholder-host validation, and default exclusion of project graphs and snapshots. No namespace migration has been applied because the owned release hostname is undecided.
- Added selected OWL disjointness axioms and explicit consistency checks for valid examples and conflicting instances.
- Persisted mutation audit events as a tamper-evident SHA-256 chain, added an integrity endpoint, and made mutations fail closed when the audit store is unavailable or corrupted.
- Added a synthetic-only FHIR R5 collection Bundle export with local structural validation and explicit handling for incomplete codes, statuses, and units.
- Bumped schema versions for the annotation and healthcare export changes; details are in [ontology governance](ONTOLOGY_GOVERNANCE.md).

# Ontology Studio v3.2.0 — 2026-10-04

## 현재 구현

- 모델 API 키 대신 ChatGPT로 로그인한 Codex CLI가 실제 텍스트 요청을 처리합니다. 요청, 상태, 출력, 해시와 실행 출처를 `.codex-jobs/`에 보관합니다.
- 전체 웹 경로에 로컬 단일 사용자 접근 검사를 적용했습니다. 개발용 키와 화면 역할 전환을 제거했습니다.
- 스냅샷은 도메인·프로젝트별 데이터만 보관합니다. 복원은 해시·SHACL·등록 파일 검사 후 실제 파일에 원자적으로 저장합니다.
- 개체와 장면 편집은 잠금과 저장 전 검증을 적용합니다. 실패 시 원본 데이터가 유지됩니다.
- 공통 Agent·Task 코어를 추가하고 7개 도메인 프로파일 모두 SHACL 검증을 지원합니다. 대학 모델은 academic-schema.ttl 정본과 academic-shapes.ttl을 사용합니다.
- 도메인 Turtle을 정본으로 통일하고 RDF/XML 호환 파일의 재생성·드리프트 확인 도구를 추가했습니다. e2e가 mv 어휘를 공유한다는 사실을 API metadata에 표시합니다.
- 헬스케어 데이터 분류를 명시하고 기본 질의를 환자 식별자·임상 소견을 출력하지 않는 집계 중심으로 바꿨습니다.
- 도메인별 competency question과 SPARQL 예제를 추가했습니다. 원본 OWL/RDF 자료는 보존합니다.
- 파이프라인 예제는 시뮬레이션과 실제 미디어 생성 여부를 구분합니다. 외부 동기화와 알림은 요청 시에만 수행합니다.
- 로컬 시작·종료의 PID 소유권 검사, Docker 호스트 작업 폴더 공유, 이동한 등록 파일 URI의 명시적 매핑을 지원합니다.
- 출처 보고서는 기록된 사실과 미확인을 표시하며 외부 인증을 주장하지 않습니다.

현재 사용 방법은 [README](README.md)와 [매뉴얼](manual.md), 확인 결과는 [안정화 기록](STABILIZATION.md)을 참고하세요.

## Ontology quality update — 2026-10-04

- Added shared PROV-O input/output and optional run timestamps, with SHACL ordering checks.
- Added timeline overlap/order/duration and dependency-cycle checks for MV; successful build-to-deploy artifact traceability for DevOps; explicit currency verification with ISO 4217-shaped codes when verified, bounded price precision, and order transition history for e-commerce; coded, timed, unit-aware observation structures for healthcare.
- Added SKOS status and privacy-classification schemes, automated parity checks against SHACL code lists, and a publication guard for placeholder namespaces.
- Added default API redaction for non-synthetic healthcare records and linked result nodes. Sensitive reads and Fuseki transfer require a server setting plus per-request opt-in, and are audited.
- Added an informative FHIR R5 crosswalk without claiming class equivalence.
- Bumped domain ontology versions to 1.2.0 and the shared core to 1.1.0.

## v3.1 작성 당시 초안

아래 내용은 이전 초안입니다. 현재 동작과 검증 범위는 위 v3.2 설명을 기준으로 합니다. 역할 기반 인증, 영구 감사 로그, 추론 그래프 자동 저장은 현재 제공하지 않습니다.

# RELEASE NOTES - AI Agent Ontology Ecosystem v3.1.0

**Release Date:** 2026-10-04  
**Version:** v3.1.0 Enterprise Governance, Versioning & OWL Deductive Reasoning Edition  

---

## 🚀 Key Highlights & New Features

### 1. 지식 그래프 버전 관리 및 불변 스냅샷 롤백 (Graph VCS) (`graph_versioning.py`)
- **Git-like 지식 그래프 버전 관리**:
  - 변경 전후의 지식 그래프 상태를 불변 Turtle 스냅샷(`.snapshots/`)으로 영구 보관.
  - 타임스탬프, 커밋 메시지, 메타데이터 및 트리플 수 자동 인덱싱.
- **시맨틱 트리플 차분(Diff) 엔진 (`compute_graph_diff`)**:
  - 그래프 간 의미론적 차이를 정밀 비교하여 추가(+), 삭제(-), 일치 트리플 목록 분리 추출.
- **원자적 원클릭 롤백 (`rollback_to_snapshot`)**:
  - 과거 스냅샷 시점으로 롤백 시 인메모리 그래프 및 로컬 파일 원자적 복원 보장.
- **웹 UI 전용 탭 (`#snapshots-pane`) & 차분 모달 (`#snapshotDiffModal`)**:
  - 스냅샷 타임라인 테이블, 원클릭 스냅샷 생성, 시각적 차분 모달, 원클릭 롤백 지원.
- **신규 REST 엔드포인트**:
  - `GET /api/v1/snapshots`: 도메인별 저장된 스냅샷 목록 조회.
  - `POST /api/v1/snapshots/create`: 현재 그래프 상태의 불변 스냅샷 생성.
  - `POST /api/v1/snapshots/rollback`: 지정 스냅샷으로 그래프 원자적 복원.
  - `GET /api/v1/snapshots/diff`: 스냅샷 간 또는 스냅샷과 현재 그래프 간 시맨틱 차분 계산.

### 2. W3C OWL 2 RL 연역적 추론 엔진 (`owl_reasoner.py`)
- **W3C 표준 OWL 2 RL & RDFS 연역적 폐포(Deductive Closure)**:
  - `owlrl` 라이브러리를 통한 서브클래스(`rdfs:subClassOf`), 서브프로퍼티(`rdfs:subPropertyOf`), 역관계(`owl:inverseOf`), 도메인/레인지 함의 및 전이적 폐포 확장.
  - 명시적 사실(Asserted)과 추론된 사실(Inferred)을 정밀 분리 및 유형별 메트릭 집계.
- **웹 UI 통합 (`#instances-pane`)**:
  - 지식 그래프 툴바에 `[OWL-RL 추론 확장]` 버튼 탑재.
  - 클릭 한 번으로 숨겨진 지식 관계를 연역적으로 추론하여 Vis.js 2D 인터랙티브 그래프에 즉시 가시화.
- **신규 REST 엔드포인트**:
  - `POST /api/v1/reasoning/expand`: 지정 도메인의 연역적 폐포 추론 및 확장 그래프 메트릭 반환.

### 3. 엔터프라이즈 RBAC 역할 기반 접근 제어 및 감사 로그 (`auth.py`)
- **다계층 역할 기반 권한 모델**:
  - `viewer` (읽기 전용: 그래프 조회, 메트릭, 검증, SPARQL)
  - `editor` (편집 가능: 인스턴스 등록, 자율 LLM 생성, 스냅샷 생성)
  - `admin` (모든 권한: 스냅샷 롤백, 인스턴스 삭제, 감사 로그 전체 조회)
- **API Key & Bearer Token 인증**:
  - `X-API-Key` 헤더 또는 `Authorization: Bearer <token>`을 통한 무상태 인증.
- **불변 감사 로깅 (Audit Logging)**:
  - 그래프 변형 및 롤백, CRUD 작업에 대한 실시간 클라이언트 IP, 식별자, 타임스탬프 감사 로그 기록 (`_AUDIT_LOGS`).
- **신규 REST 엔드포인트**:
  - `GET /api/v1/auth/identity`: 현재 요청자의 인증 상태 및 역할 조회.
  - `GET /api/v1/auth/audit-logs`: 최근 보안 및 감사 로그 조회.

### 4. 자율 LLM 에이전트 PySHACL 검증 지속성 & 실시간 텔레메트리 연동
- **PySHACL 실시간 검증 가드레일 (`agent_llm.py`)**:
  - LLM이 자율 생성한 W3C PROV-O 계보 트리플을 온톨로지 지식 그래프에 영구 반영(`save_to_graph=True`)하기 전, 해당 도메인의 SHACL 형상 규칙을 사전 검증.
  - 검증 실패 시 트리플 롤백 및 안전 보장.
- **전방위 실시간 텔레메트리 SSE 알림 (`event_stream.py` & Toast)**:
  - `INSTANCE_CREATED`, `INSTANCE_DELETED`, `AGENT_LLM_EXECUTION`, `GRAPH_SNAPSHOT_CREATED`, `GRAPH_ROLLBACK_EXECUTED`, `OWL_REASONING_EXPANDED` 전 이벤트 발행 및 웹 브라우저 실시간 Toast 팝업 & 그래프 자동 리로드.

### 5. 95개 단위 테스트 100% 통과 & 6대 산업 도메인 무결성
- 신규 모듈 3종(`test_auth.py`, `test_graph_versioning.py`, `test_owl_reasoner.py`)을 포함한 **95개 단위 테스트 100% 성공** (`run_tests.py`).
- 6대 전 도메인(MV, E2E, DevOps, Agent, E-Commerce, Healthcare) PySHACL 무결성 검증 100% 지속 통과 (`verify_all.py`).
