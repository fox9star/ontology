# 제1차 세계대전 업무 질문

화면에서는 `example.ttl`에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용하며 두 그래프의 개체 IRI는 저장 공간만 다르고 내용은 같다.
예제는 널리 알려진 사실을 간추린 **초안**이다. 12개 국가·12개 전투·6개 협정만 담았고 전투의 교전국과 지휘관은 주요 인물만 적었으며, 모든 기록은 출처를 대조하기 전이라 `unverified`로 표시한다.
따라서 결과에 없는 국가·전투·협정은 존재하지 않는다는 뜻이 아니라 아직 기록하지 않았다는 뜻이다. 전투 결과는 거친 구분이며 평가가 갈리면 `contested`를 쓴다.

### WW1-01. 어떤 국가가 어떤 진영으로 언제, 어떤 사건을 계기로 전쟁에 들어갔는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?conflict ?state ?form ?side ?entry ?trigger ?kind
WHERE {
  ?p a ww1:Participation ; ww1:inConflict ?conflict ; ww1:participant ?state ; ww1:onSide ?side ; ww1:entryDate ?entry ; ww1:enteredVia ?trigger .
  ?conflict a ww1:Conflict .
  ?state a ww1:State ; ww1:governmentForm ?form .
  ?side a ww1:Side .
  ?trigger a ww1:Event ; ww1:eventKind ?kind .
}
ORDER BY ?entry ?state
~~~

### WW1-02. 전쟁이 끝나기 전에 교전을 마친 국가는 언제 어떤 협정으로 이탈했는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?state ?exit ?agreement ?kind ?fightingEnd
WHERE {
  ?p a ww1:Participation ; ww1:participant ?state ; ww1:inConflict ?conflict ; ww1:exitDate ?exit ; ww1:endedByAgreement ?agreement .
  ?conflict a ww1:Conflict ; ww1:conflictEndDate ?fightingEnd .
  ?agreement a ww1:Agreement ; ww1:agreementKind ?kind .
  FILTER (?exit < ?fightingEnd)
}
ORDER BY ?exit ?state
~~~

### WW1-03. 개전 전 동맹이 이어진 진영과 다른 진영으로 참전한 국가는 어디인가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?alliance ?state ?expectedSide ?actualSide ?entry
WHERE {
  ?alliance a ww1:Alliance ; ww1:hasMember ?state ; ww1:correspondingSide ?expectedSide .
  ?p a ww1:Participation ; ww1:participant ?state ; ww1:onSide ?actualSide ; ww1:entryDate ?entry .
  ?actualSide a ww1:Side .
  FILTER (?expectedSide != ?actualSide)
}
ORDER BY ?alliance ?state
~~~

### WW1-04. 전선별로 어떤 전투가 언제 어디서 벌어졌고 결과는 어떻게 기록되어 있는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?theatre ?battle ?start ?end ?outcome ?place
WHERE {
  ?theatre a ww1:Theatre .
  ?battle a ww1:Event ; ww1:eventKind "battle" ; ww1:inTheatre ?theatre ; ww1:startDate ?start ; ww1:endDate ?end ; ww1:outcome ?outcome .
  OPTIONAL { ?battle ww1:locationName ?place }
}
ORDER BY ?theatre ?start ?battle
~~~

### WW1-05. 각 전투에서 진영별로 몇 개 국가가 싸웠는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?battle ?side (COUNT(DISTINCT ?state) AS ?states)
WHERE {
  ?battle a ww1:Event ; ww1:eventKind "battle" ; ww1:hasBelligerent ?p .
  ?p a ww1:Participation ; ww1:participant ?state ; ww1:onSide ?side .
}
GROUP BY ?battle ?side
ORDER BY ?battle ?side
~~~

### WW1-06. 둘 이상의 전투를 지휘한 인물은 누구이며 어느 국가에서 복무했고 생존 연도는 언제인가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?commander ?state ?born ?died (COUNT(DISTINCT ?battle) AS ?battles)
WHERE {
  ?battle a ww1:Event ; ww1:eventKind "battle" ; ww1:hadCommander ?commander .
  ?commander a ww1:Person ; ww1:servedState ?state ; ww1:birthYear ?born .
  OPTIONAL { ?commander ww1:deathYear ?died }
}
GROUP BY ?commander ?state ?born ?died
HAVING (COUNT(DISTINCT ?battle) > 1)
ORDER BY DESC(?battles) ?commander
~~~

### WW1-07. 교전이 멈춘 날과 강화 조약의 서명일·발효일은 어떻게 다른가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?conflict ?start ?fightingEnd ?treaty ?signed ?inForce
WHERE {
  ?conflict a ww1:Conflict ; ww1:conflictStartDate ?start ; ww1:conflictEndDate ?fightingEnd .
  ?treaty a ww1:Agreement ; ww1:agreementKind "peace-treaty" ; ww1:signedDate ?signed .
  OPTIONAL { ?treaty ww1:inForceDate ?inForce }
}
ORDER BY ?signed ?treaty
~~~

### WW1-08. 전쟁의 계기가 된 사건과 선전포고·침공·공격은 시간순으로 어떻게 이어졌는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?date ?event ?kind ?actor ?target
WHERE {
  ?event a ww1:Event ; ww1:eventKind ?kind ; ww1:startDate ?date ; ww1:relatedConflict ?conflict .
  ?conflict a ww1:Conflict .
  FILTER (?kind != "battle")
  OPTIONAL { ?event ww1:initiatedBy ?actor }
  OPTIONAL { ?event ww1:directedAgainst ?target }
}
ORDER BY ?date ?event
~~~

### WW1-09. 각 휴전·강화 협정은 언제 서명되었고 당사국이 몇 개 기록되어 있는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?agreement ?kind ?signed (COUNT(DISTINCT ?party) AS ?parties)
WHERE {
  ?agreement a ww1:Agreement ; ww1:agreementKind ?kind ; ww1:signedDate ?signed ; ww1:hasParty ?party .
}
GROUP BY ?agreement ?kind ?signed
ORDER BY ?signed ?agreement
~~~

### WW1-10. 참전은 기록했지만 참여한 전투가 아직 하나도 기록되지 않은 국가는 어디인가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?state ?side
WHERE {
  ?p a ww1:Participation ; ww1:participant ?state ; ww1:onSide ?side .
  FILTER NOT EXISTS { ?battle a ww1:Event ; ww1:eventKind "battle" ; ww1:hasBelligerent ?p }
}
ORDER BY ?state
~~~

### WW1-11. 출처 확인 상태별로 기록이 몇 건인가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?status (COUNT(DISTINCT ?claim) AS ?claims)
WHERE {
  ?claim a ww1:HistoricalClaim ; ww1:verificationStatus ?status .
}
GROUP BY ?status
ORDER BY ?status
~~~

### WW1-12. 출처 확인을 마친 기록은 어떤 출처로 뒷받침되는가?

~~~sparql
PREFIX ww1: <https://example.org/ontology/custom/ww1#>
SELECT ?claim ?source ?citation ?uri
WHERE {
  ?claim a ww1:HistoricalClaim ; ww1:verificationStatus "source-checked" ; ww1:supportedBy ?source .
  ?source a ww1:SourceReference ; ww1:citationText ?citation .
  OPTIONAL { ?source ww1:sourceUri ?uri }
}
ORDER BY ?claim ?source
~~~

예제의 고정 정답은 차례로 12·4·1·12·24·5·2·11·6·3·1·0행이다. 마지막 질문은 예제에 출처가 하나도 없어 비어 있으며, 별도 합성 출처를 연결한 테스트에서만 행이 생긴다. WW1-10은 예제가 모든 참전국의 전투를 포함하지 않는다는 점, 즉 기록의 범위를 드러내는 질문이다.
