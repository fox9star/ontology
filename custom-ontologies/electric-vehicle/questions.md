# 전기자동차 온톨로지 역량 질문

차량 구분, 구동계, 에너지 흐름, 충전 인프라와 출처 근거를 조회한다. 차량 기록은 상용 차종이 아닌 유형 예시이며 충전 인프라는 합성 데이터다.

### EV-01. BEV·PHEV·HEV는 외부 충전 여부와 추진 방식에서 어떻게 구분되는가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?vehicle ?label ?plugIn ?propulsion WHERE {
  ?vehicle a ev:ElectrifiedVehicle ; ev:vehiclePlugInChargeable ?plugIn ; ev:vehiclePropulsionMode ?propulsion ; rdfs:label ?label .
  FILTER(lang(?label) = "ko")
} ORDER BY ?vehicle
~~~

### EV-02. 배터리 전기차 유형에 연결한 구동계 구성품은 무엇인가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?component ?label ?role WHERE {
  ev:vehicle-bev-pattern ev:vehicleHasComponent ?component . ?component ev:componentRole ?role ; rdfs:label ?label .
  FILTER(lang(?label) = "ko")
} ORDER BY ?component
~~~

### EV-03. PHEV와 HEV의 충전 에너지원은 어떻게 다른가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?vehicle ?source WHERE {
  VALUES ?vehicle { ev:vehicle-phev-pattern ev:vehicle-hev-pattern } ?vehicle ev:vehicleChargingEnergySource ?source .
} ORDER BY ?vehicle ?source
~~~

### EV-04. AC 충전에서 설비부터 구동 배터리까지의 에너지 경로는 무엇인가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?flow ?source ?destination ?form WHERE {
  ?flow a ev:EnergyFlow ; ev:energyFlowSource ?source ; ev:energyFlowDestination ?destination ; ev:energyFlowForm ?form .
  FILTER(?flow IN (ev:flow-ac-evse-onboard, ev:flow-onboard-battery))
} ORDER BY ?flow
~~~

### EV-05. 회생 제동 에너지는 어떤 구성품 사이에서 흐르는가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?destination ?form WHERE {
  ev:flow-regeneration-battery ev:energyFlowSource ?source ; ev:energyFlowDestination ?destination ; ev:energyFlowForm ?form .
}
~~~

### EV-06. 충전소 위치와 EVSE 포트·커넥터의 관계는 무엇인가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?station ?port ?connector ?current WHERE {
  ?station ev:stationHasPort ?port . ?port ev:portHasConnector ?connector ; ev:portOutputCurrentType ?current .
} ORDER BY ?port
~~~

### EV-07. 합성 충전 세션은 어떤 차량·포트·커넥터와 상태를 기록하는가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?vehicle ?port ?connector ?current ?state WHERE {
  ev:session-example ev:sessionVehicle ?vehicle ; ev:sessionEVSEPort ?port ; ev:sessionConnector ?connector ;
    ev:sessionCurrentType ?current ; ev:sessionState ?state .
}
~~~

### EV-08. AC 충전의 차량 탑재 충전기 기능을 어떤 출처가 뒷받침하는가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?claim ?source ?url WHERE {
  ev:component-onboard-charger ev:componentHasEvidence ev:e-doe-ac-path .
  ev:e-doe-ac-path ev:evidenceClaim ?claim ; ev:evidenceSource ?doc . ?doc ev:sourceTitle ?source ; ev:sourceURL ?url .
  FILTER(lang(?claim) = "ko" && lang(?source) = "ko")
}
~~~

### EV-09. 구동계 구성품의 기능과 근거 기록은 무엇인가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?component ?role ?function ?evidence WHERE {
  ?component a ev:PowertrainComponent ; ev:componentRole ?role ; ev:componentFunction ?function ; ev:componentHasEvidence ?evidence .
  FILTER(lang(?function) = "ko")
} ORDER BY ?component ?evidence
~~~

### EV-10. 충전 시간에 영향을 주는 요인을 어떤 출처가 설명하는가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?claim ?source ?url WHERE {
  ev:e-charge-factors ev:evidenceClaim ?claim ; ev:evidenceSource ?doc . ?doc ev:sourceTitle ?source ; ev:sourceURL ?url .
  FILTER(lang(?claim) = "ko" && lang(?source) = "ko")
}
~~~

### EV-11. 온톨로지의 포함·제한·제외 범위는 무엇인가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?status ?label ?explanation WHERE {
  ?note a ev:CoverageNote ; ev:coverageStatus ?status ; ev:coverageLabel ?label ; ev:coverageExplanation ?explanation .
  FILTER(lang(?label) = "ko" && lang(?explanation) = "ko")
} ORDER BY ?status ?label
~~~

### EV-12. 차량 유형과 충전 인프라 설명에 사용한 출처는 무엇인가?

~~~sparql
PREFIX ev: <https://example.org/ontology/custom/electric-vehicle#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?source ?title ?publisher ?url ?accessed WHERE {
  ?source a ev:SourceDocument ; ev:sourceTitle ?title ; ev:sourcePublisher ?publisher ; ev:sourceURL ?url ; ev:sourceAccessedOn ?accessed .
  FILTER(lang(?title) = "ko")
} ORDER BY ?source
~~~

URI는 example.org 로컬 초안이다. 지역별 커넥터 표준, 법규, 요금과 차종별 수치 사양은 포함하지 않는다.
