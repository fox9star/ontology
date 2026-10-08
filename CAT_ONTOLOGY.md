# 고양이 온톨로지

[웹 스튜디오에서 열기](http://127.0.0.1:5000/?ont=cat). 온톨로지 검색창에 `고양이`, `cat`, `kitten`을 입력하고 **고양이 온톨로지 (cat)** 를 선택합니다. 새 항목이 보이지 않으면 페이지를 새로고침합니다.

버전은 `0.1.0`, 상태는 `draft: true`입니다. 공식 품종 자료와 개체별 생활환경·보호자·돌봄·관찰 기록을 연결하는 초기 모델입니다. 공개 릴리스 URI는 아직 결정하지 않았으며 `https://example.org/ontology/custom/cat#`은 개발용입니다.

## 모델과 관계

8개 클래스와 32개 속성에 한국어·영어 이름과 정의를 제공합니다.

| 클래스 | 기록하는 내용 |
| --- | --- |
| `Cat` | 고양이 개체와 품종 기록의 확인 상태 |
| `Breed` | 출처가 있는 품종 정보 |
| `Trait` | 품종 자료에 기술된 털·체형·무늬 특징과 근거 |
| `Environment` | 개체가 생활하는 환경 |
| `Guardian` | 개체의 돌봄을 담당하는 보호자 |
| `CareRecord` | 예정·완료·취소 상태를 가진 돌봄 활동 |
| `Observation` | 개체를 관찰한 시점과 관찰 내용·체중 기록 |
| `SourceDocument` | 공식 자료의 URL·발행 기관·확인 날짜 |

```text
고양이 → 품종 기록 → 품종 특징 → 출처 문서
  ├→ 생활환경
  ├→ 보호자
  ├→ 돌봄 기록 → 상태·예정 시각·수행 시각·담당자
  └→ 관찰 기록 → 시각·관찰 내용·체중
```

품종 특징은 **품종 표준의 기술**입니다. 모든 개체가 같은 특징을 가진다는 뜻이 아니며 개체의 관찰값으로 자동 상속하지 않습니다. 외형만으로 품종을 추론하지 않습니다. 품종을 확인하지 못한 고양이는 미확인 상태로 기록하고 `hasBreed`를 부여하지 않습니다.

## 실제 출처와 가상 예시

초기 품종 목록은 메인쿤, 샴, 브리티시 쇼트헤어, 노르웨이 숲의 4개 품종입니다. 각 품종의 2개 신체 특징을 공식 CFA 자료에서 요약했습니다. 자료 확인일은 **2026-10-05**입니다.

| 품종 | 초기 특징 2개 | 공식 출처 |
| --- | --- | --- |
| 메인쿤 / Maine Coon Cat | 풍성하고 길이가 고르지 않은 털로, 어깨의 털은 배·뒷다리 부위보다 짧음. 길고 균형 잡힌 직사각형 체형. | [CFA Maine Coon Cat](https://cfa.org/breed/maine-coon-cat/) |
| 샴 / Siamese | 짧고 가는 털이 몸에 밀착됨. 밝은 몸통과 짙은 얼굴·귀·다리·발·꼬리 포인트 사이의 대비. | [CFA Siamese](https://cfa.org/breed/siamese/) |
| 브리티시 쇼트헤어 / British Shorthair | 짧고 매우 조밀한 털. 다부지고 힘 있는 몸과 넓은 가슴. | [CFA British Shorthair](https://cfa.org/breed/british-shorthair/) |
| 노르웨이 숲 / Norwegian Forest Cat | 조밀한 속털과 길고 매끄러운 방수성 겉털의 이중모. 근육이 발달한 몸과 넓은 가슴. | [CFA Norwegian Forest Cat](https://cfa.org/breed/norwegian-forest-cat/) |

품종에 관한 성격·수명·건강 위험·치료·급여 권장량은 초기 사실로 제공하지 않습니다. TICA의 Household Pet 분류에는 혼혈·무작위 번식 고양이뿐 아니라 미등록 혈통 고양이 등도 포함되므로, 그 분류를 하나의 품종이나 모두 혼혈이라는 의미로 해석하지 않습니다. [TICA Household Cat](https://tica.org/breed/household-pet/).

예시의 **고양이 6마리와 보호자·환경·돌봄·관찰 기록은 모두 가상**입니다. 개체 4마리의 품종 연결도 가상의 설정이며, 나머지 2마리는 품종 미확인 예시입니다. `recordKind`로 가상 기록임을 표시합니다. 실제 소유자·동물·보호소의 데이터를 수집하거나 실제 돌봄 활동을 수행했다는 의미가 아닙니다.

초기 그래프는 총 41개 개체·298개 트리플로 구성됩니다. [등록 기록](reports/cat-ontology.md)에 데이터 입력 검증과 실행 중 스튜디오의 조회 결과를 기록했습니다.

## 탐색 질문

화면의 SPARQL 질문 목록에서 다음 6개 질문을 실행할 수 있습니다. [질문과 쿼리 원문](custom-ontologies/cat/questions.md).

| ID | 질문 |
| --- | --- |
| `CAT-01` | 고양이의 품종 기록과 미확인 정보는 무엇인가? |
| `CAT-02` | 품종별 특징은 어떤 출처에 근거하는가? |
| `CAT-03` | 고양이의 생활환경과 담당 보호자는 누구인가? |
| `CAT-04` | 예정·취소된 돌봄 기록은 무엇인가? |
| `CAT-05` | 완료된 돌봄의 수행 시각과 담당자는 누구인가? |
| `CAT-06` | 개체별 관찰과 체중 기록은 어떻게 연결되는가? |

조회 결과가 없으면 해당 항목이 기록되지 않았을 수 있습니다. 관계가 없다는 사실만으로 실제 보호자·품종·활동이 없었다고 단정하지 않습니다.

## 기록과 검증의 의미

돌봄 상태 `planned`는 예정, `completed`는 완료, `cancelled`는 취소를 뜻합니다. 예정된 활동을 완료로 취급하지 않습니다. 완료 기록에는 `performedAt` 수행 시각을 요구하며, 돌봄 담당자는 해당 고양이의 보호자로 연결되어야 합니다.

체중은 관찰 시점에 측정한 kg 단위의 양수 값으로 기록합니다. 양수라는 검증 규칙은 건강한 체중의 기준이나 의학적 판단을 뜻하지 않습니다. 이 모델은 기록과 조회를 위한 것으로 진단·치료·급여 안내를 제공하지 않습니다.

SHACL은 필수값·유형·허용 상태·참조 관계, 시간대가 포함된 시각 형식과 상태별 시각 필드를 검증합니다. 구조적 적합성과 출처 URL의 존재는 관찰 내용의 진실성, 품종 혈통, 돌봄의 실제 수행을 자동으로 보증하지 않습니다. 실제 데이터를 추가할 때는 기록의 근거와 담당자를 별도로 확인합니다.

## 파일

| 파일 | 용도 |
| --- | --- |
| [profile.json](custom-ontologies/cat/profile.json) | 검색 목록의 이름·설명·버전·경로 |
| [schema.ttl](custom-ontologies/cat/schema.ttl), [schema.owl](custom-ontologies/cat/schema.owl) | Turtle 정본과 RDF/XML 표현 |
| [shapes.ttl](custom-ontologies/cat/shapes.ttl) | 입력 검증 규칙 |
| [example.ttl](custom-ontologies/cat/example.ttl) | 웹 화면의 품종 목록과 가상 개체·돌봄·관찰 자료 |
| [curated-data.json](custom-ontologies/cat/curated-data.json) | 출처가 있는 품종 특징과 가상 예시의 구조화 원자료 |
| [questions.md](custom-ontologies/cat/questions.md) | 6개 탐색 질문과 SPARQL |
| [question-fixture.ttl](custom-ontologies/cat/question-fixture.ttl), [question-answers.json](custom-ontologies/cat/question-answers.json) | 고정 질문 자료와 기대 결과 |
| [consumer-cases.trig](custom-ontologies/cat/consumer-cases.trig) | 유효·무효 소비자 사례 |
