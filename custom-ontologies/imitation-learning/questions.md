# 모방학습 온톨로지 탐색 질문

방법 설명은 문헌 근거에 연결했다. 프로젝트, 로봇팔 과제, 시연 단계와 실행 상태는 합성 예시이며 실제 학습·평가를 뜻하지 않는다.

### IL-01. 과제 목표와 프로젝트 데이터 범위는?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?project ?scope ?task ?taskName ?goal ?note WHERE { ?project a iml:ImitationLearningProject; iml:projectDataStatus ?scope; iml:projectNote ?note; iml:projectHasTask ?task. ?task iml:taskName ?taskName; iml:taskGoal ?goal. } ORDER BY ?task
~~~

### IL-02. 시연 데이터의 출처, 수집·분할 상태와 한계는?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?dataset ?name ?provenance ?collection ?split ?limits WHERE { ?project iml:projectHasDataset ?dataset. ?dataset iml:datasetName ?name; iml:datasetProvenanceType ?provenance; iml:datasetCollectionStatus ?collection; iml:datasetSplitStatus ?split; iml:datasetLimitations ?limits. }
~~~

### IL-03. 시연 단계별 관측과 행동 레이블은?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?demo ?step ?index ?obs ?modality ?summary ?action ?type ?value ?labelSource WHERE { ?demo iml:demonstrationHasStep ?step. ?step iml:stepIndex ?index; iml:stepObservation ?obs; iml:stepAction ?action. ?obs iml:observationModality ?modality; iml:observationSummary ?summary. ?action iml:actionType ?type; iml:actionValue ?value; iml:actionLabelSource ?labelSource. } ORDER BY ?index
~~~

### IL-04. 행동복제, DAgger, 역강화학습의 차이와 문헌 근거는?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?method ?name ?kind ?description ?source ?title ?uri ?claim WHERE { ?project iml:projectConsidersMethod ?method. ?method iml:methodName ?name; iml:methodKind ?kind; iml:methodDescription ?description; iml:methodDocumentedBy ?source. ?source iml:sourceTitle ?title; iml:sourceUri ?uri; iml:sourceClaim ?claim. } ORDER BY ?kind
~~~

### IL-05. 학습 실행 상태와 구성은?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?run ?name ?status ?dataset ?method ?policy ?note WHERE { ?project iml:projectHasTrainingRun ?run. ?run iml:trainingName ?name; iml:trainingStatus ?status; iml:trainingUsesDataset ?dataset; iml:trainingUsesMethod ?method; iml:trainingProducesPolicy ?policy; iml:trainingNote ?note. }
~~~

### IL-06. 정책의 대상 과제, 사용 방법 및 학습 상태는?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?policy ?name ?status ?task ?method ?note WHERE { ?project iml:projectHasPolicy ?policy. ?policy iml:policyName ?name; iml:policyStatus ?status; iml:policyForTask ?task; iml:policyLearnsWithMethod ?method; iml:policyNote ?note. }
~~~

### IL-07. 평가 지표의 측정 상태와 값은?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?run ?status ?evidence ?metric ?name ?measurement ?value ?unit WHERE { ?project iml:projectHasEvaluationRun ?run. ?run iml:evaluationStatus ?status; iml:evaluationEvidenceStatus ?evidence; iml:evaluationUsesMetric ?metric. ?metric iml:metricName ?name; iml:metricMeasurementStatus ?measurement; iml:metricUnit ?unit. OPTIONAL { ?metric iml:metricMeasuredValue ?value } } ORDER BY ?metric
~~~

### IL-08. 분포 변화는 어떻게 기록되며 어떤 방법과 연결되는가?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?shift ?name ?status ?method ?methodName ?description ?note WHERE { ?project iml:projectHasDistributionShift ?shift. ?shift iml:shiftName ?name; iml:shiftAssessmentStatus ?status; iml:shiftDescription ?description; iml:shiftNote ?note; iml:shiftDiscussedByMethod ?method. ?method iml:methodName ?methodName. }
~~~

### IL-09. 안전 범위와 검증 상태는?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?constraint ?name ?description ?status ?task ?taskName ?note WHERE { ?project iml:projectHasSafetyConstraint ?constraint. ?constraint iml:constraintName ?name; iml:constraintDescription ?description; iml:constraintStatus ?status; iml:constraintAppliesToTask ?task; iml:constraintNote ?note. ?task iml:taskName ?taskName. }
~~~

### IL-10. 등록 문헌과 주장 범위는?

~~~sparql
PREFIX iml: <https://example.org/ontology/custom/imitation-learning#>
SELECT ?source ?title ?authors ?year ?uri ?claim ?accessed WHERE { ?project iml:projectHasDocumentationSource ?source. ?source iml:sourceTitle ?title; iml:sourceAuthors ?authors; iml:sourceYear ?year; iml:sourceUri ?uri; iml:sourceClaim ?claim; iml:sourceAccessedAt ?accessed. } ORDER BY ?year
~~~
