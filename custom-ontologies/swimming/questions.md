# 수영 업무 질문

화면에서는 `example.ttl`에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용하며 두 그래프의 개체 IRI는 저장 공간만 다르고 내용은 같다.
예제는 가상의 선수 4명, 클럽 2곳, 수영장 2곳, 대회 3개이며 실제 선수나 기록이 아니다. 시간은 초 단위 소수로 적으며 1분 5초 20은 65.20이다.
25m 수영장과 50m 수영장의 기록은 서로 다른 종류이므로 질문에서 구분한다. 결과에 없는 출전은 아직 기록하지 않았다는 뜻이며 출전하지 않았다는 증명이 아니다.

### SWIM-01. 어떤 대회가 어느 수영장에서 언제 열리고 종목은 몇 개인가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?meet ?pool ?length ?lanes ?start ?end (COUNT(DISTINCT ?event) AS ?events)
WHERE {
  ?meet a swim:Meet ; swim:heldAt ?pool ; swim:startDate ?start ; swim:endDate ?end ; swim:hasEvent ?event .
  ?pool a swim:Pool ; swim:poolLengthMeters ?length ; swim:laneCount ?lanes .
}
GROUP BY ?meet ?pool ?length ?lanes ?start ?end
ORDER BY ?start ?meet
~~~

### SWIM-02. 각 대회에는 어떤 영법·거리·부문의 종목이 있는가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?meet ?event ?stroke ?distance ?category
WHERE {
  ?meet a swim:Meet ; swim:hasEvent ?event .
  ?event a swim:SwimEvent ; swim:stroke ?stroke ; swim:distanceMeters ?distance ; swim:eventCategory ?category .
}
ORDER BY ?meet ?event
~~~

### SWIM-03. 종목별 공식 기록의 순위와 기록, 증빙은 무엇인가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?event ?rank ?swimmer ?time ?evidence
WHERE {
  ?entry a swim:Entry ; swim:inEvent ?event ; swim:forSwimmer ?swimmer ; swim:entryStatus "official" ;
         swim:finalTimeSeconds ?time ; swim:timingEvidenceUri ?evidence .
  OPTIONAL { ?entry swim:placeRank ?rank }
}
ORDER BY ?event ?rank ?swimmer
~~~

### SWIM-04. 선수별로 영법·거리·수영장 길이마다 최고 공식 기록은 무엇인가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?swimmer ?stroke ?distance ?length (MIN(?time) AS ?best) (COUNT(DISTINCT ?entry) AS ?swims)
WHERE {
  ?entry a swim:Entry ; swim:forSwimmer ?swimmer ; swim:inEvent ?event ; swim:entryStatus "official" ; swim:finalTimeSeconds ?time .
  ?event swim:stroke ?stroke ; swim:distanceMeters ?distance .
  ?meet swim:hasEvent ?event ; swim:heldAt ?pool .
  ?pool swim:poolLengthMeters ?length .
}
GROUP BY ?swimmer ?stroke ?distance ?length
ORDER BY ?swimmer ?stroke ?distance ?length
~~~

### SWIM-05. 실격이나 기권으로 기록이 없는 출전은 무엇이며 사유와 증빙은 있는가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?entry ?swimmer ?event ?status ?reason ?evidence
WHERE {
  ?entry a swim:Entry ; swim:forSwimmer ?swimmer ; swim:inEvent ?event ; swim:entryStatus ?status .
  FILTER (?status IN ("disqualified", "did-not-start"))
  OPTIONAL { ?entry swim:disqualificationReason ?reason }
  OPTIONAL { ?entry swim:timingEvidenceUri ?evidence }
}
ORDER BY ?entry
~~~

### SWIM-06. 아직 경기를 치르지 않고 신청만 한 출전은 무엇이며 신청 기록은 얼마인가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?event ?swimmer ?seed
WHERE {
  ?entry a swim:Entry ; swim:inEvent ?event ; swim:forSwimmer ?swimmer ; swim:entryStatus "entered" ; swim:seedTimeSeconds ?seed .
}
ORDER BY ?event ?seed
~~~

### SWIM-07. 구간 기록이 있는 공식 기록은 각 거리에서 얼마였는가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?event ?swimmer ?distance ?time
WHERE {
  ?entry a swim:Entry ; swim:inEvent ?event ; swim:forSwimmer ?swimmer ; swim:hasSplit ?split .
  ?split a swim:Split ; swim:splitDistanceMeters ?distance ; swim:splitTimeSeconds ?time .
}
ORDER BY ?event ?swimmer ?distance
~~~

### SWIM-08. 선수는 어느 부문이며 어느 클럽에 소속되어 있는가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?swimmer ?category ?club
WHERE {
  ?swimmer a swim:Swimmer ; swim:competitionCategory ?category .
  OPTIONAL { ?swimmer swim:memberOf ?club . ?club a swim:Club }
}
ORDER BY ?swimmer
~~~

### SWIM-09. 선수의 부문과 종목의 부문이 맞지 않는 출전이 있는가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?entry ?swimmer ?swimmerCategory ?eventCategory
WHERE {
  ?entry a swim:Entry ; swim:forSwimmer ?swimmer ; swim:inEvent ?event .
  ?swimmer swim:competitionCategory ?swimmerCategory .
  ?event swim:eventCategory ?eventCategory .
  FILTER (?swimmerCategory != ?eventCategory)
}
ORDER BY ?entry
~~~

### SWIM-10. 종목 1위를 두 번 이상 한 선수는 누구인가?

~~~sparql
PREFIX swim: <https://example.org/ontology/custom/swimming#>
SELECT ?swimmer (COUNT(DISTINCT ?entry) AS ?wins)
WHERE {
  ?entry a swim:Entry ; swim:forSwimmer ?swimmer ; swim:entryStatus "official" ; swim:placeRank 1 .
}
GROUP BY ?swimmer
HAVING (COUNT(DISTINCT ?entry) > 1)
ORDER BY DESC(?wins) ?swimmer
~~~

예제의 고정 정답은 차례로 3·7·10·10·2·2·8·4·0·2행이다. SWIM-04에서 선수 A와 C의 자유형 100m는 25m 기록과 50m 기록이 따로 나오며, SWIM-09는 0행이어야 하는 무결성 점검이다.
