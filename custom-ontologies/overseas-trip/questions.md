# 해외여행 계획 업무 질문

화면에서는 `example.ttl`의 합성 여행 계획에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용한다. 두 그래프의 예시 개체 IRI는 저장 공간을 구분하며 업무 구조는 같다. 순서는 일차 번호와 하루 안의 활동 순번으로 해석한다.
입국 요건의 확인 여부와 예약의 확정 여부를 구분하며, 요건이나 예약 기록이 없다는 사실은 입국 가능이나 예약 성사의 증거가 아니다.

### TRIP-01. 어느 날 어느 도시에서 어떤 활동을 몇 분 동안 할 계획인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?dayNumber ?date ?city ?countryCode ?countryName ?activityOrder ?activity ?category ?minutes
WHERE {
  ?plan a trip:TripPlan ; trip:hasItineraryDay ?day .
  ?day a trip:ItineraryDay ; trip:dayNumber ?dayNumber ; trip:dayDate ?date ; trip:cityName ?city ;
       trip:atDestination ?destination ; trip:hasActivity ?activity .
  ?destination a trip:Destination ; trip:countryCode ?countryCode ; trip:countryName ?countryName .
  ?activity a trip:Activity ; trip:activityOrder ?activityOrder ; trip:activityCategory ?category ;
            trip:plannedDurationMinutes ?minutes .
}
ORDER BY ?plan ?dayNumber ?activityOrder
~~~

### TRIP-02. 입국 전에 확인했다는 근거가 아직 없는 입국 요건은 무엇인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?countryCode ?requirement ?kind ?status ?evidence ?traveler
WHERE {
  ?plan a trip:TripPlan ; trip:hasDestination ?destination .
  ?destination a trip:Destination ; trip:countryCode ?countryCode ; trip:hasEntryRequirement ?requirement .
  ?requirement a trip:EntryRequirement ; trip:requirementKind ?kind ; trip:checkStatus ?status .
  OPTIONAL { ?requirement trip:checkEvidenceUri ?evidence }
  OPTIONAL { ?requirement trip:appliesToTraveler ?traveler }
  FILTER (?status = "unchecked" || !BOUND(?evidence))
}
ORDER BY ?plan ?countryCode ?kind ?requirement
~~~

`traveler`가 비어 있는 요건은 일행 전체에 대한 요건이다.

### TRIP-03. 예약은 어떤 종류와 기간이며 확정 근거와 뒷받침하는 활동은 무엇인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?booking ?kind ?status ?start ?end ?confirmation ?activity
WHERE {
  ?plan a trip:TripPlan ; trip:hasBooking ?booking .
  ?booking a trip:Booking ; trip:bookingKind ?kind ; trip:bookingStatus ?status ;
           trip:bookingStartDate ?start ; trip:bookingEndDate ?end .
  OPTIONAL { ?booking trip:confirmationEvidenceUri ?confirmation }
  OPTIONAL { ?booking trip:coversActivity ?activity }
}
ORDER BY ?plan ?start ?booking
~~~

### TRIP-04. 통화별·범주별 계획 예산은 얼마이며 그중 예약에 연결된 항목은 몇 건인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?currency ?category (COUNT(DISTINCT ?item) AS ?items) (COUNT(DISTINCT ?booking) AS ?linkedBookings) (SUM(?amount) AS ?total)
WHERE {
  ?plan a trip:TripPlan ; trip:hasBudgetItem ?item .
  ?item a trip:BudgetItem ; trip:budgetCategory ?category ; trip:plannedAmount ?amount ; trip:currencyCode ?currency .
  OPTIONAL { ?item trip:forBooking ?booking }
}
GROUP BY ?plan ?currency ?category
ORDER BY ?plan ?currency ?category
~~~

### TRIP-05. 여행 계획의 확정을 막고 있는 입국 요건과 예약은 무엇인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?status ?departure ?return ?travelers ?blocker ?item
WHERE {
  ?plan a trip:TripPlan ; trip:planStatus ?status ; trip:departureDate ?departure ;
        trip:returnDate ?return ; trip:travelerCount ?travelers .
  {
    ?plan trip:hasDestination ?destination .
    ?destination trip:hasEntryRequirement ?item .
    ?item trip:checkStatus "unchecked" .
    BIND ("entry-requirement-unchecked" AS ?blocker)
  } UNION {
    ?plan trip:hasBooking ?item .
    ?item a trip:Booking .
    FILTER NOT EXISTS { ?item trip:bookingStatus "booked" ; trip:confirmationEvidenceUri ?confirmation }
    BIND ("booking-unconfirmed" AS ?blocker)
  }
}
ORDER BY ?plan ?blocker ?item
~~~

### TRIP-06. 항공 예약은 어떤 구간을 어떤 순서와 날짜로 비행하는가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?booking ?status ?segmentOrder ?from ?to ?departureDate ?arrivalDate
WHERE {
  ?plan a trip:TripPlan ; trip:hasBooking ?booking .
  ?booking a trip:Booking ; trip:bookingStatus ?status ; trip:hasFlightSegment ?segment .
  ?segment a trip:FlightSegment ; trip:segmentOrder ?segmentOrder ; trip:departureAirport ?from ;
           trip:arrivalAirport ?to ; trip:segmentDepartureDate ?departureDate ; trip:segmentArrivalDate ?arrivalDate .
}
ORDER BY ?plan ?booking ?segmentOrder
~~~

### TRIP-07. 함께 여행하는 동반자는 누구이며 각자에게 적용되는 입국 요건은 무엇인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?traveler ?role ?ageGroup ?nationality ?requirement ?kind ?status
WHERE {
  ?plan a trip:TripPlan ; trip:hasTraveler ?traveler .
  ?traveler a trip:Traveler ; trip:travelerRole ?role ; trip:ageGroup ?ageGroup .
  OPTIONAL { ?traveler trip:nationalityCode ?nationality }
  OPTIONAL { ?requirement trip:appliesToTraveler ?traveler ; trip:requirementKind ?kind ; trip:checkStatus ?status }
}
ORDER BY ?plan ?traveler ?kind ?requirement
~~~

### TRIP-08. 보험은 어떤 종류를 어느 한도로 어떤 동반자에게 보장하는가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?booking ?bookingStatus ?policy ?coverage ?limit ?currency ?traveler
WHERE {
  ?plan a trip:TripPlan ; trip:hasBooking ?booking .
  ?booking a trip:Booking ; trip:bookingStatus ?bookingStatus ; trip:hasInsurancePolicy ?policy .
  ?policy a trip:InsurancePolicy ; trip:coverageKind ?coverage ; trip:coverageLimitAmount ?limit ;
          trip:coverageLimitCurrency ?currency ; trip:coversTraveler ?traveler .
}
ORDER BY ?plan ?booking ?coverage ?traveler
~~~

### TRIP-09. 취소되지 않은 보험에서 의료 보장을 받지 못하는 동반자는 누구인가?

~~~sparql
PREFIX trip: <https://example.org/ontology/custom/overseas-trip#>
SELECT ?plan ?traveler ?role ?ageGroup
WHERE {
  ?plan a trip:TripPlan ; trip:hasTraveler ?traveler .
  ?traveler a trip:Traveler ; trip:travelerRole ?role ; trip:ageGroup ?ageGroup .
  FILTER NOT EXISTS {
    ?plan trip:hasBooking ?booking .
    ?booking trip:bookingStatus ?bookingStatus ; trip:hasInsurancePolicy ?policy .
    FILTER (?bookingStatus != "cancelled")
    ?policy trip:coverageKind "medical" ; trip:coversTraveler ?traveler .
  }
}
ORDER BY ?plan ?traveler
~~~

합성 계획의 고정 정답은 각각 6행, 3행, 4행, 4행, 7행, 2행, 2행, 2행, 1행이다. TRIP-05는 별도 합성 확정 시나리오에서 세 입국 요건에 확인 근거를 넣고 네 예약을 확정하면 0행으로 바뀌고, 근거 하나를 제거하면 다시 1행이 되는지 검사한다. TRIP-09는 동반자 B를 보험에 추가하면 0행으로 바뀌고 보험을 취소하면 두 동반자 모두 나타나는지 검사한다.
