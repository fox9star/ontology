# 온톨로지 품질 점검 사용법

정본 스키마, SHACL 제약, 경쟁 질문과 인스턴스 사용 현황을 연결해 변경의 영향을 확인한다. 저장소의 기존 사실을 읽으며 원본 미디어나 인스턴스 그래프를 수정하지 않는다. 현재 스냅샷은 [품질 현황](reports/ontology-quality.md), 자동 처리용 결과는 [JSON](reports/ontology-quality.json)에 있다.

## 실행

```powershell
.\.venv\Scripts\python.exe ontology_quality.py --include-projects --json reports\ontology-quality.json --markdown reports\ontology-quality.md
.\.venv\Scripts\python.exe ontology_docs_check.py --json reports\ontology-documentation.json
.\.venv\Scripts\python.exe term_lifecycle.py check
.\.venv\Scripts\python.exe term_lifecycle.py compare --previous ontology-compatibility-baseline.json --json reports\ontology-compatibility.json
.\.venv\Scripts\python.exe build_ontology_exports.py --check
.\.venv\Scripts\python.exe controlled_vocab_check.py
.\.venv\Scripts\python.exe verify_all.py
.\.venv\Scripts\python.exe run_tests.py
```

`ontology_quality.py`는 기본 예제와 등록된 사용자 온톨로지, 출처 증거 예제를 검사한다. 현재 앱 프로파일 8개와 증거 예제 1개다. `--include-projects`를 주면 각 등록 프로젝트를 별도 그래프로 읽고 프로젝트 이름 없이 집계하며, 미디어 등록 명세가 있는 프로젝트의 저장된 출처 증거와 파일 지문도 다시 검사한다. `--no-instance-validation`은 제약 검사를 생략하며 `shacl_conforms`를 `null`로 남긴다. 미실행을 통과로 표시하지 않는다. CI는 스키마·설명·생애주기·예제·소비자 호환성을 검사하고 보고서를 artifact로 저장한다.

## 게이트와 남은 공백

클래스·속성마다 선언 파일, 한·영 설명 존재 여부, domain/range, SHACL target/path, CQ 식별자, 예제 사용 수를 기록한다. 새 속성의 domain/range 누락, SHACL path 누락, 미선언 로컬 용어를 참조하는 shape, 예제의 미선언 유형/속성과 SHACL 실패는 게이트를 실패시킨다. 상위 클래스 target에서 상속된 제약도 기록한다.

`ontology-quality-policy.json`은 일반적인 코어·분류 클래스에 도메인별 필수 필드를 강요하지 않는 이유와 `core:taskStatus`의 domain 중립성을 용어별로 설명한다. 존재하지 않는 용어의 예외나 사유가 없는 예외는 실패한다. 예외는 검사가 완성되었다는 뜻이 아니다.

CQ 커버리지는 SPARQL을 파싱한 뒤 실제 질의 표현에 들어 있는 용어 IRI를 측정한다. 문자열에 IRI가 등장하거나 prefix만 선언되는 것은 커버리지로 세지 않는다. 정답과 반례는 별도의 golden-answer 테스트에서 확인한다. 현재 CQ에 직접 등장하지 않는 용어는 `cq_backlog`에 남은 작업으로 기록되어 있다. 이 목록이 기존 공백의 기준이며 새로운 누락이나 기존 커버리지 손실은 실패한다. 새 질문이 용어를 다루면 해당 backlog 항목을 제거한다. 자동으로 baseline을 늘려 실패를 숨기지 않는다.

인스턴스 보고서는 유형/속성 미선언, 로컬 참조 미해결, 허용 목록 밖의 값, 그래프 안에서 겹치는 `dcterms:identifier`, 클래스 target 미포함 개체와 출처 관계 없는 자산을 집계한다. 프로파일·프로젝트 사이의 같은 식별자는 자동 중복으로 처리하지 않는다. 외부 파일/IRI를 참조한다는 사실만으로 존재 여부를 확인했다고 표시하지 않는다. PROV 관계가 있어도 원본 생성 모델·프롬프트·내용이 검증되었다고 판단하지 않는다.

의료 인스턴스 식별자, 이름, 값과 원문 SHACL 메시지는 공유 보고서에 넣지 않는다. 분류는 고정된 네 가지 명칭과 missing/unknown 건수만 기록한다. JSON의 용어 목록에는 스키마 용어만 포함한다.

## 선택 값의 제약

`property-contract-shapes.ttl`은 기존 shape에 직접 나오지 않던 27개 속성의 값 계약을 추가한다. 모델·프롬프트·체크섬·시각을 필수로 만들지 않는다. 값이 있으면 자료형·빈 문자열·양수 BPM·관계 대상 IRI를 검사한다. 체크섬 알고리즘은 스키마에서 고정하지 않았으므로 모든 값에 SHA-256 형식을 강요하지 않는다. predicate target을 써서 유형 선언이 없는 주체의 잘못된 값도 찾는다. RDFS inference는 range를 통해 유형을 추가할 수 있으므로 `sh:class` 통과만으로 원자료의 명시적 유형이 확인됐다고 판단하지 않는다.

수용되는 데이터가 좁아졌으므로 배포 전 소비자의 선택 값과 기존 수용 테스트를 확인해야 한다. 의미 snapshot은 SHACL/API 호환성을 증명하지 않는다. 자세한 변경 규칙은 [용어 생애주기](TERM_LIFECYCLE.md)를 따른다.

현재 저장·검증 경로는 [명시 데이터와 추론 검사](RAW_VALIDATION_AND_MODULES.md)를 따로 실행한다. 로컬 named class/union domain·range의 호환 타입은 원자료 또는 명시된 스키마 선언에 있어야 한다. [소비자 호환성 검사](CONSUMER_COMPATIBILITY.md)는 별도 고정 기준선으로 기존 SHACL 계약, 합성 수용/거절 사례, API 응답 형태와 CQ 정답을 비교한다.

## 추론·교환과 릴리스

추론 검사의 지원 범위와 열린 세계의 동일성 처리 규칙은 [의미 검증](SEMANTIC_VALIDATION.md)에 있다. FHIR 교환은 [교차 대응 문서](healthcare-fhir-crosswalk.md)를 따른다. 공식 FHIR 검증은 구성한 합성 fixture만 사용하며 구조 검증과 외부 용어 검증 결과를 따로 기록한다. CI는 공식 구조 검증을 실행한다. 외부 용어 서비스 검사는 `workflow_dispatch`의 `verify_terminology` 옵션이나 `fhir_validate.py --synthetic-fixture --official terminology --fetch-validator`로 실행하며 서비스 접근/검증 미완료는 성공으로 처리하지 않는다.

공개 URI는 미정이다. `namespace_policy.py --release`는 예약된 example.org 식별자로 실패해야 한다. `ontology-compatibility-baseline.json`은 이번 개선 후 정본의 기준이며 CI가 자동 갱신하지 않는다. 소유 도메인과 소비자 이전 계획을 정한 뒤 [URI 이전 표](URI_MIGRATION_TEMPLATE.md)를 검토한다.
