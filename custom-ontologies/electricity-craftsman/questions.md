# 전기기능사 온톨로지 역량 질문

공식 자격·시험 정보와 근거 출처, 적용 기간이 있는 출제기준 버전을 탐색한다. 2027-2029 세부 출제기준은 공지만 확인했으며 원문을 검토하기 전까지 내용 항목을 주장하지 않는다.

### ELEC-01. 자격의 공식 명칭, 코드, 관련 부처와 시행기관은 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?ko ?en ?code ?ministry ?body WHERE { ?q a ec:ElectricalQualification; ec:qualificationPreferredLabel ?ko, ?en; ec:qualificationQnetCode ?code; ec:qualificationRelatedMinistry ?ministry; ec:qualificationAdministeringBody ?body. FILTER(lang(?ko)='ko' && lang(?en)='en') }
~~~

### ELEC-02. 현행·차기 출제기준의 적용 기간과 상세 기준 반영 상태는 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?from ?through ?status ?content WHERE { ?s a ec:ExamStandardVersion; ec:standardIdentifier ?id; ec:standardPreferredLabel ?label; ec:standardValidFrom ?from; ec:standardValidThrough ?through; ec:standardStatus ?status; ec:standardContentStatus ?content. FILTER(lang(?label)='ko') } ORDER BY ?from
~~~

### ELEC-03. 필기와 실기의 검정 방법, 문항 수와 실기 시간은 어떻게 안내되는가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?method ?items ?choices ?minutes WHERE { ?s a ec:ExamStage; ec:stageIdentifier ?id; ec:stagePreferredLabel ?label; ec:stageMethod ?method. OPTIONAL { ?s ec:stageQuestionCount ?items } OPTIONAL { ?s ec:stageChoiceCount ?choices } OPTIONAL { ?s ec:stageDurationMinutes ?minutes } FILTER(lang(?label)='ko' && lang(?method)='ko') } ORDER BY ?id
~~~

### ELEC-04. 필기시험의 공식 과목명은 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?description WHERE { ?a a ec:KnowledgeArea; ec:knowledgeAreaIdentifier ?id; ec:knowledgeAreaPreferredLabel ?label; ec:knowledgeAreaDescription ?description. FILTER(lang(?label)='ko' && lang(?description)='ko') } ORDER BY ?id
~~~

### ELEC-05. 필기와 실기의 합격 점수 기준은 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?minimum ?maximum ?stageId WHERE { ?r a ec:AssessmentRule; ec:ruleIdentifier ?id; ec:rulePreferredLabel ?label; ec:ruleMinimumScore ?minimum; ec:ruleMaximumScore ?maximum; ec:ruleAppliesToStage ?s. ?s ec:stageIdentifier ?stageId. FILTER(lang(?label)='ko') } ORDER BY ?stageId
~~~

### ELEC-06. 큐넷에 명시된 실기 작업 범위와 연결 역량은 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?taskId ?taskLabel ?description ?competencyId ?competencyLabel WHERE { ?t a ec:PracticalTask; ec:practicalTaskIdentifier ?taskId; ec:practicalTaskPreferredLabel ?taskLabel; ec:practicalTaskDescription ?description; ec:taskHasCompetency ?c. ?c ec:competencyIdentifier ?competencyId; ec:competencyPreferredLabel ?competencyLabel. FILTER(lang(?taskLabel)='ko' && lang(?description)='ko' && lang(?competencyLabel)='ko') } ORDER BY ?taskId
~~~

### ELEC-07. 실기 지참 품목 22개의 명칭·규격·수량·제한은 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?spec ?quantity ?unit ?restriction WHERE { ?m a ec:MaterialRequirement; ec:materialIdentifier ?id; ec:materialPreferredLabel ?label; ec:materialSpecification ?spec; ec:materialQuantity ?quantity; ec:materialUnit ?unit. OPTIONAL { ?m ec:materialRestriction ?restriction } FILTER(lang(?label)='ko' && lang(?spec)='ko') } ORDER BY ?id
~~~

### ELEC-08. 큐넷의 실기 안전·보호구 관련 안내는 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?type ?text ?level WHERE { ?s a ec:SafetyRequirement; ec:safetyIdentifier ?id; ec:safetyPreferredLabel ?label; ec:safetyRequirementType ?type; ec:safetyText ?text. OPTIONAL { ?s ec:safetyLevel ?level } FILTER(lang(?label)='ko' && lang(?text)='ko') } ORDER BY ?id
~~~

### ELEC-09. 공식 출처 문서와 확인 시점, 확인 범위, 한계는 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?title ?uri ?kind ?accessed ?limits WHERE { ?s a ec:SourceDocument; ec:sourceIdentifier ?id; ec:sourceTitle ?title; ec:sourceUri ?uri; ec:sourceKind ?kind; ec:sourceAccessedAt ?accessed; ec:sourceLimitations ?limits. FILTER(lang(?limits)='ko') } ORDER BY ?id
~~~

### ELEC-10. 핵심 시험 정보 주장을 어떤 근거 기록이 뒷받침하는가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?status ?claim ?sourceId ?locator WHERE { ?e a ec:EvidenceRecord; ec:evidenceIdentifier ?id; ec:evidenceStatus ?status; ec:evidenceClaim ?claim; ec:evidenceSource ?s; ec:evidenceSourceLocator ?locator. ?s ec:sourceIdentifier ?sourceId. FILTER(lang(?claim)='ko') } ORDER BY ?id
~~~

### ELEC-11. 출제기준의 세부 내용 중 아직 추출하지 않은 버전은 무엇인가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?from ?through ?status ?content WHERE { ?s a ec:ExamStandardVersion; ec:standardIdentifier ?id; ec:standardPreferredLabel ?label; ec:standardValidFrom ?from; ec:standardValidThrough ?through; ec:standardStatus ?status; ec:standardContentStatus ?content. FILTER(?content='not_ingested' && lang(?label)='ko') }
~~~

### ELEC-12. 현재 데이터에서 필기 과목의 세부 출제 항목은 어느 상태로 관리되는가?

~~~sparql
PREFIX ec: <https://example.org/ontology/custom/electricity-craftsman#>
SELECT ?id ?label ?description ?source WHERE { ?a a ec:KnowledgeArea; ec:knowledgeAreaIdentifier ?id; ec:knowledgeAreaPreferredLabel ?label; ec:knowledgeAreaDescription ?description; ec:knowledgeAreaSource ?s. ?s ec:sourceTitle ?source. FILTER(lang(?label)='ko' && lang(?description)='ko') } ORDER BY ?id
~~~
