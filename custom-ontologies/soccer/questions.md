# 축구 업무 질문

화면에서는 `example.ttl`에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용하며 두 그래프의 개체 IRI는 저장 공간만 다르고 내용은 같다.
예제는 가상의 클럽 3곳, 선수 36명, 대회 2개, 경기 4개이며 실제 클럽이나 선수, 경기가 아니다. 경기 보고서의 `urn:synthetic:` 주소는 자리 표시용이다.
결과에 없는 경기나 사건은 아직 기록하지 않았다는 뜻이다. 자책골은 그 선수의 클럽이 아니라 상대 클럽의 득점으로 센다.

### SOC-01. 어떤 경기가 언제 어느 대회에서 누구와 누구 사이에 치러지며 상태와 결과는 어떠한가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?competition ?date ?home ?away ?status ?homeGoals ?awayGoals ?report
WHERE {
  ?match a soccer:Match ; soccer:inCompetition ?competition ; soccer:matchDate ?date ;
         soccer:homeClub ?home ; soccer:awayClub ?away ; soccer:matchStatus ?status .
  OPTIONAL { ?match soccer:homeGoals ?homeGoals }
  OPTIONAL { ?match soccer:awayGoals ?awayGoals }
  OPTIONAL { ?match soccer:matchReportUri ?report }
}
ORDER BY ?date ?match
~~~

### SOC-02. 종료된 경기만 볼 때 클럽별 경기 수, 득점, 실점은 얼마인가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?club (COUNT(DISTINCT ?match) AS ?played) (SUM(?scored) AS ?goalsFor) (SUM(?conceded) AS ?goalsAgainst)
WHERE {
  ?match a soccer:Match ; soccer:matchStatus "finished" .
  { ?match soccer:homeClub ?club ; soccer:homeGoals ?scored ; soccer:awayGoals ?conceded }
  UNION
  { ?match soccer:awayClub ?club ; soccer:awayGoals ?scored ; soccer:homeGoals ?conceded }
  ?club a soccer:Club .
}
GROUP BY ?club
ORDER BY ?club
~~~

### SOC-03. 득점한 선수는 누구이며 어느 클럽 소속으로 몇 골을 넣었는가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?player ?club (COUNT(DISTINCT ?event) AS ?goals)
WHERE {
  ?match soccer:hasEvent ?event ; soccer:hasAppearance ?appearance .
  ?event a soccer:MatchEvent ; soccer:eventType "goal" ; soccer:byPlayer ?player .
  ?appearance a soccer:Appearance ; soccer:forPlayer ?player ; soccer:forClub ?club .
  ?player a soccer:Player .
}
GROUP BY ?player ?club
ORDER BY DESC(?goals) ?player
~~~

### SOC-04. 득점이 아닌 사건(경고, 퇴장, 자책골)은 몇 분에 누가 일으켰는가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?minute ?type ?player ?club
WHERE {
  ?match soccer:hasEvent ?event ; soccer:hasAppearance ?appearance .
  ?event a soccer:MatchEvent ; soccer:eventType ?type ; soccer:eventMinute ?minute ; soccer:byPlayer ?player .
  ?appearance soccer:forPlayer ?player ; soccer:forClub ?club .
  FILTER (?type != "goal")
}
ORDER BY ?match ?minute
~~~

### SOC-05. 종료된 경기에서 클럽별 선발 선수는 몇 명인가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?club (COUNT(DISTINCT ?appearance) AS ?starters)
WHERE {
  ?match a soccer:Match ; soccer:matchStatus "finished" ; soccer:hasAppearance ?appearance .
  ?appearance a soccer:Appearance ; soccer:forClub ?club ; soccer:lineupRole "starter" .
}
GROUP BY ?match ?club
ORDER BY ?match ?club
~~~

### SOC-06. 교체 출전한 선수는 누구이며 몇 분에 들어갔고 언제 나갔는가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?club ?player ?in ?out
WHERE {
  ?match soccer:hasAppearance ?appearance .
  ?appearance a soccer:Appearance ; soccer:forClub ?club ; soccer:forPlayer ?player ; soccer:lineupRole "substitute" ; soccer:minuteIn ?in .
  OPTIONAL { ?appearance soccer:minuteOut ?out }
}
ORDER BY ?match ?in ?club
~~~

### SOC-07. 경기마다 선발 골키퍼는 누구이고 등번호는 몇 번인가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?club ?player ?shirt
WHERE {
  ?match soccer:hasAppearance ?appearance .
  ?appearance a soccer:Appearance ; soccer:forClub ?club ; soccer:forPlayer ?player ;
              soccer:lineupRole "starter" ; soccer:position "goalkeeper" ; soccer:shirtNumber ?shirt .
}
ORDER BY ?match ?club
~~~

### SOC-08. 대회는 어떤 종류이며 시즌과 교체 허용 인원, 경기 수는 어떠한가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?competition ?season ?type ?limit (COUNT(DISTINCT ?match) AS ?matches)
WHERE {
  ?competition a soccer:Competition ; soccer:season ?season ; soccer:competitionType ?type ; soccer:substitutionLimit ?limit .
  ?match a soccer:Match ; soccer:inCompetition ?competition .
}
GROUP BY ?competition ?season ?type ?limit
ORDER BY ?competition
~~~

### SOC-09. 아직 치르지 않았거나 연기되어 결과가 없는 경기는 무엇인가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?status ?date ?matchday
WHERE {
  ?match a soccer:Match ; soccer:matchStatus ?status ; soccer:matchDate ?date .
  FILTER (?status IN ("scheduled", "postponed"))
  OPTIONAL { ?match soccer:matchday ?matchday }
}
ORDER BY ?date ?match
~~~

### SOC-10. 기록된 점수가 득점 사건의 수와 다른 종료 경기가 있는가?

~~~sparql
PREFIX soccer: <https://example.org/ontology/custom/soccer#>
SELECT ?match ?club ?recorded (COUNT(DISTINCT ?event) AS ?counted)
WHERE {
  ?match a soccer:Match ; soccer:matchStatus "finished" .
  { ?match soccer:homeClub ?club ; soccer:homeGoals ?recorded } UNION { ?match soccer:awayClub ?club ; soccer:awayGoals ?recorded }
  OPTIONAL {
    ?match soccer:hasEvent ?event . ?event soccer:eventType ?type ; soccer:byPlayer ?player .
    ?match soccer:hasAppearance ?appearance . ?appearance soccer:forPlayer ?player ; soccer:forClub ?playerClub .
    FILTER ((?type = "goal" && ?playerClub = ?club) || (?type = "own-goal" && ?playerClub != ?club))
  }
}
GROUP BY ?match ?club ?recorded
HAVING (COUNT(DISTINCT ?event) != ?recorded)
ORDER BY ?match ?club
~~~

예제의 고정 정답은 차례로 4·3·4·4·4·4·4·2·2·0행이다. SOC-10은 0행이어야 하는 무결성 점검이며, SOC-03의 득점자에는 자책골이 들어가지 않는다.
