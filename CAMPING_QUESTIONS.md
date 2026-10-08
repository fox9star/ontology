# 캠핑 온톨로지 역량 질문

프로파일 UI의 SPARQL 템플릿으로 사용할 캠핑 계획 질문입니다.

### CAMP-01. 여행 일정과 목적지 야영장 조회

~~~sparql
PREFIX camping: <https://example.org/ontology/camping#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?tripLabel ?start ?end ?campgroundLabel WHERE {
  ?trip a camping:CampingTrip ;
        rdfs:label ?tripLabel ;
        camping:tripStartDate ?start ;
        camping:tripEndDate ?end ;
        camping:tripDestination ?campground .
  ?campground rdfs:label ?campgroundLabel .
  FILTER (lang(?tripLabel) = "ko" && lang(?campgroundLabel) = "ko")
}
ORDER BY ?start
~~~

### CAMP-02. 여행 준비물과 필요한 수량 조회

~~~sparql
PREFIX camping: <https://example.org/ontology/camping#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?tripLabel ?listLabel ?itemLabel ?equipmentLabel ?quantity WHERE {
  ?trip a camping:CampingTrip ;
        rdfs:label ?tripLabel ;
        camping:tripHasPackingList ?list .
  ?list rdfs:label ?listLabel ;
        camping:listHasItem ?item .
  ?item rdfs:label ?itemLabel ;
        camping:itemEquipment ?equipment ;
        camping:itemQuantity ?quantity .
  ?equipment rdfs:label ?equipmentLabel .
  FILTER (lang(?tripLabel) = "ko" && lang(?itemLabel) = "ko")
}
ORDER BY ?tripLabel ?itemLabel
~~~

### CAMP-03. 캠핑 사이트의 수용 인원과 소속 야영장 조회

~~~sparql
PREFIX camping: <https://example.org/ontology/camping#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?campgroundLabel ?siteLabel ?capacity WHERE {
  ?campground a camping:Campground ;
              rdfs:label ?campgroundLabel ;
              camping:hasCampsite ?site .
  ?site a camping:Campsite ;
        rdfs:label ?siteLabel ;
        camping:siteCapacity ?capacity ;
        camping:belongsToCampground ?campground .
  FILTER (lang(?siteLabel) = "ko")
}
ORDER BY DESC(?capacity)
~~~

### CAMP-04. 여행별 참가자와 예약한 사이트 조회

~~~sparql
PREFIX camping: <https://example.org/ontology/camping#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?tripLabel ?camperLabel ?reservationLabel ?siteLabel WHERE {
  ?trip a camping:CampingTrip ;
        rdfs:label ?tripLabel ;
        camping:tripHasParticipant ?camper ;
        camping:tripHasReservation ?reservation .
  ?camper rdfs:label ?camperLabel .
  ?reservation rdfs:label ?reservationLabel ;
               camping:reservationForSite ?site .
  ?site rdfs:label ?siteLabel .
  FILTER (lang(?tripLabel) = "ko" && lang(?camperLabel) = "ko")
}
ORDER BY ?tripLabel ?camperLabel
~~~
