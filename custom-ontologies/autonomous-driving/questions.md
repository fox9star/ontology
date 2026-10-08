# 자율주행 온톨로지 탐색 질문

모든 차량·운행·센서·시나리오·안전 기능 및 시험 기록은 합성 학습 예시입니다. SAE 수준은 표준 용어로만 등록하며, 가상 차량의 기능 수준은 평가하지 않았습니다. 질문은 별도 고정 IRI를 사용하는 `question-fixture.ttl`을 기준으로 합니다.

### AD-01. 시스템의 차량·기능·스택·시험 구성 요약은 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?system ?name ?recordKind ?purpose ?vehicleCount ?featureCount ?levelCount ?oddCount ?sensorCount ?moduleCount ?mapCount ?routeCount ?trajectoryCount ?scenarioCount ?safetyCount ?testCount ?sourceCount ?note WHERE {
  ?system a ad:AutonomousDrivingSystem ; rdfs:label ?name ; ad:systemRecordKind ?recordKind ; ad:systemPurpose ?purpose ; ad:systemNote ?note .
  FILTER (LANG(?name) = "ko")
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?vehicleCount) WHERE { ?system ad:hasVehicle ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?featureCount) WHERE { ?system ad:hasDrivingFeature ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?levelCount) WHERE { ?system ad:hasAutomationLevel ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?oddCount) WHERE { ?system ad:hasOperationalDesignDomain ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?sensorCount) WHERE { ?system ad:hasSensor ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?moduleCount) WHERE { ?system ad:hasSoftwareModule ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?mapCount) WHERE { ?system ad:hasRoadMap ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?routeCount) WHERE { ?system ad:hasRoute ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?trajectoryCount) WHERE { ?system ad:hasTrajectory ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?scenarioCount) WHERE { ?system ad:hasScenario ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?safetyCount) WHERE { ?system ad:hasSafetyFunction ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?testCount) WHERE { ?system ad:hasTestRun ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?sourceCount) WHERE { ?system ad:hasDocumentationSource ?item } GROUP BY ?system }
}
~~~

### AD-02. 주행 기능의 ODD와 명시적으로 평가된 자동화 수준은 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?feature ?featureName ?level ?levelLabel ?odd ?oddName ?note WHERE {
  ?system ad:hasDrivingFeature ?feature .
  ?feature ad:featureName ?featureName ; ad:featureODD ?odd ; ad:featureNote ?note .
  ?odd ad:oddName ?oddName .
  OPTIONAL { ?feature ad:featureAutomationLevel ?level . ?level ad:levelLabel ?levelLabel }
}
~~~

### AD-03. SAE J3016 수준 용어는 어떤 번호·명칭·범위로 기록되어 있는가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?level ?number ?label ?scope ?note WHERE {
  ?system ad:hasAutomationLevel ?level .
  ?level ad:levelNumber ?number ; ad:levelLabel ?label ; ad:levelScope ?scope ; ad:levelNote ?note .
}
ORDER BY ?number
~~~

### AD-04. 차량의 센서 방식과 목적은 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?sensor ?name ?modality ?vehicle ?vehicleName ?purpose WHERE {
  ?system ad:hasSensor ?sensor .
  ?sensor ad:sensorName ?name ; ad:sensorModality ?modality ; ad:mountedOnVehicle ?vehicle ; ad:sensorPurpose ?purpose .
  ?vehicle ad:vehicleName ?vehicleName .
}
ORDER BY ?sensor
~~~

### AD-05. 자율주행 소프트웨어 모듈의 입출력과 의존 흐름은 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?module ?moduleName ?kind ?inputs ?outputs ?dependency ?dependencyName ?note WHERE {
  ?system ad:hasSoftwareModule ?module .
  ?module ad:moduleName ?moduleName ; ad:moduleKind ?kind ; ad:moduleInput ?inputs ; ad:moduleOutput ?outputs ; ad:moduleNote ?note .
  OPTIONAL { ?module ad:dependsOnModule ?dependency . ?dependency ad:moduleName ?dependencyName }
}
ORDER BY ?module ?dependency
~~~

### AD-06. ODD의 도로·지역·속도와 환경 조건은 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?odd ?name ?roadwayType ?area ?maxSpeed ?condition ?note WHERE {
  ?system ad:hasOperationalDesignDomain ?odd .
  ?odd ad:oddName ?name ; ad:roadwayType ?roadwayType ; ad:geographicArea ?area ; ad:maxSpeedKph ?maxSpeed ; ad:environmentCondition ?condition ; ad:oddNote ?note .
}
ORDER BY ?odd ?condition
~~~

### AD-07. 지도·경로·계획 궤적·생성 모듈은 어떻게 연결되는가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?map ?mapName ?format ?coverage ?route ?routeName ?start ?end ?trajectory ?trajectoryName ?status ?planner ?plannerName WHERE {
  ?system ad:hasRoadMap ?map ; ad:hasRoute ?route ; ad:hasTrajectory ?trajectory .
  ?map ad:mapName ?mapName ; ad:mapFormat ?format ; ad:mapCoverage ?coverage .
  ?route ad:routeName ?routeName ; ad:routeStart ?start ; ad:routeEnd ?end ; ad:routeMap ?map .
  ?trajectory ad:trajectoryName ?trajectoryName ; ad:trajectoryStatus ?status ; ad:trajectoryForRoute ?route ; ad:trajectoryGeneratedBy ?planner .
  ?planner ad:moduleName ?plannerName .
}
~~~

### AD-08. 주행 시나리오별 운행 조건과 도로 행위자는 누구인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?scenario ?scenarioName ?kind ?odd ?actor ?actorName ?actorKind ?motion ?note WHERE {
  ?system ad:hasScenario ?scenario .
  ?scenario ad:scenarioName ?scenarioName ; ad:scenarioKind ?kind ; ad:scenarioODD ?odd ; ad:hasRoadActor ?actor ; ad:scenarioNote ?note .
  ?actor ad:actorName ?actorName ; ad:actorKind ?actorKind ; ad:actorMotion ?motion .
}
ORDER BY ?scenario ?actor
~~~

### AD-09. 안전 기능은 무엇을 감시하고 어떤 대응 개념을 기록하는가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?function ?name ?kind ?odd ?response ?status ?note WHERE {
  ?system ad:hasSafetyFunction ?function .
  ?function ad:safetyFunctionName ?name ; ad:safetyFunctionKind ?kind ; ad:monitorsODD ?odd ; ad:responseAction ?response ; ad:safetyFunctionStatus ?status ; ad:safetyFunctionNote ?note .
}
ORDER BY ?function
~~~

### AD-10. 계획된 시험의 환경·시나리오·실행 상태와 증거는 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
SELECT ?system ?test ?name ?environment ?status ?scenario ?scenarioName ?result ?date ?evidence ?note WHERE {
  ?system ad:hasTestRun ?test .
  ?test ad:testName ?name ; ad:testEnvironment ?environment ; ad:testStatus ?status ; ad:testsScenario ?scenario ; ad:testResult ?result ; ad:testNote ?note .
  ?scenario ad:scenarioName ?scenarioName .
  OPTIONAL { ?test ad:testDate ?date }
  OPTIONAL { ?test ad:testEvidenceUri ?evidence }
}
~~~

### AD-11. 각 개념 주장에 연결된 공식 문서의 확인 범위는 무엇인가?

~~~sparql
PREFIX ad: <https://example.org/ontology/custom/autonomous-driving#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?entityName ?source ?title ?publisher ?uri ?accessedAt ?claim ?language WHERE {
  ?entity ad:documentedBy ?source ; rdfs:label ?entityName .
  ?source ad:sourceTitle ?title ; ad:sourcePublisher ?publisher ; ad:sourceUri ?uri ; ad:sourceAccessedAt ?accessedAt ; ad:sourceClaim ?claim ; ad:sourceLanguage ?language .
  FILTER (LANG(?entityName) = "ko")
}
ORDER BY ?source ?entity
~~~
