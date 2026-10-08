# 소풍 탐색 질문

초기 소풍·장소·참가자·일정·준비물·금액은 모두 가상 예제입니다. 실제 장소 정보, 가격, 날씨 예보를 수집한 자료가 아닙니다.
`example.ttl`은 화면용 개체 IRI를, `question-fixture.ttl`은 별도 고정 IRI를 사용합니다.
취소된 비용은 배정 비용 합계에서 제외합니다. 준비물의 수량은 각 항목의 기록된 단위 안에서 비교합니다.

### PIC-01. 소풍의 날짜·시간·장소·예산과 계획 상태는 무엇인가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plan ?name ?recordKind ?date ?start ?end ?status ?place ?placeLabel ?placeKind ?locationNote ?budget ?currency ?note
WHERE {
  ?plan a picnic:PicnicPlan ; rdfs:label ?name ; picnic:recordKind ?recordKind ; picnic:picnicDate ?date ;
    picnic:startsAt ?start ; picnic:endsAt ?end ; picnic:status ?status ; picnic:hasPlace ?place ;
    picnic:budgetAmount ?budget ; picnic:currency ?currency ; picnic:planNote ?note .
  FILTER (LANG(?name) = "ko")
  ?place a picnic:Place ; rdfs:label ?placeLabel ; picnic:placeKind ?placeKind ; picnic:locationNote ?locationNote .
  FILTER (LANG(?placeLabel) = "ko")
}
ORDER BY ?plan
~~~

### PIC-02. 각 소풍의 참가자와 역할은 무엇인가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plan ?participant ?name ?role ?note
WHERE {
  ?plan a picnic:PicnicPlan ; picnic:hasParticipant ?participant .
  ?participant a picnic:Participant ; rdfs:label ?name ; picnic:role ?role ; picnic:participantNote ?note .
  FILTER (LANG(?name) = "ko")
}
ORDER BY ?plan ?participant
~~~

### PIC-03. 소풍 일정은 어떤 순서와 시간으로 구성되는가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
SELECT ?plan ?activity ?sequence ?kind ?start ?end ?note
WHERE {
  ?plan a picnic:PicnicPlan ; picnic:hasActivity ?activity .
  ?activity a picnic:Activity ; picnic:sequence ?sequence ; picnic:activityKind ?kind ;
    picnic:activityStart ?start ; picnic:activityEnd ?end ; picnic:activityNote ?note .
}
ORDER BY ?plan ?sequence ?activity
~~~

### PIC-04. 준비물은 얼마나 준비되었고 누가 담당하는가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plan ?supply ?name ?kind ?required ?packed ?unit ?shortage ?participant
WHERE {
  ?plan a picnic:PicnicPlan ; picnic:hasSupply ?supply .
  ?supply a picnic:SupplyItem ; rdfs:label ?name ; picnic:supplyKind ?kind ;
    picnic:requiredQuantity ?required ; picnic:packedQuantity ?packed ; picnic:unit ?unit .
  FILTER (LANG(?name) = "ko")
  BIND (IF(?required > ?packed, ?required - ?packed, 0) AS ?shortage)
  OPTIONAL {
    ?plan picnic:hasAssignment ?assignment .
    ?assignment a picnic:Assignment ; picnic:assignedSupply ?supply ; picnic:assignedTo ?participant .
    ?plan picnic:hasParticipant ?participant .
  }
}
ORDER BY ?plan ?supply ?participant
~~~

### PIC-05. 비용 상태별 항목과 취소 비용을 제외한 남은 예산은 얼마인가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
SELECT ?plan ?expense ?kind ?status ?amount ?note ?budget ?currency ?committed ?remaining
WHERE {
  ?plan a picnic:PicnicPlan ; picnic:hasExpense ?expense ; picnic:budgetAmount ?budget ; picnic:currency ?currency .
  ?expense a picnic:Expense ; picnic:expenseKind ?kind ; picnic:expenseStatus ?status ;
    picnic:amount ?amount ; picnic:expenseNote ?note .
  {
    SELECT ?plan (SUM(?includedAmount) AS ?committed)
    WHERE {
      ?plan a picnic:PicnicPlan .
      OPTIONAL {
        ?plan picnic:hasExpense ?included .
        ?included picnic:expenseStatus ?includedStatus ; picnic:amount ?includedAmount .
        FILTER (?includedStatus != "cancelled")
      }
    }
    GROUP BY ?plan
  }
  BIND (?budget - ?committed AS ?remaining)
}
ORDER BY ?plan ?expense
~~~

### PIC-06. 해당 소풍 날짜의 날씨 정보는 확인되었는가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
SELECT ?plan ?weather ?date ?status ?checkedAt ?source ?summary
WHERE {
  ?plan a picnic:PicnicPlan ; picnic:hasWeatherCheck ?weather .
  ?weather a picnic:WeatherCheck ; picnic:forDate ?date ; picnic:checkStatus ?status ; picnic:weatherSummary ?summary .
  OPTIONAL { ?weather picnic:checkedAt ?checkedAt }
  OPTIONAL { ?weather picnic:sourceUri ?source }
}
ORDER BY ?plan ?weather
~~~

### PIC-07. 준비 상태 기록을 완료하기 전에 남아 있는 항목은 무엇인가?

~~~sparql
PREFIX picnic: <https://example.org/ontology/custom/picnic#>
SELECT ?plan ?blocker ?detail
WHERE {
  ?plan a picnic:PicnicPlan ; picnic:status ?planStatus .
  FILTER (?planStatus != "cancelled")
  {
    ?plan picnic:hasSupply ?supply .
    ?supply picnic:requiredQuantity ?required ; picnic:packedQuantity ?packed .
    FILTER (?packed < ?required)
    BIND ("packing-shortage" AS ?blocker)
    BIND (STR(?supply) AS ?detail)
  } UNION {
    ?plan picnic:hasSupply ?supply .
    FILTER NOT EXISTS {
      ?plan picnic:hasAssignment ?assignment ; picnic:hasParticipant ?participant .
      ?assignment picnic:assignedSupply ?supply ; picnic:assignedTo ?participant .
    }
    BIND ("supply-unassigned" AS ?blocker)
    BIND (STR(?supply) AS ?detail)
  } UNION {
    ?plan picnic:hasWeatherCheck ?weather .
    ?weather picnic:checkStatus "unverified" .
    BIND ("weather-unverified" AS ?blocker)
    BIND (STR(?weather) AS ?detail)
  } UNION {
    {
      SELECT ?plan (SUM(?amount) AS ?committed)
      WHERE {
        ?plan picnic:hasExpense ?expense .
        ?expense picnic:expenseStatus ?expenseStatus ; picnic:amount ?amount .
        FILTER (?expenseStatus != "cancelled")
      }
      GROUP BY ?plan
    }
    ?plan picnic:budgetAmount ?budget .
    FILTER (?committed > ?budget)
    BIND ("budget-exceeded" AS ?blocker)
    BIND (STR(?committed - ?budget) AS ?detail)
  }
}
ORDER BY ?plan ?blocker ?detail
~~~

기대 결과는 구조화 원자료에서 별도로 작성했습니다.
`ready`는 기록상 준비 항목이 갖춰진 상태입니다. 장소·날씨·활동의 실제 적합성을 인증하는 값이 아닙니다.
