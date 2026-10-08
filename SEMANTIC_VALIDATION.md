# 의미 검증의 지원 범위

`owl_reasoner.run_owl_deductive_closure()`는 전달받은 그래프를 OWL-RL 또는 RDFS 규칙으로 확장하고, 아래에 열거한 모순 패턴을 검사한다. 반환값 `consistent: true`는 이 검사에서 모순을 발견하지 못했다는 뜻이며, 모든 OWL 2 온톨로지에 대한 완전한 일관성 증명이 아니다. `success`는 추론 작업이 수행됐다는 의미이므로, 호출자는 `consistent`와 `semantic_violations`를 함께 확인해야 한다.

기존 `disjoint_type_violations` 필드는 호환성을 유지한다. 추가된 `semantic_violations`는 종류별 근거를 제공하며, `consistency_scope`는 이 문서를 가리킨다. RDFS 모드에서는 OWL 동일성 등의 추론이 수행되지 않아 검사에 사용할 수 있는 사실의 범위가 좁아진다.

| 검사 종류 | 보고하는 충돌 | 정상으로 처리하는 사례 |
| --- | --- | --- |
| `disjoint_types` | `owl:disjointWith` 또는 `owl:AllDisjointClasses`로 구분한 두 named class에 같은 개체가 속함 | 선언되지 않은 클래스 중복 |
| `identity_conflict` | `owl:sameAs`로 연결된 개체 사이의 `owl:differentFrom` 또는 `owl:AllDifferent` | 서로 다른 IRI만 사용한 경우 |
| `functional_literal_conflict` | 기능성 속성에 함께 기록된 값이 지원하는 데이터타입의 서로 다른 값임 | integer `1`과 decimal `1.0`처럼 값이 같은 표현 |
| `disjoint_properties` | `owl:propertyDisjointWith` 또는 `owl:AllDisjointProperties` 속성이 같은 subject/object에 함께 적용됨 | object가 다르고 동일성도 확인되지 않음 |
| `irreflexive_property` | 비반사 속성이 동일한 개체를 연결함 | 서로 다른 이름이지만 동일성 선언이 없음 |
| `asymmetric_property` | 비대칭 속성이 양방향으로 적용되거나 자기 자신을 연결함 | 단방향 관계 |
| `negative_property_assertion` | 명시적 부정 관계와 긍정 관계가 함께 성립함 | 관계를 기록하지 않은 경우 |
| `invalid_literal` | 지원하는 XSD 데이터타입의 잘못된 어휘 표현 또는 정수 값 범위 초과 | 검사하지 않는 사용자 정의 데이터타입 |

OWL은 고유 이름 가정을 사용하지 않는다. 기능성 object property가 `a → b`, `a → c`를 가지면 두 개체가 같다는 추론이 가능하다. 역기능성 속성이 두 subject를 같은 object에 연결해도 마찬가지다. 이 구현은 이름이 다르다는 이유로 오류를 만들지 않고, 추론된 동일성이 명시적 상이성 또는 다른 검사와 충돌할 때 보고한다. 중복 업무 식별자는 경쟁 질문 SYN-06에서 별도의 데이터 품질 문제로 확인한다.

검사는 추론 후 그래프에서 수행하므로 하위 클래스, 하위 속성, 역관계와 동일성 전파로 드러나는 충돌도 포함한다. 사용자에게 보여 주는 샘플과 진단은 정렬하고 같은 진단을 중복 제거한다. blank node 식별자는 파싱마다 달라질 수 있으므로 익명 표현의 표시 문자열까지 안정적이라는 보장은 없다.

데이터타입 어휘 검사는 XSD integer 계열과 각 하위 타입의 값 범위, boolean, decimal, float/double의 숫자·INF·NaN 표현을 명시적으로 검사한다. date/dateTime은 설치된 RDFLib의 `ill_typed` 판정을 사용한다. 입력을 정규화하면 원래 잘못된 표현이 사라질 수 있으므로 어휘 검사가 필요한 가져오기 단계에서는 원래 문자열을 보존해야 한다. 테스트는 `Literal(..., normalize=False)`를 사용한다.

값 비교는 string, 언어가 붙은 문자열, boolean과 숫자 타입에 한정한다. 사용자 정의 타입, 시간대가 미정인 날짜/시각, NaN의 복잡한 값 비교를 잘못된 충돌로 판단하지 않는다. 모든 datatype facet, datatype restriction, 키와 cardinality 충돌, 일반적인 익명 class expression, 전체 OWL 프로파일 적합성이나 완전한 만족 가능성 검사를 제공하지 않는다. SHACL의 필수값, 최대 개수, 상태 전이와 업무 규칙은 기존 SHACL 검증이 담당한다. 잘못된 RDF collection이나 부정 선언 자체의 형식 검사는 별도 스키마·데이터 검증 영역이다.

외부 `owl:imports`는 실행 중 자동으로 내려받지 않는다. 필요한 스키마와 alignment는 로컬에 명시적으로 합쳐야 한다. 합성 CQ의 `prov:generated` 역관계는 테스트 fixture에 명시되어 있으며, named graph 프로젝트 범위는 쿼리 격리를 확인하는 사례다. 그래프 이름 자체가 인증이나 권한 검사를 시행하는 것은 아니다.

근거는 [W3C OWL 2 RL 규칙](https://www.w3.org/TR/owl2-profiles/#Reasoning_in_OWL_2_RL_and_RDF_Graphs_using_Rules)과 [OWL 2 Primer의 개체 동일성 설명](https://www.w3.org/TR/owl2-primer/#Equality_and_Inequality_of_Individuals)을 참조한다. 이 문서는 위 표의 구현 범위를 명시하며, W3C 규칙 전체를 구현했다는 의미로 사용하지 않는다.

관련 회귀 검사는 `tests/test_semantic_consistency.py`, 기존 `tests/test_semantic_disjointness.py`, `tests/test_owl_reasoner.py`, `tests/test_competency_questions.py`에 있다. 기본 목록 37개, 출처 증거 3개, AI 영화 제작 5개로 총 45개 질문을 검사한다. 추론 전후·출처 추가·다른 프로젝트 변경·프로젝트 간 참조 누출 및 업무 연결을 제거하거나 잘못 바꾸는 반례를 포함한다. 합성 fixture에는 환자 데이터, 실제 사용자 파일 또는 실제 생성 기록을 넣지 않는다.
