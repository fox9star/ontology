# ROS 2 온톨로지 탐색 질문

아래 질의는 `question-fixture.ttl` 기준으로 실행합니다. 초기 예제는 가상 온실 구성입니다. ROS 2의 일반 개념과 예시로 만든 이름·연결을 구분합니다.

### ROS2-01. 시스템의 구성 요약은 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?system ?name ?recordKind ?purpose ?packageCount ?nodeCount ?topicCount ?serviceCount ?actionCount ?hardwareCount ?controllerCount ?frameCount ?qosCount ?sourceCount ?note WHERE {
  ?system a ros2:ROS2System ; rdfs:label ?name ; ros2:recordKind ?recordKind ; ros2:systemPurpose ?purpose ; ros2:systemNote ?note .
  FILTER (LANG(?name) = "ko")
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?packageCount) WHERE { ?system ros2:hasPackage ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?nodeCount) WHERE { ?system ros2:hasNode ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?topicCount) WHERE { ?system ros2:hasTopic ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?serviceCount) WHERE { ?system ros2:hasService ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?actionCount) WHERE { ?system ros2:hasAction ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?hardwareCount) WHERE { ?system ros2:hasHardwareComponent ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?controllerCount) WHERE { ?system ros2:hasController ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?frameCount) WHERE { ?system ros2:hasCoordinateFrame ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?qosCount) WHERE { ?system ros2:hasQoSProfile ?item } GROUP BY ?system }
  { SELECT ?system (COUNT(DISTINCT ?item) AS ?sourceCount) WHERE { ?system ros2:hasDocumentationSource ?item } GROUP BY ?system }
}
~~~

### ROS2-02. 노드의 역할과 패키지는 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?system ?node ?name ?role ?package ?packageName ?note WHERE {
  ?system ros2:hasNode ?node .
  ?node rdfs:label ?name ; ros2:nodeRole ?role ; ros2:usesPackage ?package ; ros2:nodeNote ?note .
  ?package ros2:packageName ?packageName .
  FILTER (LANG(?name) = "ko")
}
ORDER BY ?node
~~~

### ROS2-03. 토픽은 어떤 형식과 QoS를 쓰며 누가 발행·구독하는가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?system ?topic ?name ?type ?typeName ?packageName ?publisher ?subscriber ?qos WHERE {
  ?system ros2:hasTopic ?topic .
  ?topic ros2:topicName ?name ; ros2:messageType ?type ; ros2:hasPublisher ?publisher ; ros2:hasSubscriber ?subscriber ; ros2:usesQoSProfile ?qos .
  ?type ros2:typeName ?typeName ; ros2:definedInPackage ?package .
  ?package ros2:packageName ?packageName .
}
ORDER BY ?topic ?publisher ?subscriber
~~~

### ROS2-04. 서비스의 형식, 서버, 클라이언트와 QoS는 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?system ?service ?name ?type ?typeName ?server ?client ?qos ?note WHERE {
  ?system ros2:hasService ?service .
  ?service ros2:serviceName ?name ; ros2:serviceType ?type ; ros2:serviceServer ?server ; ros2:serviceClient ?client ; ros2:serviceQoSProfile ?qos ; ros2:serviceNote ?note .
  ?type ros2:typeName ?typeName .
}
~~~

### ROS2-05. 액션의 작업과 서버·클라이언트는 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?system ?action ?name ?type ?typeName ?server ?client ?note WHERE {
  ?system ros2:hasAction ?action .
  ?action ros2:actionName ?name ; ros2:actionType ?type ; ros2:actionServer ?server ; ros2:actionClient ?client ; ros2:actionNote ?note .
  ?type ros2:typeName ?typeName .
}
~~~

### ROS2-06. 패키지와 메시지·서비스·액션 형식은 어떻게 연결되는가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?package ?name ?role ?uri ?note ?type ?typeName ?definitionKind WHERE {
  ?package a ros2:Package ; ros2:packageName ?name ; ros2:packageRole ?role ; ros2:packageUri ?uri ; ros2:packageNote ?note .
  OPTIONAL {
    ?type ros2:definedInPackage ?package ; ros2:typeName ?typeName ; ros2:definitionKind ?definitionKind .
  }
}
ORDER BY ?package ?type
~~~

### ROS2-07. 하드웨어 상태·명령 인터페이스와 컨트롤러는 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?hardware ?name ?kind ?protocol ?stateInterface ?commandInterface ?controller ?controllerName ?controllerKind ?package ?node ?controllerNote ?hardwareNote WHERE {
  ?system ros2:hasHardwareComponent ?hardware .
  ?hardware ros2:componentName ?name ; ros2:componentKind ?kind ; ros2:hardwareProtocol ?protocol ; ros2:hardwareNote ?hardwareNote .
  OPTIONAL { ?hardware ros2:stateInterface ?stateInterface }
  OPTIONAL { ?hardware ros2:commandInterface ?commandInterface }
  OPTIONAL {
    ?hardware ros2:controlledBy ?controller .
    ?controller ros2:controllerName ?controllerName ; ros2:controllerKind ?controllerKind ; ros2:controllerPackage ?package ; ros2:controllerNode ?node ; ros2:controllerNote ?controllerNote .
  }
}
ORDER BY ?hardware
~~~

### ROS2-08. tf2 좌표 프레임의 부모 관계는 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?system ?frame ?name ?role ?parent ?parentName ?note WHERE {
  ?system ros2:hasCoordinateFrame ?frame .
  ?frame ros2:frameName ?name ; ros2:frameRole ?role ; ros2:frameNote ?note .
  OPTIONAL {
    ?frame ros2:parentFrame ?parent .
    ?parent ros2:frameName ?parentName .
  }
}
ORDER BY ?frame
~~~

### ROS2-09. 시스템에 정의된 QoS 정책 값은 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
SELECT ?system ?qos ?name ?reliability ?durability ?history ?depth ?note WHERE {
  ?system ros2:hasQoSProfile ?qos .
  ?qos ros2:qosName ?name ; ros2:reliability ?reliability ; ros2:durability ?durability ; ros2:historyPolicy ?history ; ros2:qosNote ?note .
  OPTIONAL { ?qos ros2:historyDepth ?depth }
}
ORDER BY ?qos
~~~

### ROS2-10. 개념과 예시의 근거로 연결된 문서는 무엇인가?

~~~sparql
PREFIX ros2: <https://example.org/ontology/custom/ros2#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?entity ?entityName ?source ?title ?publisher ?uri ?accessedAt ?claim ?language WHERE {
  ?entity ros2:documentedBy ?source .
  ?entity rdfs:label ?entityName .
  ?source ros2:sourceTitle ?title ; ros2:sourcePublisher ?publisher ; ros2:sourceUri ?uri ; ros2:sourceAccessedAt ?accessedAt ; ros2:sourceClaim ?claim ; ros2:sourceLanguage ?language .
  FILTER (LANG(?entityName) = "ko")
}
ORDER BY ?source ?entity
~~~
