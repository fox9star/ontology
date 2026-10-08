# 온톨로지 품질 현황

이 보고서는 읽기 전용 점검 결과입니다. 인스턴스 정보는 집계 수치만 포함합니다.

| 지표 | 수치 |
|---|---:|
| terms | 231 |
| classes | 71 |
| properties | 160 |
| questions | 45 |
| terms_with_shapes | 222 |
| terms_referenced_by_questions | 131 |
| terms_used_by_bundled_instances | 175 |
| cq_backlog_terms | 100 |
| structural_exceptions | 10 |
| profile_count | 9 |
| project_count | 1 |

## 정본 모듈 버전

| 파일 | 버전 | Ontology IRI |
|---|---|---|
| core-schema.ttl | 1.1.1 | https://example.org/ontology/core |
| mv-schema.ttl | 1.2.1 | https://example.org/mv |
| agent-schema.ttl | 1.2.1 | https://example.org/agent |
| devops-schema.ttl | 1.2.1 | http://example.org/ontology/devops |
| ecommerce-schema.ttl | 1.2.1 | http://example.org/ontology/ecommerce |
| healthcare-schema.ttl | 1.3.1 | http://example.org/ontology/healthcare |
| academic-schema.ttl | 1.2.1 | https://example.org/ontology/academic |
| controlled-vocabularies.ttl | 1.0.0 | https://example.org/ontology/vocab |
| evidence-schema.ttl | 1.0.0 | https://example.org/ontology/evidence |
| custom-ontologies/ai-film/schema.ttl | 0.1.0 | https://example.org/ontology/custom/ai-film |

## 품질 게이트

통과

## 인스턴스 집계

| 프로파일 | 개체 | SHACL | 미선언 속성/유형 | 출처 관계 없는 자산 | 해결되지 않은 로컬 참조 |
|---|---:|---|---:|---:|---:|
| academic | 2 | True | 0 | 0 | 0 |
| agent | 23 | True | 0 | 0 | 0 |
| ai-film | 14 | True | 0 | 11 | 0 |
| devops | 10 | True | 0 | 2 | 0 |
| e2e | 19 | True | 0 | 2 | 0 |
| ecommerce | 4 | True | 0 | 0 | 0 |
| evidence | 10 | True | 0 | 0 | 0 |
| healthcare | 4 | True | 0 | 1 | 0 |
| mv | 16 | True | 0 | 0 | 0 |

## 용어 연결표

SHACL은 상위 클래스 target에서 상속된 제약을 포함합니다. CQ 없음은 미완료 항목입니다.

| 용어 | 종류 | SHACL 수 | CQ | 예제 사용 수 | 남은 공백 |
|---|---|---:|---|---:|---|
| http://example.org/ontology/devops#BuildArtifact | class | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#BuildTask | class | 3 | BUS-01, BUS-02 | 1 | 없음 |
| http://example.org/ontology/devops#DeploymentTask | class | 3 | BUS-01, BUS-02 | 1 | 없음 |
| http://example.org/ontology/devops#DevOpsAgent | class | 1 | 미포함 | 3 | cq |
| http://example.org/ontology/devops#DevOpsPipeline | class | 2 | BUS-01, BUS-02, DEV-01 | 1 | 없음 |
| http://example.org/ontology/devops#PipelineTask | class | 2 | 미포함 | 0 | cq |
| http://example.org/ontology/devops#SecurityScanTask | class | 3 | BUS-01, DEV-02 | 1 | 없음 |
| http://example.org/ontology/devops#TargetEnvironment | class | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#VulnerabilityReport | class | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#branchName | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#commitHash | property | 1 | BUS-01 | 1 | 없음 |
| http://example.org/ontology/devops#dependsOn | property | 1 | 미포함 | 2 | cq |
| http://example.org/ontology/devops#deployedTo | property | 1 | BUS-01 | 1 | 없음 |
| http://example.org/ontology/devops#deploysArtifact | property | 1 | BUS-01, BUS-02 | 1 | 없음 |
| http://example.org/ontology/devops#environmentName | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#executionStatus | property | 2 | BUS-01, BUS-02, DEV-01 | 4 | 없음 |
| http://example.org/ontology/devops#generatesReport | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#hasTask | property | 1 | BUS-01, BUS-02, DEV-01 | 3 | 없음 |
| http://example.org/ontology/devops#imageTag | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/devops#managedBy | property | 1 | 미포함 | 3 | cq |
| http://example.org/ontology/devops#pipelineId | property | 1 | DEV-01 | 1 | 없음 |
| http://example.org/ontology/devops#producesArtifact | property | 1 | BUS-01, BUS-02 | 1 | 없음 |
| http://example.org/ontology/devops#vulnerabilityCount | property | 1 | BUS-01, DEV-02 | 1 | 없음 |
| http://example.org/ontology/ecommerce#CustomerSession | class | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/ecommerce#OrderStatusEvent | class | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/ecommerce#OrderTask | class | 2 | EC-02 | 1 | 없음 |
| http://example.org/ontology/ecommerce#Product | class | 1 | EC-01 | 1 | 없음 |
| http://example.org/ontology/ecommerce#RecommendationAgent | class | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/ecommerce#changedAt | property | 1 | SYN-04 | 0 | 없음 |
| http://example.org/ontology/ecommerce#eventOrder | property | 1 | SYN-04 | 0 | 없음 |
| http://example.org/ontology/ecommerce#fromStatus | property | 1 | SYN-04 | 0 | 없음 |
| http://example.org/ontology/ecommerce#handledBy | property | 1 | EC-02 | 1 | 없음 |
| http://example.org/ontology/ecommerce#hasStatusEvent | property | 1 | SYN-04 | 0 | 없음 |
| http://example.org/ontology/ecommerce#includesProduct | property | 1 | EC-02 | 1 | 없음 |
| http://example.org/ontology/ecommerce#orderStatus | property | 1 | EC-02 | 1 | 없음 |
| http://example.org/ontology/ecommerce#price | property | 1 | EC-01 | 1 | 없음 |
| http://example.org/ontology/ecommerce#priceCurrency | property | 1 | EC-01 | 0 | 없음 |
| http://example.org/ontology/ecommerce#priceCurrencyStatus | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/ecommerce#productId | property | 1 | EC-01 | 1 | 없음 |
| http://example.org/ontology/ecommerce#recommends | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/ecommerce#toStatus | property | 1 | SYN-04 | 0 | 없음 |
| http://example.org/ontology/healthcare#ClinicalObservation | class | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#ClinicalReport | class | 2 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#DiagnosticTask | class | 3 | HC-02 | 1 | 없음 |
| http://example.org/ontology/healthcare#MedicalAnalysisAgent | class | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#PatientRecord | class | 1 | HC-01 | 1 | 없음 |
| http://example.org/ontology/healthcare#PrivacyClassification | class | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#analyzedBy | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#associatedWithRecord | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#codeSystem | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#confidenceScore | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#dataClassification | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#diagnosticStatus | property | 1 | HC-02 | 1 | 없음 |
| http://example.org/ontology/healthcare#findingText | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#generatesObservation | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#generatesReport | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#numericValue | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#observationCode | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#observationStatus | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#observedAt | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#observesRecord | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#patientId | property | 1 | 미포함 | 1 | cq |
| http://example.org/ontology/healthcare#reportCode | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#reportCodeSystem | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#reportResult | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#reportStatus | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#taskIntent | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#textValue | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#unitCode | property | 1 | 미포함 | 0 | cq |
| http://example.org/ontology/healthcare#unitCodeSystem | property | 1 | 미포함 | 0 | cq |
| https://example.org/agent#Agent | class | 1 | 미포함 | 3 | cq |
| https://example.org/agent#AgentAssignment | class | 1 | 미포함 | 3 | cq |
| https://example.org/agent#Artifact | class | 1 | 미포함 | 2 | cq |
| https://example.org/agent#Capability | class | 0 | 미포함 | 3 | class_shape, cq |
| https://example.org/agent#Handoff | class | 1 | BUS-03 | 1 | 없음 |
| https://example.org/agent#HumanAgent | class | 1 | 미포함 | 0 | cq |
| https://example.org/agent#Project | class | 1 | AG-02, BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#ReviewDecision | class | 1 | AG-02 | 1 | 없음 |
| https://example.org/agent#ReviewRun | class | 3 | BUS-03 | 1 | 없음 |
| https://example.org/agent#Role | class | 0 | 미포함 | 3 | class_shape, cq |
| https://example.org/agent#SoftwareAgent | class | 1 | 미포함 | 3 | cq |
| https://example.org/agent#Task | class | 1 | AG-01 | 3 | 없음 |
| https://example.org/agent#TaskRun | class | 2 | 미포함 | 3 | cq |
| https://example.org/agent#acceptanceCriteria | property | 2 | 미포함 | 4 | cq |
| https://example.org/agent#artifactType | property | 1 | 미포함 | 2 | cq |
| https://example.org/agent#artifactUri | property | 1 | 미포함 | 2 | cq |
| https://example.org/agent#assignedTo | property | 1 | AG-01 | 3 | 없음 |
| https://example.org/agent#assignmentAgent | property | 1 | 미포함 | 3 | cq |
| https://example.org/agent#assignmentRole | property | 1 | 미포함 | 3 | cq |
| https://example.org/agent#checksum | property | 1 | 미포함 | 0 | cq |
| https://example.org/agent#containsArtifact | property | 1 | BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#decision | property | 1 | AG-02, BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#decisionAbout | property | 1 | AG-02, BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#dependsOn | property | 1 | AG-01 | 2 | 없음 |
| https://example.org/agent#errorCode | property | 1 | 미포함 | 0 | cq |
| https://example.org/agent#goal | property | 1 | 미포함 | 1 | cq |
| https://example.org/agent#hasAssignment | property | 1 | 미포함 | 3 | cq |
| https://example.org/agent#hasCapability | property | 1 | 미포함 | 3 | cq |
| https://example.org/agent#hasDecision | property | 1 | BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#hasFinalArtifact | property | 1 | AG-02, BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#hasHandoff | property | 1 | 미포함 | 1 | cq |
| https://example.org/agent#hasTask | property | 1 | BUS-03, BUS-04 | 3 | 없음 |
| https://example.org/agent#implementsTask | property | 1 | BUS-03, BUS-04, SYN-03 | 3 | 없음 |
| https://example.org/agent#reason | property | 1 | 미포함 | 1 | cq |
| https://example.org/agent#requiresCapability | property | 1 | 미포함 | 3 | cq |
| https://example.org/agent#reviews | property | 1 | BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#status | property | 1 | SYN-03 | 3 | 없음 |
| https://example.org/agent#taskObjective | property | 1 | AG-01 | 3 | 없음 |
| https://example.org/agent#toAgent | property | 1 | BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#toTask | property | 1 | BUS-03, BUS-04 | 1 | 없음 |
| https://example.org/agent#toolVersion | property | 1 | 미포함 | 3 | cq |
| https://example.org/agent#version | property | 2 | 미포함 | 5 | cq |
| https://example.org/mv#AIAgent | class | 0 | 미포함 | 9 | class_shape, cq |
| https://example.org/mv#AudioAsset | class | 1 | 미포함 | 2 | cq |
| https://example.org/mv#AudioGenerationTask | class | 2 | 미포함 | 2 | cq |
| https://example.org/mv#CreativeBrief | class | 1 | 미포함 | 2 | cq |
| https://example.org/mv#GenerationTask | class | 2 | 미포함 | 0 | cq |
| https://example.org/mv#ImageAsset | class | 1 | BMV-02, SYN-06, SYN-07 | 4 | 없음 |
| https://example.org/mv#ImageGenerationTask | class | 2 | 미포함 | 1 | cq |
| https://example.org/mv#LyricGenerationTask | class | 2 | 미포함 | 1 | cq |
| https://example.org/mv#MediaAsset | class | 0 | 미포함 | 0 | class_shape, cq |
| https://example.org/mv#MusicVideo | class | 1 | 미포함 | 2 | cq |
| https://example.org/mv#MusicVideoProject | class | 1 | BMV-01, BMV-02, BMV-03, BMV-05, BMV-06, BUS-05, BUS-06 | 2 | 없음 |
| https://example.org/mv#QualityCheckTask | class | 2 | 미포함 | 0 | cq |
| https://example.org/mv#RenderTask | class | 2 | 미포함 | 2 | cq |
| https://example.org/mv#Shot | class | 1 | MV-01 | 4 | 없음 |
| https://example.org/mv#SubtitleGenerationTask | class | 2 | 미포함 | 1 | cq |
| https://example.org/mv#Timeline | class | 1 | 미포함 | 2 | cq |
| https://example.org/mv#TranslationTask | class | 2 | 미포함 | 1 | cq |
| https://example.org/mv#bpm | property | 1 | 미포함 | 1 | cq |
| https://example.org/mv#checksum | property | 1 | BMV-05, SYN-11 | 0 | 없음 |
| https://example.org/mv#dependsOn | property | 1 | E2E-02 | 3 | 없음 |
| https://example.org/mv#durationSeconds | property | 2 | MV-02 | 4 | 없음 |
| https://example.org/mv#endSecond | property | 1 | BMV-03, MV-01 | 4 | 없음 |
| https://example.org/mv#fileUri | property | 3 | MV-02 | 8 | 없음 |
| https://example.org/mv#genre | property | 1 | 미포함 | 1 | cq |
| https://example.org/mv#hasAudio | property | 1 | BMV-01, BUS-05, BUS-06 | 2 | 없음 |
| https://example.org/mv#hasBrief | property | 1 | 미포함 | 2 | cq |
| https://example.org/mv#hasFinalVideo | property | 1 | BMV-01, BUS-05, BUS-06 | 2 | 없음 |
| https://example.org/mv#hasImage | property | 1 | BMV-02, BMV-05, BMV-06, SYN-05, SYN-10 | 4 | 없음 |
| https://example.org/mv#hasShot | property | 1 | BMV-03, BUS-05, BUS-06 | 4 | 없음 |
| https://example.org/mv#hasTimeline | property | 2 | BMV-01, BMV-03, BUS-05, BUS-06 | 4 | 없음 |
| https://example.org/mv#height | property | 1 | MV-02 | 4 | 없음 |
| https://example.org/mv#lyricText | property | 1 | 미포함 | 2 | cq |
| https://example.org/mv#mimeType | property | 1 | 미포함 | 0 | cq |
| https://example.org/mv#modelVersion | property | 1 | BUS-05, SYN-01 | 3 | 없음 |
| https://example.org/mv#orderIndex | property | 1 | MV-01 | 4 | 없음 |
| https://example.org/mv#promptText | property | 1 | BUS-05, SYN-01 | 2 | 없음 |
| https://example.org/mv#startSecond | property | 1 | BMV-03, MV-01 | 4 | 없음 |
| https://example.org/mv#status | property | 1 | E2E-01 | 8 | 없음 |
| https://example.org/mv#targetDurationSeconds | property | 1 | 미포함 | 2 | cq |
| https://example.org/mv#usesAudio | property | 1 | BMV-01, BUS-05, BUS-06 | 2 | 없음 |
| https://example.org/mv#usesImage | property | 1 | BUS-05, BUS-06 | 4 | 없음 |
| https://example.org/mv#usesInput | property | 1 | E2E-02 | 1 | 없음 |
| https://example.org/mv#width | property | 1 | MV-02 | 4 | 없음 |
| https://example.org/ontology/academic#Course | class | 1 | AC-01 | 1 | 없음 |
| https://example.org/ontology/academic#Professor | class | 1 | AC-02 | 0 | 없음 |
| https://example.org/ontology/academic#Student | class | 1 | 미포함 | 1 | cq |
| https://example.org/ontology/academic#courseCode | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/academic#credits | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/academic#enrollsIn | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/academic#hasStudent | property | 1 | AC-01 | 0 | 없음 |
| https://example.org/ontology/academic#teaches | property | 1 | AC-02 | 0 | 없음 |
| https://example.org/ontology/core#Agent | class | 0 | 미포함 | 0 | class_shape, cq |
| https://example.org/ontology/core#Artifact | class | 0 | SYN-07 | 0 | class_shape |
| https://example.org/ontology/core#Project | class | 0 | 미포함 | 0 | class_shape, cq |
| https://example.org/ontology/core#SensitiveRecord | class | 0 | 미포함 | 0 | class_shape, cq |
| https://example.org/ontology/core#Task | class | 0 | 미포함 | 0 | class_shape, cq |
| https://example.org/ontology/core#TaskRun | class | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/core#runAgent | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/core#runEndedAt | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/core#runInput | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/core#runOutput | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/core#runStartedAt | property | 1 | 미포함 | 0 | cq |
| https://example.org/ontology/core#taskStatus | property | 1 | 미포함 | 0 | domain, cq |
| https://example.org/ontology/custom/ai-film#EditVersion | class | 1 | AIF-04, AIF-05 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#FilmProject | class | 1 | AIF-01, AIF-05 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#GenerationTask | class | 1 | AIF-01, AIF-02 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#MediaAsset | class | 1 | AIF-03 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#ReviewDecision | class | 1 | AIF-03 | 4 | 없음 |
| https://example.org/ontology/custom/ai-film#Scene | class | 1 | AIF-01 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#Screenplay | class | 1 | AIF-01 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#Shot | class | 1 | AIF-01 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#assetStatus | property | 1 | AIF-03, AIF-04 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#assetUri | property | 1 | AIF-03, AIF-04 | 0 | 없음 |
| https://example.org/ontology/custom/ai-film#decision | property | 1 | AIF-03, AIF-04 | 4 | 없음 |
| https://example.org/ontology/custom/ai-film#decisionReason | property | 1 | AIF-03 | 4 | 없음 |
| https://example.org/ontology/custom/ai-film#editStatus | property | 1 | AIF-05 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#generationEvidenceUri | property | 1 | AIF-02 | 0 | 없음 |
| https://example.org/ontology/custom/ai-film#hasEditVersion | property | 2 | AIF-04, AIF-05 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#hasGenerationTask | property | 2 | AIF-01 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#hasReview | property | 2 | AIF-03, AIF-04 | 4 | 없음 |
| https://example.org/ontology/custom/ai-film#hasScene | property | 2 | AIF-01 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#hasScreenplay | property | 2 | AIF-01 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#hasShot | property | 2 | AIF-01 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#mediaType | property | 1 | AIF-03 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#modelIdentifier | property | 1 | AIF-02 | 0 | 없음 |
| https://example.org/ontology/custom/ai-film#modelKnowledgeStatus | property | 1 | AIF-02 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#plannedAsset | property | 1 | AIF-02 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#promptText | property | 1 | AIF-01 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#reviewEvidenceUri | property | 1 | AIF-03, AIF-04 | 0 | 없음 |
| https://example.org/ontology/custom/ai-film#reviewKind | property | 2 | AIF-03, AIF-04 | 4 | 없음 |
| https://example.org/ontology/custom/ai-film#sceneOrder | property | 1 | AIF-01 | 1 | 없음 |
| https://example.org/ontology/custom/ai-film#shotOrder | property | 1 | AIF-01 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#sourceEvidenceUri | property | 1 | AIF-03, AIF-04 | 0 | 없음 |
| https://example.org/ontology/custom/ai-film#targetDurationSeconds | property | 1 | AIF-01 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#taskStatus | property | 1 | AIF-01, AIF-02 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#usesAsset | property | 1 | AIF-04, AIF-05 | 2 | 없음 |
| https://example.org/ontology/custom/ai-film#versionLabel | property | 1 | AIF-04, AIF-05 | 1 | 없음 |
| https://example.org/ontology/evidence#ClaimScope | class | 1 | EV-02 | 3 | 없음 |
| https://example.org/ontology/evidence#EvidenceRecord | class | 1 | EV-01, EV-03 | 3 | 없음 |
| https://example.org/ontology/evidence#VerificationClaim | class | 1 | EV-01, EV-02, EV-03 | 6 | 없음 |
| https://example.org/ontology/evidence#VerificationStatus | class | 1 | EV-02 | 4 | 없음 |
| https://example.org/ontology/evidence#aboutAsset | property | 1 | EV-02 | 6 | 없음 |
| https://example.org/ontology/evidence#assetIdentifier | property | 1 | EV-01, EV-02, EV-03 | 6 | 없음 |
| https://example.org/ontology/evidence#checkedAt | property | 1 | EV-01, EV-02, EV-03 | 6 | 없음 |
| https://example.org/ontology/evidence#checkedBy | property | 1 | EV-01, EV-02, EV-03 | 6 | 없음 |
| https://example.org/ontology/evidence#evidenceRole | property | 1 | EV-01, EV-03 | 3 | 없음 |
| https://example.org/ontology/evidence#evidenceURI | property | 1 | EV-01, EV-03 | 3 | 없음 |
| https://example.org/ontology/evidence#expectedSHA256 | property | 1 | EV-01 | 2 | 없음 |
| https://example.org/ontology/evidence#hasEvidence | property | 1 | EV-01, EV-03 | 4 | 없음 |
| https://example.org/ontology/evidence#originalModel | property | 1 | EV-03 | 1 | 없음 |
| https://example.org/ontology/evidence#originalOriginIRI | property | 1 | EV-03 | 1 | 없음 |
| https://example.org/ontology/evidence#originalPrompt | property | 1 | EV-03 | 1 | 없음 |
| https://example.org/ontology/evidence#projectIdentifier | property | 1 | EV-01 | 6 | 없음 |
| https://example.org/ontology/evidence#scope | property | 1 | EV-01, EV-02, EV-03 | 6 | 없음 |
| https://example.org/ontology/evidence#sha256 | property | 1 | EV-01, EV-03 | 3 | 없음 |
| https://example.org/ontology/evidence#sourceCopyState | property | 1 | EV-01 | 2 | 없음 |
| https://example.org/ontology/evidence#status | property | 1 | EV-01, EV-02, EV-03 | 6 | 없음 |
| https://example.org/ontology/evidence#unknownReason | property | 1 | EV-01, EV-02 | 2 | 없음 |
| https://example.org/ontology/evidence#verifiedAt | property | 1 | EV-03 | 2 | 없음 |

## 구조 예외와 CQ 미포함 사유

- `http://example.org/ontology/devops#BuildArtifact` (CQ 미포함): Existing query coverage debt: the 빌드 산출물 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#DevOpsAgent` (CQ 미포함): Existing query coverage debt: the DevOps 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#PipelineTask` (CQ 미포함): Existing query coverage debt: the 파이프라인 작업 실행 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#TargetEnvironment` (CQ 미포함): Existing query coverage debt: the 배포 대상 환경 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#VulnerabilityReport` (CQ 미포함): Existing query coverage debt: the 취약점 보고서 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#branchName` (CQ 미포함): Existing query coverage debt: the 브랜치 이름 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#dependsOn` (CQ 미포함): Existing query coverage debt: the 선행 파이프라인 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#environmentName` (CQ 미포함): Existing query coverage debt: the 환경 이름 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#generatesReport` (CQ 미포함): Existing query coverage debt: the 취약점 보고서를 생성 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#imageTag` (CQ 미포함): Existing query coverage debt: the 이미지 태그 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/devops#managedBy` (CQ 미포함): Existing query coverage debt: the 담당 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/ecommerce#CustomerSession` (CQ 미포함): Existing query coverage debt: the 고객 세션 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/ecommerce#OrderStatusEvent` (CQ 미포함): Existing query coverage debt: the 주문 상태 변경 이벤트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/ecommerce#RecommendationAgent` (CQ 미포함): Existing query coverage debt: the 추천 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/ecommerce#priceCurrencyStatus` (CQ 미포함): Existing query coverage debt: the 가격 통화 확인 상태 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/ecommerce#recommends` (CQ 미포함): Existing query coverage debt: the 상품을 추천 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#ClinicalObservation` (CQ 미포함): Existing query coverage debt: the 임상 관측값 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#ClinicalReport` (CQ 미포함): Existing query coverage debt: the 임상 분석 보고서 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#MedicalAnalysisAgent` (CQ 미포함): Existing query coverage debt: the 의료 분석 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#PrivacyClassification` (CQ 미포함): Existing query coverage debt: the 개인정보 분류 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#analyzedBy` (CQ 미포함): Existing query coverage debt: the 분석 담당 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#associatedWithRecord` (CQ 미포함): Existing query coverage debt: the 관련 환자 기록 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#codeSystem` (CQ 미포함): Existing query coverage debt: the 코드 체계 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#confidenceScore` (CQ 미포함): Existing query coverage debt: the 모델 신뢰 점수 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#dataClassification` (CQ 미포함): Existing query coverage debt: the 기록 분류 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#findingText` (CQ 미포함): Existing query coverage debt: the 분석 소견 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#generatesObservation` (CQ 미포함): Existing query coverage debt: the 임상 관측값을 생성 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#generatesReport` (CQ 미포함): Existing query coverage debt: the 분석 보고서를 생성 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#numericValue` (CQ 미포함): Existing query coverage debt: the 수치 관측값 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#observationCode` (CQ 미포함): Existing query coverage debt: the 관측 코드 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#observationStatus` (CQ 미포함): Existing query coverage debt: the 관측 결과 상태 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#observedAt` (CQ 미포함): Existing query coverage debt: the 관측 시각 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#observesRecord` (CQ 미포함): Existing query coverage debt: the 관측 대상 환자 기록 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#patientId` (CQ 미포함): Existing query coverage debt: the 내부 환자 키 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#reportCode` (CQ 미포함): Existing query coverage debt: the 보고서 코드 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#reportCodeSystem` (CQ 미포함): Existing query coverage debt: the 보고서 코드 체계 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#reportResult` (CQ 미포함): Existing query coverage debt: the 보고서 결과 관측값 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#reportStatus` (CQ 미포함): Existing query coverage debt: the 보고서 상태 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#taskIntent` (CQ 미포함): Existing query coverage debt: the 진단 작업 의도 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#textValue` (CQ 미포함): Existing query coverage debt: the 문자 관측값 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#unitCode` (CQ 미포함): Existing query coverage debt: the UCUM 단위 코드 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `http://example.org/ontology/healthcare#unitCodeSystem` (CQ 미포함): Existing query coverage debt: the 단위 코드 체계 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#Agent` (CQ 미포함): Existing query coverage debt: the 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#AgentAssignment` (CQ 미포함): Existing query coverage debt: the 프로젝트 역할 배정 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#Artifact` (CQ 미포함): Existing query coverage debt: the 결과물 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#Capability` (class_shape): Capability is a reusable classification; actor/task reference constraints check its type, but no capability-specific required fields are defined.
- `https://example.org/agent#Capability` (CQ 미포함): Existing query coverage debt: the 기능 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#HumanAgent` (CQ 미포함): Existing query coverage debt: the 사람 참여자 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#Role` (class_shape): Role is a reusable classification; assignments constrain the role reference, while no universal role fields are required.
- `https://example.org/agent#Role` (CQ 미포함): Existing query coverage debt: the 역할 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#SoftwareAgent` (CQ 미포함): Existing query coverage debt: the 소프트웨어 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#TaskRun` (CQ 미포함): Existing query coverage debt: the 작업 실행 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#acceptanceCriteria` (CQ 미포함): Existing query coverage debt: the 완료 기준 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#artifactType` (CQ 미포함): Existing query coverage debt: the 결과물 유형 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#artifactUri` (CQ 미포함): Existing query coverage debt: the 결과물 위치 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#assignmentAgent` (CQ 미포함): Existing query coverage debt: the 배정된 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#assignmentRole` (CQ 미포함): Existing query coverage debt: the 배정된 역할 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#checksum` (CQ 미포함): Existing query coverage debt: the 체크섬 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#errorCode` (CQ 미포함): Existing query coverage debt: the 오류 코드 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#goal` (CQ 미포함): Existing query coverage debt: the 공동 목표 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#hasAssignment` (CQ 미포함): Existing query coverage debt: the 프로젝트 역할 배정 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#hasCapability` (CQ 미포함): Existing query coverage debt: the 기능을 보유 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#hasHandoff` (CQ 미포함): Existing query coverage debt: the 인계 묶음을 전달 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#reason` (CQ 미포함): Existing query coverage debt: the 검수 사유 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#requiresCapability` (CQ 미포함): Existing query coverage debt: the 기능을 요구 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#toolVersion` (CQ 미포함): Existing query coverage debt: the 사용 도구 버전 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/agent#version` (CQ 미포함): Existing query coverage debt: the 버전 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#AIAgent` (class_shape): The actor class allows local tools and imported agents with unknown configuration; GenerationTask constrains actor references without requiring fabricated model settings.
- `https://example.org/mv#AIAgent` (CQ 미포함): Existing query coverage debt: the AI 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#AudioAsset` (CQ 미포함): Existing query coverage debt: the 음원 자산 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#AudioGenerationTask` (CQ 미포함): Existing query coverage debt: the 음원 생성 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#CreativeBrief` (CQ 미포함): Existing query coverage debt: the 제작 요청 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#GenerationTask` (CQ 미포함): Existing query coverage debt: the 생성 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#ImageGenerationTask` (CQ 미포함): Existing query coverage debt: the 이미지 생성 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#LyricGenerationTask` (CQ 미포함): Existing query coverage debt: the 가사 생성 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#MediaAsset` (class_shape): MediaAsset is a broad base class; concrete audio/image/video classes validate metadata, and predicate contracts validate optional common fields.
- `https://example.org/mv#MediaAsset` (CQ 미포함): Existing query coverage debt: the 미디어 자산 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#MusicVideo` (CQ 미포함): Existing query coverage debt: the 뮤직비디오 영상 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#QualityCheckTask` (CQ 미포함): Existing query coverage debt: the 품질 검수 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#RenderTask` (CQ 미포함): Existing query coverage debt: the 렌더링 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#SubtitleGenerationTask` (CQ 미포함): Existing query coverage debt: the 자막 생성 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#Timeline` (CQ 미포함): Existing query coverage debt: the 타임라인 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#TranslationTask` (CQ 미포함): Existing query coverage debt: the 번역 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#bpm` (CQ 미포함): Existing query coverage debt: the 분당 박자 수 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#genre` (CQ 미포함): Existing query coverage debt: the 음악 장르 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#hasBrief` (CQ 미포함): Existing query coverage debt: the 제작 요청 참조 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#lyricText` (CQ 미포함): Existing query coverage debt: the 가사 문장 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#mimeType` (CQ 미포함): Existing query coverage debt: the 미디어 형식 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/mv#targetDurationSeconds` (CQ 미포함): Existing query coverage debt: the 목표 재생 시간(초) term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/academic#Student` (CQ 미포함): Existing query coverage debt: the 학생 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/academic#courseCode` (CQ 미포함): Existing query coverage debt: the 과목 코드 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/academic#credits` (CQ 미포함): Existing query coverage debt: the 학점 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/academic#enrollsIn` (CQ 미포함): Existing query coverage debt: the 수강한다 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#Agent` (class_shape): The core actor abstraction imposes no domain-specific identity/configuration fields; concrete domain agent shapes supply constraints.
- `https://example.org/ontology/core#Agent` (CQ 미포함): Existing query coverage debt: the 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#Artifact` (class_shape): The core artifact abstraction does not assume a file format or location; concrete artifact subclasses and runOutput references supply constraints.
- `https://example.org/ontology/core#Project` (class_shape): The core project abstraction does not require a domain-specific deliverable; concrete project subclasses define required relations.
- `https://example.org/ontology/core#Project` (CQ 미포함): Existing query coverage debt: the 프로젝트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#SensitiveRecord` (class_shape): SensitiveRecord is an access/retention classification, not a universal record structure; healthcare record shapes define clinical constraints.
- `https://example.org/ontology/core#SensitiveRecord` (CQ 미포함): Existing query coverage debt: the 민감 기록 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#Task` (class_shape): The planned-task abstraction differs across domains; concrete task shapes supply status and dependency contracts.
- `https://example.org/ontology/core#Task` (CQ 미포함): Existing query coverage debt: the 계획 작업 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#TaskRun` (CQ 미포함): Existing query coverage debt: the 작업 실행 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#runAgent` (CQ 미포함): Existing query coverage debt: the 실행 담당 에이전트 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#runEndedAt` (CQ 미포함): Existing query coverage debt: the 실행 종료 시각 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#runInput` (CQ 미포함): Existing query coverage debt: the 실행 입력 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#runOutput` (CQ 미포함): Existing query coverage debt: the 실행 결과물 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#runStartedAt` (CQ 미포함): Existing query coverage debt: the 실행 시작 시각 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.
- `https://example.org/ontology/core#taskStatus` (domain): Domain-neutral status abstraction shared by plans and runs; domain subproperties define their domain, while the optional value contract enforces string values.
- `https://example.org/ontology/core#taskStatus` (CQ 미포함): Existing query coverage debt: the 작업 상태 term is not directly referenced by a catalog query. Track it for domain CQ expansion; do not count this as completed coverage.

## 해석 범위

- CQ coverage means a term is referenced by parsed query algebra; golden-answer tests verify behavior separately.
- Instance use counts are explicit facts in bundled examples, without inferred duplicates.
- Provenance links do not verify original model, prompt, source contents or generation quality.
- Only counts are exported for instances; reports omit patient identities and SHACL value messages.
- CQ backlog is remaining work, not completed test coverage.
