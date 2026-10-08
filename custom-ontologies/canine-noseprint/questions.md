# 개의 비문 온톨로지 탐색 질문

연구 결과는 원문 논문의 표본과 프로토콜 범위로만 기록한다. 예제에는 이미지가 없고 식별·성능 측정을 실행하지 않았다.

### DNP-01. 합성 프로젝트의 범위와 대상 개체는 무엇인가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?project ?status ?subject ?pseudonym ?scope WHERE { ?project a np:NosePrintProject; np:projectStatus ?status; np:projectScopeNote ?scope; np:projectHasSubject ?subject. ?subject np:subjectPseudonym ?pseudonym. }
~~~

### DNP-02. 가명 비문 개체와 개 온톨로지 레코드는 어떻게 연결되는가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?subject ?pseudonym ?record WHERE { ?subject a np:CanineSubject; np:subjectPseudonym ?pseudonym; np:subjectDogRecordUri ?record. }
~~~

### DNP-03. 표본의 자산 상태와 촬영 조건은 무엇인가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?sample ?assetStatus ?asset ?session ?device ?lighting ?pose ?surface WHERE { ?sample a np:NosePrintSample; np:sampleAssetStatus ?assetStatus; np:sampleAssetUri ?asset; np:sampleCapturedIn ?session. ?session np:captureDeviceType ?device; np:captureLighting ?lighting; np:capturePose ?pose; np:captureSurfaceCondition ?surface. } ORDER BY ?sample
~~~

### DNP-04. 분석 관심 영역은 어떻게 정의되고 어떤 자료를 근거로 하는가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?region ?name ?definition ?source ?title WHERE { ?region a np:NoseRegion; np:regionName ?name; np:regionDefinition ?definition; np:regionDocumentedBy ?source. ?source np:sourceTitle ?title. }
~~~

### DNP-05. 표본의 초점·각도·조명·반사·가림 품질 상태는?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?sample ?assessment ?status ?focus ?pose ?lighting ?glare ?occlusion ?issue WHERE { ?sample np:sampleQualityAssessment ?assessment. ?assessment np:qualityStatus ?status; np:focusStatus ?focus; np:poseStatus ?pose; np:lightingStatus ?lighting; np:glareStatus ?glare; np:occlusionStatus ?occlusion; np:qualityIssue ?issue. } ORDER BY ?sample
~~~

### DNP-06. 전처리 및 비문 템플릿은 실행되었는가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?sample ?prep ?prepStatus ?steps ?template ?templateStatus ?method WHERE { ?prep np:preprocessingOfSample ?sample; np:preprocessingStatus ?prepStatus; np:preprocessingSteps ?steps. ?template np:templateFromSample ?sample; np:templateStatus ?templateStatus; np:templateMethod ?method. }
~~~

### DNP-07. 참조 모델의 구조·상태와 연구 근거는 무엇인가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?model ?name ?family ?status ?description ?source ?title ?claim ?limits WHERE { ?model a np:RecognitionModel; np:modelName ?name; np:modelFamily ?family; np:modelStatus ?status; np:modelDescription ?description; np:modelDocumentedBy ?source. ?source np:sourceTitle ?title; np:sourceClaimScope ?claim; np:sourceLimitations ?limits. }
~~~

### DNP-08. 이 예시 데이터셋의 표본 수와 실제 데이터 보유 여부는?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?dataset ?name ?provenance ?status ?subjects ?samples ?split ?limits WHERE { ?dataset a np:ReferenceDataset; np:datasetName ?name; np:datasetProvenance ?provenance; np:datasetStatus ?status; np:datasetSubjectCount ?subjects; np:datasetSampleCount ?samples; np:datasetSplitProtocol ?split; np:datasetLimitations ?limits. }
~~~

### DNP-09. 비교 작업과 결과의 현재 상태는?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?task ?mode ?status ?query ?gallery ?result ?resultStatus ?note WHERE { ?task a np:IdentificationTask; np:taskMode ?mode; np:taskStatus ?status; np:taskQuerySample ?query; np:taskGalleryDataset ?gallery; np:taskHasResult ?result. ?result np:matchStatus ?resultStatus; np:matchNote ?note. }
~~~

### DNP-10. 평가 계획의 지표는 측정되었으며 값이 있는가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?run ?status ?dataset ?model ?metric ?name ?kind ?measurement ?value WHERE { ?run a np:EvaluationRun; np:evaluationStatus ?status; np:evaluationUsesDataset ?dataset; np:evaluationUsesModel ?model; np:evaluationUsesMetric ?metric. ?metric np:metricName ?name; np:metricKind ?kind; np:metricMeasurementStatus ?measurement. OPTIONAL { ?metric np:metricValue ?value } } ORDER BY ?metric
~~~

### DNP-11. 합성 픽스처의 이용 권한 상태와 실제 표본의 보존 원칙은?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?permission ?status ?scope ?retention ?subject ?sample WHERE { ?permission a np:DataUsePermission; np:permissionStatus ?status; np:permissionScope ?scope; np:retentionRule ?retention; np:permissionCoversSubject ?subject; np:permissionCoversSample ?sample. } ORDER BY ?sample
~~~

### DNP-12. 연구별 비문 고유성·안정성·성능 주장과 한계는 무엇인가?

~~~sparql
PREFIX np: <https://example.org/ontology/custom/canine-noseprint#>
PREFIX dog: <https://example.org/ontology/custom/dog#>
SELECT ?source ?title ?year ?uri ?claim ?limits WHERE { ?project np:projectHasSource ?source. ?source np:sourceTitle ?title; np:sourceYear ?year; np:sourceUri ?uri; np:sourceClaimScope ?claim; np:sourceLimitations ?limits. } ORDER BY ?year ?title
~~~
