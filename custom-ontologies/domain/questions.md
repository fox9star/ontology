# 지식·업무 영역 온톨로지 역량 질문

이 질문은 SKOS와 호환되는 영역 계층, 범위, 프로필 배정, 매핑 근거, 검토 및 변경 이력을 탐색한다. 예시 분류는 초안이며 권위 있는 분야 체계로 간주하지 않는다.

### DOM-01. 분류 체계의 버전·상태와 최상위 영역은 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?catalogLabel ?version ?status ?topId ?topLabel WHERE { ?catalog a dom:DomainCatalog; dom:catalogPreferredLabel ?catalogLabel; dom:catalogVersion ?version; dom:catalogLifecycleStatus ?status; dom:catalogHasTopDomain ?top. ?top dom:domainIdentifier ?topId; dom:domainPreferredLabel ?topLabel. FILTER(lang(?catalogLabel) = 'ko' && lang(?topLabel) = 'ko') } ORDER BY ?topId
~~~

### DOM-02. 영역 식별자·선호 표기·분류 기호·생애주기 상태는 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?id ?label ?notation ?status WHERE { ?domain a dom:KnowledgeDomain; dom:domainIdentifier ?id; dom:domainPreferredLabel ?label; dom:domainNotation ?notation; dom:domainLifecycleStatus ?status. FILTER(lang(?label) = 'ko') } ORDER BY ?id
~~~

### DOM-03. 직접 상위 영역과 하위 영역의 계층 관계는 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?childId ?childLabel ?parentId ?parentLabel WHERE { ?child dom:domainBroader ?parent; dom:domainIdentifier ?childId; dom:domainPreferredLabel ?childLabel. ?parent dom:domainIdentifier ?parentId; dom:domainPreferredLabel ?parentLabel. FILTER(lang(?childLabel) = 'ko' && lang(?parentLabel) = 'ko') } ORDER BY ?childId ?parentId
~~~

### DOM-04. 검색에 쓸 대체 표기와 언어 태그는 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?id ?label ?alias ?language WHERE { ?domain dom:domainIdentifier ?id; dom:domainPreferredLabel ?label; dom:domainAlternativeLabel ?alias. FILTER(lang(?label) = 'ko') BIND(lang(?alias) AS ?language) } ORDER BY ?id ?language
~~~

### DOM-05. 영역 정의 문장은 무엇을 포함하거나 제외하며 검토 상태는 어떤가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?domainId ?label ?kind ?text ?status WHERE { ?scope a dom:DomainScopeStatement; dom:scopeForDomain ?domain; dom:scopeKind ?kind; dom:scopeText ?text; dom:scopeReviewStatus ?status. ?domain dom:domainIdentifier ?domainId; dom:domainPreferredLabel ?label. FILTER(lang(?label) = 'ko' && lang(?text) = 'en') } ORDER BY ?domainId ?kind
~~~

### DOM-06. 로컬 온톨로지 프로필은 어떤 영역에 제안 배정되어 있고 근거·신뢰도는 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?profileId ?domainId ?status ?method ?confidence ?rationale WHERE { ?assignment a dom:DomainAssignment; dom:assignmentForProfile ?profile; dom:assignmentToDomain ?domain; dom:assignmentStatus ?status; dom:assignmentMethod ?method; dom:assignmentConfidence ?confidence; dom:assignmentRationale ?rationale. ?profile dom:ontologyProfileId ?profileId. ?domain dom:domainIdentifier ?domainId. FILTER(lang(?rationale) = 'ko') } ORDER BY ?profileId
~~~

### DOM-07. 계층이 아닌 교차 영역 관계의 유형·상태·설명은 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?relation ?subjectId ?objectId ?type ?status ?rationale WHERE { ?relation a dom:DomainRelation; dom:relationSubjectDomain ?subject; dom:relationObjectDomain ?object; dom:relationType ?type; dom:relationStatus ?status; dom:relationRationale ?rationale. ?subject dom:domainIdentifier ?subjectId. ?object dom:domainIdentifier ?objectId. FILTER(lang(?rationale) = 'en') } ORDER BY ?relation
~~~

### DOM-08. 외부 분류 매핑은 착수·제안·검토 중 어디에 있으며 외부 개념 URI가 있는가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?mapping ?domainId ?status ?relationType ?schemeName ?schemeUri ?conceptUri ?rationale WHERE { ?mapping a dom:DomainMapping; dom:mappingLocalDomain ?domain; dom:mappingStatus ?status; dom:mappingRelationType ?relationType; dom:mappingRationale ?rationale. ?domain dom:domainIdentifier ?domainId. OPTIONAL { ?mapping dom:mappingExternalScheme ?scheme. ?scheme dom:schemeName ?schemeName; dom:schemeUri ?schemeUri. } OPTIONAL { ?mapping dom:mappingExternalConceptUri ?conceptUri } FILTER(lang(?rationale) = 'en') } ORDER BY ?mapping
~~~

### DOM-09. 분류 구조와 프로필 범위 기록에 사용한 자료·발행자·한계는 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?source ?title ?publisher ?year ?uri ?kind ?scope ?limitations WHERE { ?source a dom:DomainSource; dom:sourceTitle ?title; dom:sourcePublisher ?publisher; dom:sourceYear ?year; dom:sourceUri ?uri; dom:sourceKind ?kind; dom:sourceScope ?scope; dom:sourceLimitations ?limitations. FILTER(lang(?scope) = 'en' && lang(?limitations) = 'en') } ORDER BY ?source
~~~

### DOM-10. 영역 검토의 진행 상태·결과·기준·검토자 역할은 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?domainId ?status ?outcome ?criteria ?reviewer ?rationale WHERE { ?review a dom:DomainReview; dom:reviewForDomain ?domain; dom:reviewStatus ?status; dom:reviewOutcome ?outcome; dom:reviewCriteria ?criteria; dom:reviewerRole ?reviewer; dom:reviewRationale ?rationale. ?domain dom:domainIdentifier ?domainId. FILTER(lang(?criteria) = 'en' && lang(?rationale) = 'en') }
~~~

### DOM-11. 영역의 생성·변경 이력과 이전·이후 상태, 사유는 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?domainId ?action ?date ?previous ?newStatus ?reason ?role WHERE { ?event a dom:DomainChangeEvent; dom:changeForDomain ?domain; dom:changeAction ?action; dom:changeDate ?date; dom:changePreviousStatus ?previous; dom:changeNewStatus ?newStatus; dom:changeReason ?reason; dom:changeRecordedByRole ?role. ?domain dom:domainIdentifier ?domainId. FILTER(lang(?reason) = 'en') }
~~~

### DOM-12. 이 초안의 프로필 배정 기록에 아직 연결되지 않은 영역은 무엇인가?

~~~sparql
PREFIX dom: <https://example.org/ontology/custom/domain#>
SELECT ?id ?label WHERE { ?domain a dom:KnowledgeDomain; dom:domainIdentifier ?id; dom:domainPreferredLabel ?label. FILTER(lang(?label) = 'ko') FILTER NOT EXISTS { ?assignment a dom:DomainAssignment; dom:assignmentToDomain ?domain } } ORDER BY ?id
~~~
