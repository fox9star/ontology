# Peacock / 공작류 온톨로지 역량 질문

학명·성별 용어·형태·행동·서식·먹이·번식 값을 출처별 근거와 함께 탐색한다. 서로 다른 동물원 페이지의 수치는 각 출처 범위대로 유지한다.

### PEA-01. 공작류 예시 종의 학명, 보통명과 분류 단계를 무엇으로 기록했는가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?species ?scientificName ?label ?rank WHERE {
  ?species a pea:PeafowlSpecies ; pea:taxonScientificName ?scientificName ;
    pea:taxonRank ?rank ; rdfs:label ?label .
  FILTER(lang(?label) = "ko")
} ORDER BY ?scientificName
~~~

### PEA-02. 각 종은 어느 속·과·목·강으로 이어지는가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?speciesName ?genusName ?familyName ?orderName ?className WHERE {
  ?species a pea:PeafowlSpecies ; pea:taxonScientificName ?speciesName ; pea:taxonHigherTaxon ?genus .
  ?genus pea:taxonScientificName ?genusName ; pea:taxonHigherTaxon ?family .
  ?family pea:taxonScientificName ?familyName ; pea:taxonHigherTaxon ?order .
  ?order pea:taxonScientificName ?orderName ; pea:taxonHigherTaxon ?class .
  ?class pea:taxonScientificName ?className .
} ORDER BY ?speciesName
~~~

### PEA-03. peacock, peahen, peachick은 각각 어떤 성별 또는 성장 단계 용어인가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?term ?category ?label WHERE {
  { ?term a pea:SexTerm ; pea:sexCategory ?category ; pea:sexTermLabel ?label }
  UNION
  { ?term a pea:LifeStageTerm ; pea:lifeStageCategory ?category ; pea:lifeStageTermLabel ?label }
  FILTER(lang(?label) = "ko")
} ORDER BY ?category
~~~

### PEA-04. 공작의 train 구조와 눈무늬는 무엇이며 어떤 출처가 뒷받침하는가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?feature ?label ?description ?source WHERE {
  ?feature a pea:MorphologicalFeature ; pea:featureLabel ?label ;
    pea:featureDescription ?description ; pea:featureEvidence ?evidence .
  ?evidence pea:evidenceSource ?doc . ?doc pea:sourceTitle ?source .
  FILTER(?feature IN (pea:feature-train-structure, pea:feature-ocelli))
  FILTER(lang(?label) = "ko" && lang(?description) = "ko" && lang(?source) = "ko")
} ORDER BY ?feature
~~~

### PEA-05. 인도공작과 녹색공작의 성별에 따른 외형 설명은 어떻게 구분되는가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?feature ?species ?sex ?description WHERE {
  ?feature a pea:MorphologicalFeature ; pea:featureKind "sexual-dimorphism" ;
    pea:featureOfSpecies ?species ; pea:featureDescription ?description .
  OPTIONAL { ?feature pea:featureAssociatedSexTerm ?sex }
  FILTER(lang(?description) = "ko")
} ORDER BY ?species ?feature
~~~

### PEA-06. 종별 서식 환경 또는 분포 범위는 어느 출처에서 설명되는가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?item ?species ?kind ?description ?source WHERE {
  ?item a pea:HabitatRange ; pea:habitatOfSpecies ?species ; pea:habitatKind ?kind ;
    pea:habitatDescription ?description ; pea:habitatEvidence ?evidence .
  ?evidence pea:evidenceSource ?doc . ?doc pea:sourceTitle ?source .
  FILTER(lang(?description) = "ko" && lang(?source) = "ko")
} ORDER BY ?species ?kind
~~~

### PEA-07. 동물원 자료가 공작류의 먹이로 열거한 항목은 무엇인가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?diet ?category ?label ?species WHERE {
  ?diet a pea:DietItem ; pea:dietCategory ?category ; pea:dietLabel ?label ;
    pea:dietOfSpecies ?species .
  FILTER(lang(?label) = "ko")
} ORDER BY ?category ?label
~~~

### PEA-08. 출처가 설명하는 전시·사회·섭식 행동은 무엇인가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?behavior ?kind ?label ?species ?description WHERE {
  ?behavior a pea:Behavior ; pea:behaviorKind ?kind ; pea:behaviorLabel ?label ;
    pea:behaviorOfSpecies ?species ; pea:behaviorDescription ?description .
  FILTER(lang(?label) = "ko" && lang(?description) = "ko")
} ORDER BY ?kind ?behavior ?species
~~~

### PEA-09. 산란 수와 포란 기간을 출처별로 비교하면 어떤 값이 기록되어 있는가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?record ?measure ?minimum ?maximum ?unit ?estimate ?source WHERE {
  ?record a pea:ReproductiveObservation ; pea:reproductionMeasure ?measure ;
    pea:reproductionMinimum ?minimum ; pea:reproductionMaximum ?maximum ;
    pea:reproductionUnit ?unit ; pea:reproductionEstimateType ?estimate ;
    pea:reproductionEvidence ?evidence .
  ?evidence pea:evidenceSource ?doc . ?doc pea:sourceTitle ?source .
  FILTER(lang(?source) = "ko")
} ORDER BY ?measure ?source
~~~

### PEA-10. 사용한 출처의 제목·발행자·확인일·범위는 무엇인가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?title ?publisher ?url ?accessed ?scope WHERE {
  ?source a pea:SourceDocument ; pea:sourceTitle ?title ; pea:sourcePublisher ?publisher ;
    pea:sourceURL ?url ; pea:sourceAccessedOn ?accessed ; pea:sourceScope ?scope .
  FILTER(lang(?title) = "ko" && lang(?scope) = "ko")
} ORDER BY ?source
~~~

### PEA-11. 각 핵심 주장에 연결된 근거 출처, 위치와 근거 상태는 무엇인가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?evidence ?about ?source ?locator ?status ?claim WHERE {
  ?evidence a pea:EvidenceRecord ; pea:evidenceAbout ?about ; pea:evidenceSource ?doc ;
    pea:evidenceLocator ?locator ; pea:evidenceStatus ?status ; pea:evidenceClaim ?claim .
  ?doc pea:sourceTitle ?source .
  FILTER(lang(?claim) = "ko" && lang(?source) = "ko")
} ORDER BY ?evidence
~~~

### PEA-12. 이 초안에서 포함·제한·제외한 지식 범위는 무엇인가?

~~~sparql
PREFIX pea: <https://example.org/ontology/custom/peafowl#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?note ?status ?label ?explanation WHERE {
  ?note a pea:CoverageNote ; pea:coverageStatus ?status ; pea:coverageLabel ?label ;
    pea:coverageExplanation ?explanation .
  FILTER(lang(?label) = "ko" && lang(?explanation) = "ko")
} ORDER BY ?status ?note
~~~

이 프로필은 초안이다. 출처 주장은 종 설명이지 개체·개체군에 대한 현장 관찰이 아니다. 보전 등급은 포함하지 않는다.
