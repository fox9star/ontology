# 지식·업무 영역 온톨로지 (`domain`)

이 프로필은 지식 분야와 업무·응용 영역을 분류하고, 그 영역과 로컬 온톨로지 프로필의 연결을 기록한다. 인터넷 DNS 도메인 이름을 다루는 모델은 아니다.

## 범위와 구조

- 프로필 ID: `domain`, 버전 `0.1.0`, 상태: 초안, 네임스페이스: `https://example.org/ontology/custom/domain#`
- 11개 클래스와 99개 속성으로 분류 체계, 프로필 배정, 범위 진술, 분야 간 관계, 외부 분류 매핑, 출처, 검토와 변경 기록을 표현한다.
- 핵심 클래스는 `DomainCatalog`, `KnowledgeDomain`, `OntologyProfile`, `DomainAssignment`, `DomainRelation`, `DomainScopeStatement`, `DomainMapping`, `ExternalClassificationScheme`, `DomainSource`, `DomainReview`, `DomainChangeEvent`다.
- `DomainCatalog`와 `KnowledgeDomain`은 각각 `skos:ConceptScheme`과 `skos:Concept`의 하위 클래스로 두었다. 사용자 정의 선호어·대체어·정의·기호·상위/하위·관련어 속성은 대응하는 SKOS 속성의 하위 속성으로 연결한다. 상위/하위는 직접 부모-자식 관계를 뜻한다.

## 예시 분류

분류 예시는 12개 개념과 8개 직접 계층 관계를 포함한다. 최상위 분야는 인공지능, 컴퓨터 네트워킹, 디지털 미디어, 헬스케어, 로보틱스, 교통이다. 하위 분야에는 머신러닝, 모방학습, 무선 네트워킹, 로봇 미들웨어, 자율주행, AI 영화 제작이 있다. 자율주행과 AI 영화 제작은 각각 두 상위 분야에 연결되는 다중 상위 분류 사례다.

현재 로컬 프로필 연결 5건은 `ai-film`, `autonomous-driving`, `imitation-learning`, `ros2`, `wireless-router`에 대한 제안 배정이다. 예시 출처는 해당 프로필의 메타데이터를 가리킨다. 이 배정은 승인된 분류 판단이 아니다. 외부 분류 체계 매핑 레코드는 검토 흐름을 보여 주는 미착수 예시이며, 외부 체계나 대상 URI를 주장하지 않는다. 검토 상태는 예정/미검토다.

따라서 이 계층은 설명용 초안이며 공식적이거나 포괄적인 분야 표준이 아니다. 배포용 URI와 분류 권위 기관은 정해지지 않았다.

## 검증 및 스튜디오 등록

2026-10-08 로컬 확인 결과:

- 데이터 그래프 524개 트리플, 인스턴스 40개, 질문 fixture 524개 트리플
- SHACL 원본 및 추론 단계 모두 적합, 위반 결과 0건
- 역직렬화한 Turtle/OWL 스키마 그래프가 동일함
- 12개 competency query의 SPARQL 문법 파싱 완료, 답변 계약 12개가 질문 ID와 구조상 일치
- 로컬 카탈로그 30개 프로필에 `domain` 등록
- 탐색기: 클래스 11, 속성 99, 인스턴스 40
- 템플릿 API: `DOM-01`–`DOM-12`; 선택 메뉴 페이지 HTTP 200 및 `domain` 옵션 확인

질문 쿼리는 문법만 확인했고 실행하거나 예상 답변과 비교하지 않았다. TriG 소비자 예시는 파싱했지만 실행하지 않았다. 자동 테스트와 브라우저 시각 검수는 하지 않았다. 검증 기록은 [등록 보고서](reports/domain-ontology.md)와 기계 판독용 [JSON 보고서](reports/domain-ontology.json)에 있다.

## 파일

- 스키마: [Turtle](custom-ontologies/domain/schema.ttl), [OWL/RDF/XML](custom-ontologies/domain/schema.owl), [SHACL](custom-ontologies/domain/shapes.ttl)
- 예시 데이터: [RDF/Turtle](custom-ontologies/domain/example.ttl), [질문 fixture](custom-ontologies/domain/question-fixture.ttl), [답변 계약](custom-ontologies/domain/question-answers.json)
- [역량 질문](custom-ontologies/domain/questions.md), [소비자 호환 예시](custom-ontologies/domain/consumer-cases.trig)
- 스튜디오 카탈로그는 `custom-ontologies/` 아래 프로필을 자동 검색하므로 프로필 ID `domain`으로 선택할 수 있다.

## 모델 참고

SKOS는 개념 체계, 다국어 표기, 노트, 계층·연관 링크와 매핑을 표현하기 위한 W3C 권고안이다. 이 프로필은 그 표현 모델을 참고할 뿐, 아래 예시 분류의 권위나 외부 분류와의 동등성을 SKOS가 보증한다는 뜻은 아니다. [W3C SKOS Reference](https://www.w3.org/TR/skos-reference/)
