# 온톨로지 관리 기준

## 정본과 버전

- *-schema.ttl은 사람이 편집하는 도메인 스키마의 정본이다. *.owl은 RDF/XML을 요구하는 기존 도구를 위한 호환 출력이며 build_ontology_exports.py로 생성한다.
- 변경 후 python build_ontology_exports.py --check에서 모든 출력이 정본과 같아야 한다.
- Current schema versions: core 1.1.1; MV, agent, DevOps, e-commerce, and academic 1.2.1; healthcare 1.3.1. Incompatible URI or meaning changes require a major version and migration guidance.
- e2e는 별도 namespace를 가진 독립 스키마가 아니라 mv 스키마를 재사용하는 파이프라인 프로파일이다. API 메타데이터의 profile_of: mv로 표시한다. 독립화는 데이터와 소비자를 함께 옮길 계획이 생겼을 때 수행한다.

## 모델링 원칙

- 프로젝트, 에이전트, 계획 작업, 실행, 결과물은 가능한 한 core-schema.ttl의 core:Project, core:Agent, core:Task, core:TaskRun, core:Artifact를 상위 개념으로 재사용한다. 개인정보가 포함되거나 분류가 확인되지 않은 기록은 core:SensitiveRecord 계층을 사용한다.
- 실행 결과에는 계획 작업과 실제 실행을 구분하고, 행위자·입력·생성 결과는 PROV-O와 연결한다. 도메인 전용 관계를 공통 계층에 억지로 넣지 않는다.
- rdfs:domain과 rdfs:range는 RDF 추론으로 주체나 대상을 새 유형으로 분류할 수 있다. 복수 유형을 의도하면 명시적으로 OWL union을 쓰고, 닫힌 데이터 검증은 SHACL에 둔다.
- SHACL은 저장 가능한 데이터의 필수값·자료형·관계 대상·허용 상태를 검사한다. OWL의 제약은 열린 세계의 의미를 표현하며 SHACL의 필수 필드 검사와 같은 역할이 아니다.
- 출처, 모델, 프롬프트, 파일 생성 여부는 자료에 근거가 있을 때만 기록한다. 알 수 없는 사실은 추정하지 말고 미확인으로 남긴다.

## 개인정보·민감 기록

- 헬스케어 그래프의 각 환자 기록은 health:dataClassification으로 Unverified, Synthetic, Pseudonymized, Sensitive 중 하나를 표시한다. 출처가 확인되지 않은 현재 예제는 Unverified로 표시한다.
- API의 기본 의료 그래프 조회는 `Synthetic`으로 명시된 기록만 남긴다. 미확인·가명·민감 또는 분류 누락 기록과 연결된 진단·결과 개체를 제거하고, 모든 분류에서 환자 키를 가린다. SHACL 검증과 로컬 파일은 원자료에 적용한다.
- 상세 의료 응답과 의료 그래프의 Fuseki 동기화는 서버의 `ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE=1` 설정 및 해당 요청의 `include_sensitive=true`를 모두 요구한다. 허용된 상세 열람과 변경 요청 감사 이벤트는 기본적으로 `.runtime/audit.jsonl`에 SHA-256 연결 해시로 영속 저장한다. 메모리의 최근 200건은 파일이 설정되지 않은 독립 사용의 대체 수단이며 앱의 기본 저장 방식이 아니다.
- `ONTOLOGY_AUDIT_LOG_PATH`로 감사 파일 위치를 지정하고 `ONTOLOGY_AUDIT_RETENTION_DAYS`로 보존 기간을 지정한다. 기본 `0`은 전체 기록을 유지한다. 기간을 설정하면 다음 기록 때 만료된 이벤트를 제거하고 남은 연결 해시를 재생성한다. 보존 기간은 운영자가 데이터 정책에 맞춰 설정한다. 경로에는 OS 접근 권한을 적용하고 원격 백업·저장 시 암호화는 운영 환경에 맞춰 준비한다.
- `GET /api/v1/auth/audit-integrity`로 현재 파일의 연결 해시를 검사한다. 본문·질의 문자열·IP는 저장하지 않는다. 변경 요청은 감사 저장소가 불가능하거나 변조가 감지되면 실행 전에 실패한다. 요청 이벤트만으로 변경 성공을 증명하지 않는다. 파일 전체 재작성이나 마지막 기록 삭제는 독립 보관한 이전 해시가 없으면 감지하지 못할 수 있으므로 해시 체인을 변조 불가능한 저장소로 간주하지 않는다. 보존 처리 전 필요한 기록을 별도 보호 저장소에 보관한다.
- 기본 의료 SPARQL, 탐색, 개체 상세, 그래프, 내보내기, 감사 뷰와 메트릭은 정제된 응답 그래프를 사용한다. 앱은 신뢰된 단일 사용자 로컬 범위에서만 실행하며, 이 경계를 공개 서비스의 사용자별 권한 체계로 간주하지 않는다.
- 식별 키와 이름을 실제 정보라고 단정하거나, 출처가 없는 예제를 합성 데이터라고 재분류하지 않는다.

## 작업 흐름

1. 먼저 관련 competency question이 새 용어로 답을 표현하는지 확인한다.
2. 정본 Turtle에 용어, 다국어 라벨, 설명, 타입, domain/range를 정의한다.
3. 해당 도메인의 SHACL shapes에 폐쇄형 데이터 검증을 추가한다. 기존 예제에 없는 사실을 채워 넣지 않는다.
4. 관련 예제 또는 별도 검증 자료를 갱신하고 build_ontology_exports.py로 RDF/XML 호환 파일을 재생성한다.
5. 앱의 온톨로지 목록 version과 문서를 함께 갱신한다. 새 도메인이나 프로파일은 API 메타데이터와 competency question catalog에도 추가한다.

앱 로더는 정본 Turtle/RDF/XML과 로컬 core-schema.ttl, controlled-vocabularies.ttl을 읽는다. 네트워크에서 PROV-O 등을 자동 다운로드하지 않는다. 이로써 서버 검증이 외부 사이트 상태에 의존하지 않는다.

## 통제 어휘와 상호운용성

- `controlled-vocabularies.ttl`은 상태·검수 판정·의료 분류를 SKOS 개념 체계와 URI로 식별한다. 저장/API의 기존 상태 문자열은 유지하고 `skos:notation`을 코드로 사용한다. `controlled_vocab_check.py`가 각 SHACL 허용 목록과 코드 어휘의 일치, 한·영 선호 라벨을 검사한다.
- 새 도메인 상태 값은 정본 SHACL 목록과 SKOS scheme을 같은 변경으로 갱신한다. 상태 전이를 모델링할 때는 허용 전이 규칙을 별도 SHACL로 추가한다.
- `healthcare-fhir-crosswalk.md`는 FHIR R5 후보 대응을 기록한다. 로컬 개념은 FHIR 리소스와 동등하다고 단정하지 않으며, 확인된 코드·단위·시각만 교환한다.

## 검증 및 namespace 공개 정책

- 로컬 품질 게이트는 `ontology_quality.py`, `ontology_docs_check.py`, `term_lifecycle.py`, `verify_all.py`, `build_ontology_exports.py --check`, `controlled_vocab_check.py`, `namespace_policy.py`, `python run_tests.py`를 포함한다. GitHub Actions에서 내보내기, 어휘, namespace/version, 생애주기·호환성, 커버리지와 회귀 테스트를 실행하고 근거 보고서를 보관한다. [품질 점검 사용법](QUALITY_GUIDE.md)을 따른다.
- `namespace_policy.py` 개발 검사는 ontology IRI·용어 선언 중복, namespace, semantic version과 로컬 import 폐쇄/순환을 검사한다. `namespace_policy.py --release`는 예약된 `example.org`/`example.com` 식별자가 있으면 실패한다. 이 저장소의 namespace는 개발용이므로 실제 공개 전 URI 소유 도메인 결정, URI 마이그레이션 표, 소비자 호환성 계획이 필요하다.
- vocabulary별 URI와 용어 매핑, 저장 그래프·스냅샷 업데이트 체크리스트는 [URI_MIGRATION_TEMPLATE.md](URI_MIGRATION_TEMPLATE.md)를 사용한다. 폐기 용어는 `owl:deprecated true`와 `dcterms:isReplacedBy`로 안내하고, 의미가 같다는 근거 없이 OWL 동등성 공리를 추가하지 않는다.
- `core-shapes.ttl`은 공통 실행 시각을 검사한다. 시작·종료 시각은 원자료로 확인될 때 기록하고, 둘 다 있으면 종료가 시작보다 빠르지 않은지 검증한다.


## Quality work completed on 2026-10-05

- Golden-answer tests execute the 25 documented competency questions. Healthcare and the 11 additional cross-cutting questions use synthetic test data, with empty-result, isolation and inference counterexamples.
- All 175 named classes and properties have Korean and English labels and definitions; `ontology_docs_check.py` measures bilingual coverage and is a CI gate.
- OWL consistency checks cover the eight supported conflict patterns documented in [SEMANTIC_VALIDATION.md](SEMANTIC_VALIDATION.md), including explicit identity conflicts and negative property assertions. This is not a complete OWL 2 consistency proof.
- `ontology_quality.py` connects each schema term with SHACL and query references and reports explicit instance usage. Structural exceptions and remaining CQ coverage debt are documented per term; the baseline prevents new gaps without claiming the existing backlog is complete. See [QUALITY_GUIDE.md](QUALITY_GUIDE.md).
- `term_lifecycle.py` checks retirement/replacement and compares the reviewed `ontology-compatibility-baseline.json` to changed schema semantics. SHACL and API acceptance changes require separate regression review.
- Mutation events persist in `.runtime/audit.jsonl` as a SHA-256 hash chain. Set `ONTOLOGY_AUDIT_LOG_PATH` to choose another file and `ONTOLOGY_AUDIT_RETENTION_DAYS` to configure retention; `0` keeps the complete history. Request bodies, query strings, and client IPs are excluded. Mutations fail closed if the store is unavailable or corrupted. Verify the chain at `GET /api/v1/auth/audit-integrity`.
- `GET /api/v1/healthcare/fhir-bundle` exports only explicitly `Synthetic` records as a FHIR R5 collection Bundle. Resources missing required codes, statuses, or units are omitted with a generic warning. See [the FHIR crosswalk](healthcare-fhir-crosswalk.md).
- Current schema versions are core `1.1.1`, MV/agent/DevOps/e-commerce/academic `1.2.1`, and healthcare `1.3.1`; e2e uses the MV profile version.
- The release namespace remains undecided, so no IRIs were migrated. `namespace_migration.py` defaults to a dry run, creates per-file backups with `--apply`, and excludes project graphs and snapshots unless `--include-project-data` is explicitly supplied. See [the URI migration worksheet](URI_MIGRATION_TEMPLATE.md).
