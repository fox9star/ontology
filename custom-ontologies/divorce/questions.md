# 이혼 업무 질문

화면에서는 `example.ttl`에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용하며 두 그래프의 개체 IRI는 저장 공간만 다르고 내용은 같다.
예제는 **가상**의 사건 5건이며 실제 사람이나 법원 기록이 아니다. 당사자와 자녀는 가명 표시만 있고, 날짜·금액·`urn:synthetic:` 증빙 주소는 모두 만든 값이다.
이 온톨로지는 법률 자문이 아니며 법정 기간이나 요건을 계산하지 않는다. 숙려 종료일은 법원이 알려 준 값을 그대로 받아 날짜의 순서만 비교한다.
숙려 상태 질문(DIV-03)은 기준일을 **2026-10-05**로 고정해 계산한다. 결과에 없는 사건이나 결정은 아직 기록하지 않았다는 뜻이다.

### DIV-01. 사건마다 유형과 단계, 접수일, 효력 발생일, 종결 증빙, 철회일은 무엇인가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?type ?status ?filed ?effective ?evidence ?withdrawn
WHERE {
  ?case a div:DivorceCase ; div:caseType ?type ; div:caseStatus ?status .
  OPTIONAL { ?case div:filedDate ?filed }
  OPTIONAL { ?case div:effectiveDate ?effective }
  OPTIONAL { ?case div:decreeEvidenceUri ?evidence }
  OPTIONAL { ?case div:withdrawalDate ?withdrawn }
}
ORDER BY ?case
~~~

### DIV-02. 협의 사건의 접수·숙려 종료·의사 확인·효력 발생 날짜는 어떻게 이어지는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?filed ?reflectionEnd ?confirmation ?effective
WHERE {
  ?case a div:DivorceCase ; div:caseType "consensual" ; div:filedDate ?filed ; div:reflectionEndDate ?reflectionEnd .
  OPTIONAL { ?case div:confirmationDate ?confirmation }
  OPTIONAL { ?case div:effectiveDate ?effective }
}
ORDER BY ?case
~~~

### DIV-03. 기준일 2026-10-05 현재 숙려 기간이 끝났지만 아직 의사 확인을 받지 않은 협의 사건은 무엇인가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
SELECT ?case ?reflectionEnd
WHERE {
  BIND ("2026-10-05"^^xsd:date AS ?asOf)
  ?case a div:DivorceCase ; div:caseType "consensual" ; div:caseStatus "filed" ; div:reflectionEndDate ?reflectionEnd .
  FILTER (?reflectionEnd <= ?asOf)
  FILTER NOT EXISTS { ?case div:confirmationDate ?confirmation }
}
ORDER BY ?case
~~~

### DIV-04. 사건마다 당사자는 누구이며 어떤 역할인가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?party ?role
WHERE {
  ?case a div:DivorceCase ; div:hasParty ?party .
  ?party a div:Party ; div:partyRole ?role .
}
ORDER BY ?case ?party
~~~

### DIV-05. 사건마다 자녀는 누구이며 접수 시점에 미성년이었는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?child ?minor
WHERE {
  ?case a div:DivorceCase ; div:hasChild ?child .
  ?child a div:Child ; div:minorAtFiling ?minor .
}
ORDER BY ?case ?child
~~~

### DIV-06. 양육 결정이 아직 없는 미성년 자녀는 누구이며 사건은 어느 단계인가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?child ?status
WHERE {
  ?case a div:DivorceCase ; div:caseStatus ?status ; div:hasChild ?child .
  ?child div:minorAtFiling true .
  FILTER NOT EXISTS { ?case div:hasCustodyArrangement ?a . ?a div:custodyOfChild ?child }
}
ORDER BY ?case ?child
~~~

### DIV-07. 정해진 양육 결정은 어떤 자녀를 누가 어떤 친권 방식으로 맡는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?child ?custodian ?authority
WHERE {
  ?case a div:DivorceCase ; div:hasCustodyArrangement ?arrangement .
  ?arrangement a div:CustodyArrangement ; div:custodyOfChild ?child ; div:custodian ?custodian ; div:authorityHolding ?authority .
}
ORDER BY ?case ?child
~~~

### DIV-08. 양육비는 누가 누구에게 어떤 자녀를 위해 매달 얼마를 어느 날 지급하는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?case ?child ?payer ?payee ?amount ?currency ?day
WHERE {
  ?case a div:DivorceCase ; div:hasSupportObligation ?support .
  ?support a div:SupportObligation ; div:supportForChild ?child ; div:payer ?payer ; div:payee ?payee ;
           div:monthlyAmount ?amount ; div:currencyCode ?currency ; div:paymentDay ?day .
}
ORDER BY ?case ?child
~~~

### DIV-09. 재산·채무 항목은 어떤 종류와 가액이며 당사자별로 몇 퍼센트씩 나뉘는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?asset ?type ?value ?currency ?party ?share
WHERE {
  ?case a div:DivorceCase ; div:hasAsset ?asset .
  ?asset a div:Asset ; div:assetType ?type ; div:estimatedValue ?value ; div:valueCurrency ?currency ; div:hasAllocation ?allocation .
  ?allocation a div:AssetAllocation ; div:allocatedTo ?party ; div:sharePercent ?share .
}
ORDER BY ?asset ?party
~~~

### DIV-10. 종결된 사건에서 분할 비율의 합이 100이 아닌 항목이 있는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?asset (SUM(?share) AS ?total)
WHERE {
  ?case a div:DivorceCase ; div:caseStatus "finalized" ; div:hasAsset ?asset .
  OPTIONAL { ?asset div:hasAllocation ?allocation . ?allocation div:sharePercent ?share }
}
GROUP BY ?asset
HAVING (COALESCE(SUM(?share), 0) != 100)
ORDER BY ?asset
~~~

### DIV-11. 양육비를 받는 당사자가 그 자녀의 양육자와 다른 경우가 있는가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?support ?payee ?custodian
WHERE {
  ?case a div:DivorceCase ; div:hasSupportObligation ?support ; div:hasCustodyArrangement ?arrangement .
  ?support div:supportForChild ?child ; div:payee ?payee .
  ?arrangement div:custodyOfChild ?child ; div:custodian ?custodian .
  FILTER (?custodian != ?payee)
}
ORDER BY ?support
~~~

### DIV-12. 사건 유형과 단계별로 사건이 몇 건인가?

~~~sparql
PREFIX div: <https://example.org/ontology/custom/divorce#>
SELECT ?type ?status (COUNT(DISTINCT ?case) AS ?cases)
WHERE {
  ?case a div:DivorceCase ; div:caseType ?type ; div:caseStatus ?status .
}
GROUP BY ?type ?status
ORDER BY ?type ?status
~~~

예제의 고정 정답은 차례로 5·3·1·10·3·1·1·1·8·0·0·5행이다. DIV-10과 DIV-11은 0행이어야 하는 무결성 점검이다.
