# 온톨로지 개선 완료 기록 — 2026-10-05

제안한 여섯 가지 개선을 코드·검사·문서와 CI 설정에 반영했다. 아래 수치는 이번 로컬 실행 결과이며 GitHub Actions의 원격 실행 결과는 아니다.

| 개선 | 구현 결과 |
|---|---|
| 문서와 구현 일치 | 영속 감사 파일, 보존 처리, 요청 이벤트의 의미와 연결 해시의 한계를 거버넌스/README에 반영 |
| 품질 커버리지 | 클래스·속성 175개의 모듈/버전, 설명, domain/range, 활성 SHACL, CQ와 예제 사용 연결표 및 집계 생성 |
| 경쟁 질문 | 14개에서 25개로 확대; 출처 누락·자산 계보·재시도 이력·상태 변화·프로젝트 격리·중복 식별자·추론과 반례 추가 |
| 추론·제약 | 8개 지원 충돌 패턴 검사; 고유 이름 가정 없이 OWL 동일성 처리; 선택 값 27개 속성의 SHACL 계약 보강 |
| FHIR 교환 | 재귀 참조/자료형/주체 일관성 검증, 공식 R5 구조·외부 용어 검증 실행, 발견한 체중 profile category 오류 수정 |
| 용어 생애주기 | 폐기·대체·동등성 근거, namespace/import, 버전·공리 변경 검사 및 8개 모듈 기준선 생성 |

한국어 정의 104개를 보강해 클래스·속성 175개 모두 한국어/영어 라벨과 정의를 갖췄다. RDF/XML 호환 출력 6개는 정본과 일치한다. 새 커버리지 검사에서 예제의 미선언 `mv:Agent` 유형을 발견해 기존 개체를 유지하면서 선언된 `mv:AIAgent`로 수정했다.

## 검증 근거

- 자동 테스트 **302개 통과**, 실패/오류/건너뜀 **0개**. 실행·로그 해시는 [verification.json](verification.json)에 있다.
- 예제 **7개 프로파일**과 등록 프로젝트 **1개**의 SHACL 통과. [커버리지 현황](ontology-quality.md), [JSON](ontology-quality.json).
- 한국어/영어 라벨·정의 각각 **175/175**, 문서 예외 **0개**. [문서 커버리지](ontology-documentation.json).
- 정본 버전·namespace/import·폐기/대체 검사와 호환성 기준선 비교 통과. [호환성 결과](ontology-compatibility.json).
- 공식 HL7 validator **6.10.4**, FHIR R5 **5.0.0**, 고정한 패키지 **5개**를 사용한 합성 Bundle 구조 검증 통과: fatal/error **0**, warning **6**, information **5**.
- 별도 외부 용어 서비스 검증 통과: fatal/error **0**, warning **4**, information **4**. 실제 `https://tx.fhir.org/r5` 호출 근거와 출력 해시가 [FHIR 실행 기록](../fhir-validation-evidence.json)에 있다.

구조 검증 경고에는 오프라인에서 확인할 수 없는 용어와 서술문·수행자 권고가 포함된다. 외부 용어 검증 후에도 서술문·수행자 권고와 Task output 타입의 미정의 binding 안내가 남는다. 파트너별 implementation guide, 임상 정확성 또는 전체 OWL 2 일관성을 검증했다고 해석하지 않는다.

## 남은 범위와 운영

활성 SHACL 연결이 있는 용어는 **166/175**이고, 공통/분류 클래스 **9개**는 도메인 필수 필드를 강요하지 않는 이유를 용어별로 기록했다. `core:taskStatus`의 domain 중립 예외를 포함한 구조 예외는 **10개**이다. 속성 **116개**는 모두 활성 SHACL path에 연결된다.

경쟁 질문이 직접 참조하는 용어는 **54/175**이다. 직접 질의에 포함되지 않은 **121개**는 완료된 테스트 커버리지로 세지 않고 [품질 정책](../ontology-quality-policy.json)의 backlog에 기록했다. 새 누락, 기존 커버리지 손실, 해결 후 남은 stale 예외는 게이트를 실패시킨다. 출처 연결 수치는 원본 생성 모델·프롬프트가 검증됐다는 의미가 아니다.

공개 URI 소유 도메인은 미정이다. URI 이전 도구와 생애주기·호환성 기준선은 준비되어 있고 `namespace_policy.py --release`는 개발용 식별자를 계속 거절한다. 새 선택 값 제약은 수용 범위를 좁히므로 소비자의 데이터 수용 회귀를 확인한 후 배포한다. CI의 외부 용어 서비스 검사는 수동 workflow 실행의 `verify_terminology` 옵션으로 준비했다.

재실행과 해석은 [품질 점검 사용법](../QUALITY_GUIDE.md), [의미 검증 범위](../SEMANTIC_VALIDATION.md), [용어 생애주기](../TERM_LIFECYCLE.md), [FHIR 대응 문서](../healthcare-fhir-crosswalk.md)를 따른다.
