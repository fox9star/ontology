# 고양이 탐색 질문

공식 품종 표준의 특징과 가상 개체·환경·보호자·돌봄·관찰 기록을 탐색합니다.
모든 예제 고양이는 `recordKind "synthetic"`입니다. 품종 표준의 특징을 개체의 실제 특징으로 추론하지 않습니다.
`example.ttl`은 화면용 IRI를, `question-fixture.ttl`은 별도 고정 IRI를 사용합니다.
값이 없는 생년월일이나 미확인 품종은 미기록 정보이며 쿼리 결과에서는 빈 값으로 유지합니다.

### CAT-01. 고양이의 품종 기록과 미확인 정보는 무엇인가?

~~~sparql
PREFIX cat: <https://example.org/ontology/custom/cat#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?cat ?name ?recordKind ?sex ?birthDate ?breedStatus ?breed ?breedLabel ?breedEvidence
WHERE {
  ?cat a cat:Cat ; rdfs:label ?name ; cat:recordKind ?recordKind ; cat:sex ?sex ; cat:breedStatus ?breedStatus .
  FILTER (LANG(?name) = "ko")
  OPTIONAL { ?cat cat:birthDate ?birthDate }
  OPTIONAL { ?cat cat:hasBreed ?breed . ?breed a cat:Breed ; rdfs:label ?breedLabel . FILTER (LANG(?breedLabel) = "ko") }
  OPTIONAL { ?cat cat:breedEvidenceNote ?breedEvidence }
}
ORDER BY ?cat
~~~

### CAT-02. 품종별 특징은 어떤 출처에 근거하는가?

~~~sparql
PREFIX cat: <https://example.org/ontology/custom/cat#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?breed ?breedLabel ?trait ?category ?text ?sourceURL ?publisher ?sourceKind ?accessedOn
WHERE {
  ?breed a cat:Breed ; rdfs:label ?breedLabel ; cat:hasTrait ?trait ; cat:describedBy ?source .
  FILTER (LANG(?breedLabel) = "ko")
  ?trait a cat:Trait ; cat:traitCategory ?category ; cat:traitText ?text ; cat:documentedBy ?source .
  ?source a cat:SourceDocument ; cat:sourceURL ?sourceURL ; cat:publisher ?publisher ;
    cat:sourceKind ?sourceKind ; cat:accessedOn ?accessedOn .
}
ORDER BY ?breed ?trait ?sourceURL
~~~

### CAT-03. 고양이의 생활환경과 담당 보호자는 누구인가?

~~~sparql
PREFIX cat: <https://example.org/ontology/custom/cat#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?cat ?environment ?environmentType ?environmentNote ?guardian ?guardianLabel
WHERE {
  ?cat a cat:Cat ; cat:livesIn ?environment ; cat:caredForBy ?guardian .
  ?environment a cat:Environment ; cat:environmentType ?environmentType ; cat:environmentNote ?environmentNote .
  ?guardian a cat:Guardian ; rdfs:label ?guardianLabel . FILTER (LANG(?guardianLabel) = "ko")
}
ORDER BY ?cat ?guardian
~~~

### CAT-04. 예정·취소된 돌봄 기록은 무엇인가?

~~~sparql
PREFIX cat: <https://example.org/ontology/custom/cat#>
SELECT ?record ?cat ?careKind ?status ?scheduledFor ?carer ?note
WHERE {
  ?record a cat:CareRecord ; cat:aboutCat ?cat ; cat:careKind ?careKind ; cat:status ?status ;
    cat:carer ?carer ; cat:recordNote ?note .
  OPTIONAL { ?record cat:scheduledFor ?scheduledFor }
  FILTER (?status IN ("planned", "cancelled"))
}
ORDER BY ?record
~~~

### CAT-05. 완료된 돌봄의 수행 시각과 담당자는 누구인가?

~~~sparql
PREFIX cat: <https://example.org/ontology/custom/cat#>
SELECT ?record ?cat ?careKind ?performedAt ?scheduledFor ?carer ?note
WHERE {
  ?record a cat:CareRecord ; cat:aboutCat ?cat ; cat:careKind ?careKind ; cat:status "completed" ;
    cat:performedAt ?performedAt ; cat:carer ?carer ; cat:recordNote ?note .
  OPTIONAL { ?record cat:scheduledFor ?scheduledFor }
}
ORDER BY ?record
~~~

### CAT-06. 개체별 관찰과 체중 기록은 어떻게 연결되는가?

~~~sparql
PREFIX cat: <https://example.org/ontology/custom/cat#>
SELECT ?observation ?cat ?recordKind ?observedAt ?kind ?text ?value ?unit
WHERE {
  ?observation a cat:Observation ; cat:observedCat ?cat ; cat:observedAt ?observedAt ;
    cat:observationKind ?kind ; cat:observationText ?text .
  ?cat a cat:Cat ; cat:recordKind ?recordKind .
  OPTIONAL { ?observation cat:measurementValue ?value }
  OPTIONAL { ?observation cat:measurementUnit ?unit }
}
ORDER BY ?observation
~~~

기대 결과는 구조화 원자료에서 별도로 작성했습니다. 기록된 체중은 측정값의 예제이며 품종별 정상 범위·건강 상태 판단을 뜻하지 않습니다.
돌봄의 완료 상태는 수행 시각이 있는 기록입니다. 예정된 작업을 실제 수행한 것으로 해석하지 않습니다.
