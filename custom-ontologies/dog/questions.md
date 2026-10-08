# 개 업무 질문

화면에서는 `example.ttl`에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용하며 두 그래프의 개체 IRI는 저장 공간만 다르고 내용은 같다.
예제는 가상의 개 4마리와 보호자 3명, 병원 2곳이며 실제 동물이나 사람, 마이크로칩, 증명서가 아니다. `urn:synthetic:` 주소는 자리 표시용이다.
접종 상태 질문(DOG-03)은 기준일을 **2026-10-05**로 고정해 계산한다. 결과에 없는 접종은 아직 기록하지 않았다는 뜻이며 맞히지 않았다는 증명이 아니다.

### DOG-01. 어떤 개가 어떤 품종·성별·중성화 상태인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dog ?breed ?size ?sex ?neuter
WHERE {
  ?dog a dog:Dog ; dog:hasBreed ?breed ; dog:sex ?sex ; dog:neuterStatus ?neuter .
  ?breed a dog:Breed .
  OPTIONAL { ?breed dog:typicalSizeClass ?size }
}
ORDER BY ?dog
~~~

### DOG-02. 보호자별로 돌보는 개는 몇 마리인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?guardian (COUNT(DISTINCT ?dog) AS ?dogs)
WHERE {
  ?guardian a dog:Guardian .
  ?dog a dog:Dog ; dog:hasGuardian ?guardian .
}
GROUP BY ?guardian
ORDER BY DESC(?dogs) ?guardian
~~~

### DOG-03. 기준일 2026-10-05 현재 광견병 접종은 유효한가, 기한이 지났는가, 예정인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?dog ?status ?administered ?due ?certificate ?standing
WHERE {
  BIND ("2026-10-05"^^xsd:date AS ?asOf)
  ?dog a dog:Dog ; dog:hasVaccination ?v .
  ?v a dog:Vaccination ; dog:vaccineKind "rabies" ; dog:vaccinationStatus ?status ; dog:nextDueDate ?due .
  OPTIONAL { ?v dog:administeredDate ?administered }
  OPTIONAL { ?v dog:certificateUri ?certificate }
  BIND (IF(?status = "scheduled", "planned", IF(?due < ?asOf, "overdue", "current")) AS ?standing)
}
ORDER BY ?dog
~~~

### DOG-04. 광견병 접종 기록이 아직 하나도 없는 개는 어느 개인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dog
WHERE {
  ?dog a dog:Dog .
  FILTER NOT EXISTS { ?dog dog:hasVaccination ?v . ?v dog:vaccineKind "rabies" }
}
ORDER BY ?dog
~~~

### DOG-05. 아직 맞히지 않은 예정 접종은 무엇이며 언제로 잡혀 있는가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dog ?kind ?due
WHERE {
  ?dog a dog:Dog ; dog:hasVaccination ?v .
  ?v a dog:Vaccination ; dog:vaccinationStatus "scheduled" ; dog:vaccineKind ?kind ; dog:nextDueDate ?due .
}
ORDER BY ?due ?dog
~~~

### DOG-06. 병원별로 실시한 접종은 몇 건인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?clinic (COUNT(DISTINCT ?v) AS ?vaccinations)
WHERE {
  ?clinic a dog:Clinic .
  ?v a dog:Vaccination ; dog:vaccinationStatus "administered" ; dog:administeredAt ?clinic .
}
GROUP BY ?clinic
ORDER BY ?clinic
~~~

### DOG-07. 병원별·방문 사유별로 방문은 몇 번이고 가장 최근 방문일은 언제인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?clinic ?reason (COUNT(DISTINCT ?visit) AS ?visits) (MAX(?date) AS ?latest)
WHERE {
  ?dog a dog:Dog ; dog:hasVisit ?visit .
  ?visit a dog:VetVisit ; dog:visitedClinic ?clinic ; dog:visitReason ?reason ; dog:visitDate ?date .
}
GROUP BY ?clinic ?reason
ORDER BY ?clinic ?reason
~~~

### DOG-08. 개별 체중은 시간에 따라 어떻게 변했는가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dog ?date ?kg
WHERE {
  ?dog a dog:Dog ; dog:hasWeightRecord ?record .
  ?record a dog:WeightRecord ; dog:measuredDate ?date ; dog:weightKg ?kg .
}
ORDER BY ?dog ?date
~~~

### DOG-09. 동물등록 상태는 어떠하며 등록된 개의 식별번호와 증빙은 무엇인가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dog ?status ?number ?evidence
WHERE {
  ?dog a dog:Dog ; dog:microchipStatus ?status .
  OPTIONAL { ?dog dog:microchipNumber ?number }
  OPTIONAL { ?dog dog:registrationEvidenceUri ?evidence }
}
ORDER BY ?dog
~~~

### DOG-10. 생년월일이 확실하지 않은 개는 어느 개이며 어떤 값이 기록되어 있는가?

~~~sparql
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dog ?knowledge ?birth
WHERE {
  ?dog a dog:Dog ; dog:birthDateKnowledge ?knowledge .
  OPTIONAL { ?dog dog:birthDate ?birth }
  FILTER (?knowledge != "exact")
}
ORDER BY ?dog
~~~

예제의 고정 정답은 차례로 4·3·3·1·2·2·5·5·4·3행이다. DOG-04는 달이만 광견병 기록이 없다는 것을 보여 주며, DOG-03의 `overdue`는 콩이의 접종 유효기한이 기준일보다 앞서기 때문이다.
