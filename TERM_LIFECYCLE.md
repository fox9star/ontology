# 용어 생애주기와 버전 호환성

공개 URI 소유 도메인은 아직 미정이다. 현재 `example.org` IRI는 개발용으로 유지하며, 이 문서와 검사 도구의 존재는 공개 릴리스 준비 완료를 의미하지 않는다.

## 용어 선언과 모듈 경계

각 모듈은 하나의 절대 IRI로 `owl:Ontology`를 선언하고, 하나의 SemVer `owl:versionInfo`를 기록한다. 선택적인 `owl:versionIRI`는 절대 IRI이며 다른 모듈·버전과 중복할 수 없다. 클래스, 객체 속성, 데이터 속성, 주석 속성, SKOS 개념·개념 체계는 한 파일에서만 선언한다. `owl:Class`와 `rdfs:Class`를 같은 자원에 함께 선언하는 것은 하나의 클래스 역할로 취급한다.

기본 용어 네임스페이스는 모듈 온톨로지 IRI 뒤의 `#`이다. 기존 데이터와의 호환성을 위해 `controlled-vocabularies.ttl`에는 healthcare 네임스페이스의 SKOS 개념·개념 체계를 선언하는 명시적 예외가 있다. 이 예외는 클래스나 속성의 중복 선언을 허용하지 않는다. 실제 IRI를 이동할 때에는 이 예외도 검토한다.

로컬 `owl:imports`는 번들 안의 온톨로지 IRI 또는 선언된 버전 IRI로 해석할 수 있어야 하고 순환할 수 없다. PROV-O는 현재 명시적으로 허용된 외부 참조이며 검사 과정에서 다운로드하지 않는다. 외부 온톨로지 전체의 추론이나 버전 안정성이 검증되었다는 의미는 아니다. 새 외부 import는 로컬 번들에 추가하거나 검토 후 `namespace_policy.EXTERNAL_IMPORTS`에 정확한 IRI로 등록한다.

```powershell
.\.venv\Scripts\python.exe .\namespace_policy.py
.\.venv\Scripts\python.exe .\term_lifecycle.py check
```

## 폐기와 대체

호환성 기간 동안 이전 용어의 IRI와 역할 선언을 유지하고 `owl:deprecated true`를 추가한다. 후속 용어가 있다면 `dcterms:isReplacedBy`에 정확히 하나의 절대 IRI를 기록한다. 대체 대상은 같은 역할의 활성 용어여야 한다. 클래스에서 속성으로, 객체 속성에서 데이터 속성으로 바꾸는 것은 대체 관계로 허용하지 않는다.

대체 대상은 로컬에 선언되어 있거나 `term_lifecycle_policy.json`의 `external_replacements`에 출처·대상·역할·검토 이유를 명시해야 한다. 외부 대상의 역할은 사람이 확인한 정책 기록이며, 도구가 원격 스키마를 조회하여 증명하지 않는다. 대체 사슬과 순환을 허용하지 않으므로, 이전 용어들의 대체 관계는 최종 활성 용어로 직접 연결한다. 후속 용어 없이 폐기할 때에는 같은 정책 파일의 `retired_terms`에 정확한 용어 IRI와 이유를 기록한다. 미사용·중복 정책 기록은 검사 실패이다.

예를 들어 실제 검토가 끝난 외부 대체는 아래 구조로 기록한다. 현재 저장소에는 승인된 대체나 폐기 용어가 없다.

```json
{
  "retired_terms": {},
  "external_replacements": [
    {
      "source": "https://owned.invalid/v1#OldProject",
      "target": "https://owned.invalid/v2#Project",
      "role": "class",
      "reason": "소비자 영향과 후속 클래스의 의미를 검토한 근거를 기록한다."
    }
  ],
  "equivalence_justifications": []
}
```

폐기·대체 관계 자체는 의미 동등성을 주장하지 않는다. `owl:equivalentClass`와 `owl:equivalentProperty`는 정말 같은 외연을 갖는지 검토한 경우에만 사용하고, 정책 파일의 `equivalence_justifications`에 `source`, `predicate`, `target`, `reason`을 기록한다. 문서 이름이 비슷하거나 URI만 바뀌었다는 이유로 동등성을 추가하지 않는다. 이 검사는 근거 기록의 존재를 확인하며 근거의 타당성은 의미 검토와 회귀 테스트로 확인한다.

## 호환성 기준선

`ontology-compatibility-baseline.json`은 이 개선 작업 시점의 개발 스키마 기준선이다. 과거 공개 릴리스의 호환성을 증명하는 자료는 아니다. 기존 기준선을 CI에서 다시 생성하면 변경이 숨겨지므로, CI는 비교만 수행한다. 릴리스 검토가 끝난 후에만 기준선을 새 버전으로 교체하고 이전 기준선은 버전 관리 이력에 보존한다.

```powershell
# 현재 스키마를 기존 검토 기준선과 비교한다.
.\.venv\Scripts\python.exe .\term_lifecycle.py compare --previous .\ontology-compatibility-baseline.json --json .\.runtime\ontology-compatibility.json

# 변경과 소비자 영향 검토가 끝난 뒤, 새 기준선을 별도 파일에 작성한다.
.\.venv\Scripts\python.exe .\term_lifecycle.py snapshot --output .\.runtime\candidate-ontology-baseline.json
```

비교 도구는 RDF 빈 노드 식별자가 바뀌어도 같은 제한·리스트 공리를 같은 것으로 계산한다. 용어 제거, 역할 또는 도메인/범위·상위 관계·익명 제한·disjointness·SKOS 관계 등 명시된 공리 변경, 온톨로지 IRI나 import 변경은 영향받은 모듈의 major 버전 증가를 요구한다. 새 용어 추가는 버전 증가를 요구한다. 불확실한 공리 변경도 보수적으로 major 검토 대상으로 분류한다. 레이블·설명·SKOS 문서 주석과 폐기 표시는 의미 해시에서 제외하며, 폐기 표시는 별도 생애주기 검사로 검증한다.

SHACL 필수값·카디널리티·자료형·허용 값·대상 범위가 달라져 이전에 허용하던 인스턴스를 거부하게 되는 경우도 호환성 변경이다. 현재 기준선 CLI는 **정규 스키마 공리만** 비교한다. SHACL·API·SPARQL 소비자·저장 인스턴스의 호환성은 예전 정상/비정상 fixture, 경쟁 질문과 프로파일 검증으로 별도 확인하고, 데이터 수용 범위를 축소한다면 major 버전을 검토한다. 기준선 통과만으로 이 호환성 전체나 공개 릴리스 적합성을 선언하지 않는다.

## 한국어·영어 설명 커버리지

`ontology_docs_check.py`는 모든 명명된 스키마 클래스·속성에 대해 `rdfs:label@ko`, `rdfs:label@en`, `rdfs:comment@ko`, `rdfs:comment@en`의 존재와 최소 설명 길이를 측정한다. 통제 어휘의 SKOS 레이블 검사는 `controlled_vocab_check.py`가 담당한다. 글 길이 검사만으로 설명 정확성이나 번역 일치를 보장하지 않으므로, 실제 용어의 대상·단위·출처·추론 의미를 검토한다.

```powershell
.\.venv\Scripts\python.exe .\ontology_docs_check.py --json .\.runtime\ontology-documentation.json
```

불가피한 설명 누락은 `ontology_documentation_exceptions.json`에 `file`, `term`, `field`(`label` 또는 `definition`), `language`(`ko` 또는 `en`), `reason`으로 정확히 한 항목을 기록한다. 예외를 적용해도 측정된 커버리지가 증가하지 않으며, 번역이 추가되면 오래된 예외는 실패하므로 제거해야 한다. 현재 예외는 없다.
