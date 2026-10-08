# 정치·선거 정보 역량 질문

예시 데이터는 가상 인물·정당·선거만 포함합니다. 쿼리는 중립적인 구조화 정보의 조회를 위한 것입니다.

### POL-01. 선거 일정과 선거구 조회

~~~sparql
PREFIX politics: <https://example.org/ontology/politics#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?electionLabel ?date ?districtLabel ?status WHERE {
  ?election a politics:Election ;
            rdfs:label ?electionLabel ;
            politics:electionDate ?date ;
            politics:electionStatus ?status ;
            politics:heldInDistrict ?district .
  ?district rdfs:label ?districtLabel .
  FILTER (lang(?electionLabel) = "ko" && lang(?districtLabel) = "ko")
}
ORDER BY ?date
~~~

### POL-02. 후보자와 정당별 집계 결과 조회

~~~sparql
PREFIX politics: <https://example.org/ontology/politics#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?electionLabel ?candidateLabel ?partyLabel ?votes ?tallyStatus WHERE {
  ?election a politics:Election ;
            rdfs:label ?electionLabel ;
            politics:hasResult ?result .
  ?result politics:resultForCandidate ?candidate ;
          politics:voteCount ?votes ;
          politics:resultStatus ?tallyStatus .
  ?candidate rdfs:label ?candidateLabel ;
             politics:memberParty ?party .
  ?party rdfs:label ?partyLabel .
  FILTER (lang(?candidateLabel) = "ko")
}
ORDER BY DESC(?votes)
~~~

### POL-03. 정책 입장과 그 출처 조회

~~~sparql
PREFIX politics: <https://example.org/ontology/politics#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?actorLabel ?issueLabel ?statement ?recordedAt ?source WHERE {
  ?position a politics:PolicyPosition ;
            politics:positionByActor ?actor ;
            politics:positionOnIssue ?issue ;
            politics:positionStatement ?statement ;
            politics:positionRecordedAt ?recordedAt ;
            politics:sourceURL ?source .
  ?actor rdfs:label ?actorLabel .
  ?issue rdfs:label ?issueLabel .
  FILTER (lang(?actorLabel) = "ko" && lang(?issueLabel) = "ko")
}
ORDER BY DESC(?recordedAt)
~~~

### POL-04. 후보자별 선거운동 행사 일정 조회

~~~sparql
PREFIX politics: <https://example.org/ontology/politics#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?candidateLabel ?campaignLabel ?eventLabel ?eventDate WHERE {
  ?campaign a politics:Campaign ;
            rdfs:label ?campaignLabel ;
            politics:runByActor ?candidate ;
            politics:hasCampaignEvent ?event .
  ?candidate a politics:Candidate ; rdfs:label ?candidateLabel .
  ?event rdfs:label ?eventLabel ; politics:eventDate ?eventDate .
  FILTER (lang(?candidateLabel) = "ko")
}
ORDER BY ?eventDate
~~~
