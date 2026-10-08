# 세계 2차 대전 탐색 질문

초기 데이터는 공식 기록관·박물관 자료에서 확인한 사건 표본입니다. 전쟁 전체를 망라하지 않습니다.
`example.ttl`은 화면용 개체 IRI를, `question-fixture.ttl`은 별도 고정 개체 IRI를 사용합니다.
일자만 확인한 사건은 시작일과 종료일을 같게 기록하며 `dateNote`에서 개시·종료·서명 등 일자의 의미를 설명합니다.
참여 역할과 진영은 해당 사건에만 적용합니다. 조회 결과가 없는 사실을 역사적으로 부재했다고 해석하지 않습니다.

### WW2-01. 전쟁의 시간 범위 안에서 사건은 어떤 순서로 일어났는가?

~~~sparql
PREFIX ww2: <https://example.org/ontology/custom/ww2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?event ?label ?kind ?start ?end ?dateNote ?warStart ?warEnd ?warDateNote
WHERE {
  ?war a ww2:Conflict ; ww2:startDate ?warStart ; ww2:endDate ?warEnd ; ww2:dateNote ?warDateNote .
  ?event a ww2:HistoricalEvent ; ww2:eventOf ?war ; rdfs:label ?label ;
    ww2:eventKind ?kind ; ww2:startDate ?start ; ww2:endDate ?end ; ww2:dateNote ?dateNote .
  FILTER (LANG(?label) = "ko")
}
ORDER BY ?start ?event
~~~

### WW2-02. 각 사건에 참여한 국가·인물의 역할과 근거는 무엇인가?

~~~sparql
PREFIX ww2: <https://example.org/ontology/custom/ww2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?event ?actor ?actorLabel ?actorKind ?historicalName ?role ?side ?from ?until ?sourceURL
WHERE {
  ?event a ww2:HistoricalEvent ; ww2:hasParticipation ?participation .
  ?participation a ww2:Participation ; ww2:participant ?actor ; ww2:role ?role ; ww2:documentedBy ?source .
  { ?actor a ww2:State ; ww2:historicalName ?historicalName . BIND("state" AS ?actorKind) }
  UNION { ?actor a ww2:Person . BIND("person" AS ?actorKind) }
  ?actor rdfs:label ?actorLabel . FILTER (LANG(?actorLabel) = "ko")
  ?source ww2:sourceURL ?sourceURL .
  OPTIONAL { ?participation ww2:side ?side }
  OPTIONAL { ?participation ww2:startDate ?from }
  OPTIONAL { ?participation ww2:endDate ?until }
}
ORDER BY ?event ?actor ?role ?sourceURL
~~~

### WW2-03. 사건이 발생한 장소와 장소의 종류는 무엇인가?

~~~sparql
PREFIX ww2: <https://example.org/ontology/custom/ww2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?event ?place ?placeLabel ?placeKind
WHERE {
  ?event a ww2:HistoricalEvent ; ww2:occurredAt ?place .
  ?place a ww2:Place ; rdfs:label ?placeLabel ; ww2:placeKind ?placeKind .
  FILTER (LANG(?placeLabel) = "ko")
}
ORDER BY ?event ?place
~~~

### WW2-04. 사건에 관한 역사 서술은 어떤 출처를 인용하는가?

~~~sparql
PREFIX ww2: <https://example.org/ontology/custom/ww2#>
SELECT ?event ?claim ?text ?source ?sourceURL ?publisher ?sourceKind ?accessedOn
WHERE {
  ?event a ww2:HistoricalEvent ; ww2:hasClaim ?claim .
  ?claim a ww2:HistoricalClaim ; ww2:aboutEvent ?event ; ww2:claimText ?text ; ww2:citesSource ?source .
  ?source a ww2:SourceDocument ; ww2:sourceURL ?sourceURL ; ww2:publisher ?publisher ;
    ww2:sourceKind ?sourceKind ; ww2:accessedOn ?accessedOn .
}
ORDER BY ?event ?claim ?source
~~~

### WW2-05. 현지 군대의 항복·항복 발표·문서 서명·정전의 날짜는 어떻게 구분되는가?

~~~sparql
PREFIX ww2: <https://example.org/ontology/custom/ww2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?event ?label ?kind ?date ?dateNote
WHERE {
  ?event a ww2:HistoricalEvent ; rdfs:label ?label ; ww2:eventKind ?kind ;
    ww2:startDate ?date ; ww2:dateNote ?dateNote .
  FILTER (LANG(?label) = "ko")
  FILTER (?kind IN ("surrender", "surrender-announcement", "surrender-signing", "ceasefire"))
}
ORDER BY ?date ?event
~~~

### WW2-06. 원문 사료를 직접 제공하는 출처로 연결된 사건은 무엇인가?

~~~sparql
PREFIX ww2: <https://example.org/ontology/custom/ww2#>
SELECT DISTINCT ?event ?source ?sourceURL
WHERE {
  ?event a ww2:HistoricalEvent ; ww2:hasClaim ?claim .
  ?claim a ww2:HistoricalClaim ; ww2:aboutEvent ?event ; ww2:citesSource ?source .
  ?source a ww2:SourceDocument ; ww2:sourceKind "primary-document" ; ww2:sourceURL ?sourceURL .
}
ORDER BY ?event ?source
~~~

고정 정답은 출처를 확인한 구조화 기록에서 별도로 작성했습니다. `sourceKind`는 링크된 자료의 유형이며,
SHACL 적합성은 입력 구조·참조·날짜 관계를 확인합니다. 출처 내용에 대한 역사학적 비평을 대신하지 않습니다.
