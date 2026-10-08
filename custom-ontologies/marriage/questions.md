# 결혼·결혼식 탐색 질문

모든 초기 인물·행사·초대 응답·예약·금액은 가상 예제입니다. 결혼 정보 기록은 행사 일정과 독립적이며 법적 혼인 상태를 판정하지 않습니다.
`example.ttl`은 화면용 개체 IRI를, `question-fixture.ttl`은 별도 고정 IRI를 사용합니다.
수용 인원 비교에는 수락한 초대 그룹의 기록된 인원만 포함합니다. 취소된 비용과 작업은 준비 조건에서 제외합니다.

### MAR-01. 계획·당사자와 별도로 기록한 결혼 정보는 무엇인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plan ?name ?recordKind ?status ?coordinator ?budget ?currency ?note ?marriageInfoStatus ?marriageDate ?marriageInfoNote ?marriageInfoSource
WHERE {
  ?plan a marriage:MarriagePlan ; rdfs:label ?name ; marriage:recordKind ?recordKind ; marriage:status ?status ;
    marriage:coordinatedBy ?coordinator ; marriage:budgetAmount ?budget ; marriage:currency ?currency ;
    marriage:planNote ?note ; marriage:marriageInfoStatus ?marriageInfoStatus .
  FILTER (LANG(?name) = "ko")
  OPTIONAL { ?plan marriage:marriageDate ?marriageDate }
  OPTIONAL { ?plan marriage:marriageInfoNote ?marriageInfoNote }
  OPTIONAL { ?plan marriage:marriageInfoSourceUri ?marriageInfoSource }
}
ORDER BY ?plan
~~~

### MAR-02. 계획에 등록된 인물과 역할은 무엇인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plan ?person ?name ?note ?isPartner ?isCoordinator
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:hasPerson ?person .
  ?person a marriage:Person ; rdfs:label ?name ; marriage:personNote ?note .
  FILTER (LANG(?name) = "ko")
  BIND (IF(EXISTS { ?plan marriage:hasPartner ?person }, "yes", "no") AS ?isPartner)
  BIND (IF(EXISTS { ?plan marriage:coordinatedBy ?person }, "yes", "no") AS ?isCoordinator)
}
ORDER BY ?plan ?person
~~~

### MAR-03. 행사는 어떤 순서·시간·장소에서 진행하고 수용 인원은 얼마인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?plan ?event ?sequence ?kind ?start ?end ?note ?venue ?venueLabel ?venueKind ?capacity ?locationNote
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:hasCeremony ?event .
  ?event a marriage:Ceremony ; marriage:sequence ?sequence ; marriage:eventKind ?kind ;
    marriage:eventStartsAt ?start ; marriage:eventEndsAt ?end ; marriage:eventNote ?note ; marriage:atVenue ?venue .
  ?venue a marriage:Venue ; rdfs:label ?venueLabel ; marriage:venueKind ?venueKind ;
    marriage:capacity ?capacity ; marriage:locationNote ?locationNote .
  FILTER (LANG(?venueLabel) = "ko")
}
ORDER BY ?plan ?sequence ?event
~~~

### MAR-04. 초대의 응답 상태·그룹 인원·응답 시각은 무엇인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
SELECT ?plan ?invitation ?person ?event ?status ?partySize ?responseAt
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:hasInvitation ?invitation .
  ?invitation a marriage:Invitation ; marriage:invitedPerson ?person ; marriage:forEvent ?event ; marriage:rsvpStatus ?status .
  OPTIONAL { ?invitation marriage:partySize ?partySize }
  OPTIONAL { ?invitation marriage:responseRecordedAt ?responseAt }
}
ORDER BY ?plan ?invitation
~~~

### MAR-05. 준비 작업의 담당자·마감·완료·선행 관계는 무엇인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
SELECT ?plan ?task ?assignee ?dueAt ?status ?note ?completedAt ?dependency
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:hasTask ?task .
  ?task a marriage:PreparationTask ; marriage:assignedTo ?assignee ; marriage:dueAt ?dueAt ;
    marriage:taskStatus ?status ; marriage:taskNote ?note .
  OPTIONAL { ?task marriage:completedAt ?completedAt }
  OPTIONAL { ?task marriage:dependsOn ?dependency }
}
ORDER BY ?plan ?task ?dependency
~~~

### MAR-06. 서비스 예약의 제공자·필수 여부·상태·확인 근거는 무엇인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
SELECT ?plan ?booking ?kind ?event ?status ?provider ?confirmation ?note ?required
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:hasBooking ?booking .
  ?booking a marriage:ServiceBooking ; marriage:serviceKind ?kind ; marriage:bookedFor ?event ;
    marriage:bookingStatus ?status ; marriage:providerLabel ?provider ; marriage:bookingNote ?note ; marriage:isRequired ?required .
  OPTIONAL { ?booking marriage:confirmationUri ?confirmation }
}
ORDER BY ?plan ?booking
~~~

### MAR-07. 예정·지불·취소 비용과 잔여 예산은 얼마인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
SELECT ?plan ?expense ?kind ?status ?amount ?note ?budget ?currency ?committed ?remaining
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:hasExpense ?expense ; marriage:budgetAmount ?budget ; marriage:currency ?currency .
  ?expense a marriage:Expense ; marriage:expenseKind ?kind ; marriage:expenseStatus ?status ;
    marriage:amount ?amount ; marriage:expenseNote ?note .
  OPTIONAL {
    SELECT ?plan (SUM(?activeAmount) AS ?activeTotal)
    WHERE {
      ?plan marriage:hasExpense ?activeExpense .
      ?activeExpense marriage:expenseStatus ?activeStatus ; marriage:amount ?activeAmount .
      FILTER (?activeStatus IN ("planned", "paid"))
    }
    GROUP BY ?plan
  }
  BIND (COALESCE(?activeTotal, 0) AS ?committed)
  BIND (?budget - ?committed AS ?remaining)
}
ORDER BY ?plan ?expense
~~~

### MAR-08. 준비 상태를 막는 항목은 무엇인가?

~~~sparql
PREFIX marriage: <https://example.org/ontology/custom/marriage#>
SELECT ?plan ?blocker ?detail
WHERE {
  ?plan a marriage:MarriagePlan ; marriage:status ?planStatus .
  FILTER (?planStatus != "cancelled")
  {
    ?plan marriage:hasTask ?task .
    ?task marriage:taskStatus ?taskStatus .
    FILTER (?taskStatus NOT IN ("completed", "cancelled"))
    BIND ("task-incomplete" AS ?blocker)
    BIND (STR(?task) AS ?detail)
  }
  UNION {
    ?plan marriage:hasBooking ?booking .
    ?booking marriage:isRequired true ; marriage:bookingStatus ?bookingStatus .
    FILTER (?bookingStatus != "confirmed")
    BIND ("required-booking-unconfirmed" AS ?blocker)
    BIND (STR(?booking) AS ?detail)
  }
  UNION {
    ?plan marriage:hasInvitation ?invitation .
    ?invitation marriage:rsvpStatus "pending" .
    BIND ("invitation-pending" AS ?blocker)
    BIND (STR(?invitation) AS ?detail)
  }
  UNION {
    {
      SELECT ?plan ?event (SUM(?partySize) AS ?acceptedCount)
      WHERE {
        ?plan marriage:hasInvitation ?acceptedInvitation .
        ?acceptedInvitation marriage:rsvpStatus "accepted" ; marriage:forEvent ?event ; marriage:partySize ?partySize .
      }
      GROUP BY ?plan ?event
    }
    ?plan marriage:hasCeremony ?event .
    ?event marriage:atVenue ?venue .
    ?venue marriage:capacity ?capacity .
    FILTER (?acceptedCount > ?capacity)
    BIND ("invitation-capacity-exceeded" AS ?blocker)
    BIND (STR(?event) AS ?detail)
  }
  UNION {
    {
      SELECT ?plan (SUM(?amount) AS ?committed)
      WHERE {
        ?plan marriage:hasExpense ?expense .
        ?expense marriage:expenseStatus ?expenseStatus ; marriage:amount ?amount .
        FILTER (?expenseStatus IN ("planned", "paid"))
      }
      GROUP BY ?plan
    }
    ?plan marriage:budgetAmount ?budget .
    FILTER (?committed > ?budget)
    BIND ("budget-exceeded" AS ?blocker)
    BIND (STR(?committed - ?budget) AS ?detail)
  }
}
ORDER BY ?plan ?blocker ?detail
~~~
