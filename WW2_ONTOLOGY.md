# 세계 2차 대전 온톨로지

[웹 스튜디오에서 열기](http://127.0.0.1:5000/?ont=ww2). 온톨로지 검색창에 `세계2차대전`, `대전`, `World War`, `WWII`, `ww2`를 입력하고 **세계2차대전 온톨로지 (ww2)** 를 선택합니다. 새 항목이 보이지 않으면 페이지를 새로고침합니다.

버전은 `0.1.0`, 상태는 `draft: true`입니다. 출처를 따라 사건과 참여자를 탐색할 수 있는 초기 지식 그래프이며, 전쟁 전체를 망라하지 않습니다. 공개 릴리스 URI는 아직 결정하지 않았으며 `https://example.org/ontology/custom/ww2#`은 개발용입니다.

## 모델과 관계

8개 클래스와 21개 속성에 한국어·영어 이름과 정의를 제공합니다.

| 클래스 | 기록하는 내용 |
| --- | --- |
| `Conflict` | 전쟁과 채택한 시간 범위 |
| `HistoricalEvent` | 침공·공격·전투·상륙·항복 등의 사건 |
| `State` | 사건 당시의 국가·정치체와 역사적 국명 |
| `Person` | 사건에 참여한 인물 |
| `Place` | 국가·지역·도시·만·기지·수용소 수준의 장소 |
| `Participation` | 특정 사건에서 국가·인물이 맡은 역할, 진영, 참여 기간, 근거 |
| `SourceDocument` | 출처 URL, 발행 기관, 자료 유형, 확인 날짜 |
| `HistoricalClaim` | 특정 사건에 대한 요약 서술과 인용 출처 |

```text
전쟁 ← 사건 → 장소
        ├→ 참여 기록 → 국가 또는 인물
        │       └→ 역할·진영·기간·근거 문서
        └→ 역사 서술 → 출처 문서
```

역할과 진영은 `Participation`에 기록하며 **해당 사건에만 적용**합니다. 초기 국가 참여 기록은 해당 국가 소속 군대나 대표자의 사건 행위를 요약합니다. 예를 들어 스탈린그라드의 독일군 항복은 독일 국가 전체의 항복을 뜻하지 않습니다. `Axis`·`Allied`는 사건별 역사적 진영을 묶는 분류이며 정식 동맹 조약 가입일을 나타내지 않습니다. 역사적 국명은 현대 국가명·국경과 동일하다고 가정하지 않습니다. 장소는 탐색용 범위를 나타내며 정밀 좌표나 당시 국경을 제공하지 않습니다.

## 날짜와 자료 범위

초기 전쟁 레코드는 **1939-09-01부터 1945-09-02까지**를 채택합니다. 유럽의 개전일과 일본의 정식 항복문서 서명일을 기준으로 삼은 이 그래프의 시대 구분입니다. 아시아에서는 1937년부터 이어진 전쟁의 맥락을 함께 고려해야 합니다. [The National WWII Museum의 아시아·태평양 전쟁 설명](https://www.nationalww2museum.org/war/articles/asia-pacific-war-1945).

사건의 날짜는 일 단위입니다. 확인한 날짜가 개시일·종료일·서명일·방송일인 경우 시작일과 종료일을 같게 기록하고 `dateNote`에 의미를 설명합니다. 따라서 같은 시작일·종료일을 가진 전투 레코드도 전투 전체가 하루 만에 끝났다는 뜻이 아닙니다. 항복 발표, 문서 서명, 전투 중지는 서로 다른 사건으로 구분합니다.

홀로코스트의 맥락도 군사 사건과 함께 고려합니다. USHMM은 나치의 유대인 박해와 살해가 전개된 홀로코스트 시대를 **1933–1945년**, 조직적·체계적 대량학살의 시행을 **1941–1945년**으로 설명합니다. 이 장기 과정을 임의의 정확한 시작일·종료일로 축소하지 않습니다. 초기 그래프에는 아우슈비츠 해방 사건이 포함됩니다. [USHMM, Introduction to the Holocaust](https://encyclopedia.ushmm.org/content/en/article/introduction-to-the-holocaust).

## 초기 사건 10개와 출처

| 기록한 날짜 | 사건 | 날짜의 의미 | 출처 |
| --- | --- | --- | --- |
| 1939-09-01 | 독일의 폴란드 침공 개시 | 침공 개시일 | [USHMM](https://encyclopedia.ushmm.org/content/en/article/invasion-of-poland-fall-1939) |
| 1941-06-22 | 바르바로사 작전 개시 | 독일의 소련 침공 개시일 | [USHMM](https://encyclopedia.ushmm.org/content/en/article/invasion-of-the-soviet-union-june-1941) |
| 1941-12-07 | 진주만 공격 | 하와이 현지 공격일 | [미국 국립공원관리청](https://www.nps.gov/wwii/learn/historyculture/pearl-harbor.htm) |
| 1943-02-02 | 스탈린그라드의 독일군 항복 | 남아 있던 독일군의 항복과 전투 종결일 | [USHMM](https://encyclopedia.ushmm.org/content/en/timeline-event/holocaust/1942-1945/german-defeat-at-stalingrad) |
| 1944-06-06 | 노르망디 상륙 개시 (D-Day) | 상륙 개시일 | [USHMM](https://encyclopedia.ushmm.org/content/en/article/d-day) |
| 1945-01-27 | 아우슈비츠 수용소 해방 | 소련군의 해방일 | [USHMM](https://encyclopedia.ushmm.org/content/en/timeline-event/holocaust/1942-1945/soviet-forces-liberate-auschwitz) |
| 1945-05-07 | 독일 항복문서의 랭스 서명 | 랭스에서 문서를 서명한 날짜 | [미국 국립문서기록관리청의 항복문서](https://www.archives.gov/milestone-documents/surrender-of-germany) |
| 1945-05-08 | 독일군 작전 중지의 발효 | 문서가 정한 중앙유럽시간 23:01의 발효일 | [미국 국립문서기록관리청의 항복문서](https://www.archives.gov/milestone-documents/surrender-of-germany) |
| 1945-08-15 | 일본의 항복 수락 방송 | 일본 현지 방송일 | [National Museum of Nuclear Science & History / AHF의 방송 자료](https://ahf.nuclearmuseum.org/ahf/key-documents/jewel-voice-broadcast/) |
| 1945-09-02 | 일본 항복문서의 정식 서명 | 도쿄만 USS Missouri 함상 서명일 | [미국 국립문서기록관리청의 항복문서](https://www.archives.gov/milestone-documents/surrender-of-japan) |

5월 8일 기록은 문서가 규정한 작전 중지 시점을 나타내며, 모든 지역에서 실제 전투가 동시에 멈췄다는 서술이 아닙니다. 스탈린그라드의 항복에는 정식 항복문서 서명이 확인되었다는 의미를 부여하지 않습니다.

## 탐색 질문

화면의 SPARQL 질문 목록에서 다음 6개 질문을 실행할 수 있습니다. [질문과 쿼리 원문](custom-ontologies/ww2/questions.md).

| ID | 질문 |
| --- | --- |
| `WW2-01` | 전쟁의 시간 범위 안에서 사건은 어떤 순서로 일어났는가? |
| `WW2-02` | 각 사건에 참여한 국가·인물의 역할과 근거는 무엇인가? |
| `WW2-03` | 사건이 발생한 장소와 장소의 종류는 무엇인가? |
| `WW2-04` | 사건에 관한 역사 서술은 어떤 출처를 인용하는가? |
| `WW2-05` | 현지 군대의 항복·항복 발표·문서 서명·정전의 날짜는 어떻게 구분되는가? |
| `WW2-06` | 원문 사료를 직접 제공하는 출처로 연결된 사건은 무엇인가? |

조회 결과가 없다는 이유만으로 어떤 사건·참여자·관계가 역사적으로 존재하지 않았다고 해석하지 않습니다. 초기 데이터에 포함하지 않은 항목일 수 있습니다.

## 검증과 출처 해석

SHACL 규칙은 필수값과 유형, 허용된 사건·역할·자료 분류, 날짜의 선후 관계, 전쟁·사건·참여 기간의 포함 관계, 사건과 역사 서술의 양방향 참조를 확인합니다.

`HistoricalClaim`의 서술은 인용 자료를 요약한 문구입니다. `SourceDocument.sourceKind`는 `primary-document`, `museum-summary`, `archive-exhibit`로 자료 유형을 구분합니다. 링크가 있다는 사실과 SHACL 적합성은 문서의 진위나 서술의 정확성을 자동으로 보증하지 않습니다. 역사적 해석과 자료 비평은 원문을 확인하여 수행합니다.

| 파일 | 용도 |
| --- | --- |
| [profile.json](custom-ontologies/ww2/profile.json) | 검색 목록의 이름·설명·버전·경로 |
| [schema.ttl](custom-ontologies/ww2/schema.ttl), [schema.owl](custom-ontologies/ww2/schema.owl) | Turtle 정본과 RDF/XML 표현 |
| [shapes.ttl](custom-ontologies/ww2/shapes.ttl) | 입력 검증 규칙 |
| [example.ttl](custom-ontologies/ww2/example.ttl) | 웹 화면에서 탐색하는 초기 사건 데이터 |
| [curated-data.json](custom-ontologies/ww2/curated-data.json) | 출처를 확인한 사건·참여자·장소·자료의 구조화 원자료 |
| [questions.md](custom-ontologies/ww2/questions.md) | 6개 탐색 질문과 SPARQL |
| [question-fixture.ttl](custom-ontologies/ww2/question-fixture.ttl), [question-answers.json](custom-ontologies/ww2/question-answers.json) | 별도 개체 IRI를 사용하는 고정 질문 자료와 기대 결과 |
| [consumer-cases.trig](custom-ontologies/ww2/consumer-cases.trig) | 유효·무효 소비자 사례 |
