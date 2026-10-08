# 온톨로지 Competency Questions

이 목록은 각 도메인 그래프가 답할 수 있어야 하는 대표 질문과 실행 가능한 SPARQL을 연결한다. 질의 결과가 비어 있으면 예제 데이터에 관계가 기록되지 않았다는 뜻이며, 누락된 사실을 채워 넣으라는 뜻은 아니다. 주요 질문은 SPARQL 대화형 쿼리의 도메인 템플릿에도 제공한다.

## 공통 실행·출처 질문

각 도메인에서 실행을 표현하는 방법은 다르다. 이 프로젝트의 공통 코어는 계획 작업과 실제 실행을 구별하며, 공통 상태·담당자·결과물 관계를 정한다. 새 도메인의 질문에는 실행 ID, 상태, 에이전트, 생성 결과 중 필요한 축을 명시한다.

## 뮤직비디오 (mv)

### MV-01. 장면은 재생 순서와 어느 시간 구간에 배치되는가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX mv: <https://example.org/mv#>
SELECT ?shotName ?order ?startSec ?endSec WHERE {
  ?shot a mv:Shot ;
        rdfs:label ?shotName ;
        mv:orderIndex ?order ;
        mv:startSecond ?startSec ;
        mv:endSecond ?endSec .
}
ORDER BY ?order
~~~

### MV-02. 오디오·이미지 자산의 파일 위치와 기본 기술 정보는 무엇인가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
SELECT ?asset ?file ?duration ?width ?height WHERE {
  ?asset mv:fileUri ?file .
  OPTIONAL { ?asset mv:durationSeconds ?duration }
  OPTIONAL { ?asset mv:width ?width }
  OPTIONAL { ?asset mv:height ?height }
}
ORDER BY ?asset
~~~

## 가사·자막·번역 파이프라인 (e2e profile of mv)

### E2E-01. 텍스트 작업의 상태와 담당 에이전트는 무엇인가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX mv: <https://example.org/mv#>
SELECT ?task ?taskLabel ?status ?agentLabel WHERE {
  ?task mv:status ?status ;
        prov:wasAssociatedWith ?agent .
  ?agent rdfs:label ?agentLabel .
  OPTIONAL { ?task rdfs:label ?taskLabel }
}
ORDER BY ?task
~~~

### E2E-02. 작업은 어떤 선행 작업에 의존하거나 어떤 자료를 입력으로 사용하는가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
SELECT ?task ?relation ?target WHERE {
  { ?task mv:dependsOn ?target . BIND("task-dependency" AS ?relation) }
  UNION
  { ?task mv:usesInput ?target . BIND("input" AS ?relation) }
}
ORDER BY ?task ?relation
~~~

## DevOps (devops)

### DEV-01. 각 파이프라인의 상태와 포함 작업은 무엇인가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX devops: <http://example.org/ontology/devops#>
SELECT ?pipeId ?status ?task ?taskLabel WHERE {
  ?pipe a devops:DevOpsPipeline ;
        devops:pipelineId ?pipeId ;
        devops:executionStatus ?status ;
        devops:hasTask ?task .
  OPTIONAL { ?task rdfs:label ?taskLabel }
}
ORDER BY ?pipeId ?task
~~~

### DEV-02. 보안 스캔에서 기록된 취약점 수는 얼마인가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX devops: <http://example.org/ontology/devops#>
SELECT ?task ?label ?vulnerabilities WHERE {
  ?task a devops:SecurityScanTask ;
        devops:vulnerabilityCount ?vulnerabilities .
  OPTIONAL { ?task rdfs:label ?label }
}
~~~

## 에이전트 협업 (agent)

### AG-01. 각 계획 작업의 목표, 담당자, 선행 작업은 무엇인가?

~~~sparql
PREFIX ag: <https://example.org/agent#>
SELECT ?task ?objective ?agent ?dependsOn WHERE {
  ?task a ag:Task ;
        ag:taskObjective ?objective ;
        ag:assignedTo ?agent .
  OPTIONAL { ?task ag:dependsOn ?dependsOn }
}
ORDER BY ?task
~~~

### AG-02. 프로젝트의 최종 결과물에 승인 검수 판정이 연결되어 있는가?

~~~sparql
PREFIX ag: <https://example.org/agent#>
SELECT ?project ?artifact ?decision WHERE {
  ?project a ag:Project ; ag:hasFinalArtifact ?artifact .
  OPTIONAL {
    ?review a ag:ReviewDecision ;
            ag:decisionAbout ?artifact ;
            ag:decision ?decision .
  }
}
ORDER BY ?project ?artifact
~~~

## 전자상거래 (ecommerce)

### EC-01. 상품별 카탈로그 가격은 얼마인가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ecom: <http://example.org/ontology/ecommerce#>
SELECT ?product ?label ?productId ?price ?currency WHERE {
  ?product a ecom:Product ;
           ecom:productId ?productId ;
           ecom:price ?price .
  OPTIONAL { ?product rdfs:label ?label }
  OPTIONAL { ?product ecom:priceCurrency ?currency }
}
ORDER BY ?productId
~~~

### EC-02. 주문의 상태와 연결된 상품은 무엇인가?

~~~sparql
PREFIX ecom: <http://example.org/ontology/ecommerce#>
SELECT ?order ?status ?agent ?product WHERE {
  ?order a ecom:OrderTask ;
         ecom:orderStatus ?status ;
         ecom:handledBy ?agent .
  OPTIONAL { ?order ecom:includesProduct ?product }
}
ORDER BY ?order
~~~

## 헬스케어 (healthcare)

### HC-01. 환자 키나 레코드 URI를 반환하지 않고 기록 수를 집계할 수 있는가?

~~~sparql
PREFIX health: <http://example.org/ontology/healthcare#>
SELECT (COUNT(DISTINCT ?record) AS ?recordCount) WHERE {
  ?record a health:PatientRecord .
}
~~~

### HC-02. 환자와 소견 텍스트를 출력하지 않고 진단 상태별 실행 수를 집계할 수 있는가?

~~~sparql
PREFIX health: <http://example.org/ontology/healthcare#>
SELECT ?status (COUNT(?task) AS ?taskCount) WHERE {
  ?task a health:DiagnosticTask ;
        health:diagnosticStatus ?status .
}
GROUP BY ?status
ORDER BY ?status
~~~

## 대학 수강 (academic)

### AC-01. 각 과목에 실제로 기록된 학생은 누구인가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX academic: <https://example.org/ontology/academic#>
SELECT ?courseLabel ?studentLabel WHERE {
  ?course a academic:Course ;
          rdfs:label ?courseLabel ;
          academic:hasStudent ?student .
  ?student rdfs:label ?studentLabel .
}
ORDER BY ?courseLabel ?studentLabel
~~~

### AC-02. 교수와 담당 과목의 기록된 연결은 무엇인가?

~~~sparql
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX academic: <https://example.org/ontology/academic#>
SELECT ?professorLabel ?courseLabel WHERE {
  ?professor a academic:Professor ;
             rdfs:label ?professorLabel ;
             academic:teaches ?course .
  ?course rdfs:label ?courseLabel .
}
ORDER BY ?professorLabel ?courseLabel
~~~

## 합성 회귀 사례: 출처·이력·프로젝트 범위·추론

아래 SYN 질문은 `tests/fixtures/competency_synthetic.trig`의 고정 합성 데이터를 사용한다. 이름 있는 그래프 `ex:alpha`, `ex:beta`는 프로젝트 범위를 나타내며, 나머지 사례는 기본 그래프에서 실행한다. SYN-07과 SYN-08은 로컬 MV/Core 스키마를 합친 뒤 OWL-RL로 확장한 기본 그래프에서 실행한다. 원본 데이터에는 추론 결과를 저장하지 않는다.

`not-recorded`는 이 그래프에서 근거를 찾지 못했다는 뜻이다. 생성 모델이나 프롬프트가 실제로 없다는 결론 또는 출처가 확인됐다는 결론으로 바꾸지 않는다. 중복 ID는 프로젝트 내부의 데이터 품질 진단이며, 서로 다른 IRI를 OWL 모순으로 판단하는 규칙이 아니다.

### SYN-01. 자산의 생성 모델·프롬프트·근거 자료는 어디까지 기록되어 있는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX mv: <https://example.org/mv#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?asset ?model ?prompt ?evidence ?recording WHERE {
  VALUES ?asset { ex:verifiedAsset ex:unverifiedAsset }
  ?asset prov:wasGeneratedBy ?run .
  OPTIONAL { ?run mv:modelVersion ?model }
  OPTIONAL { ?run mv:promptText ?prompt }
  OPTIONAL { ?run prov:used ?evidence }
  BIND(IF(BOUND(?model) && BOUND(?prompt) && BOUND(?evidence),
          "recorded", "not-recorded") AS ?recording)
}
ORDER BY ?asset
~~~

### SYN-02. 최종 자산에서 여러 단계의 파생 원본까지 추적할 수 있는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?ancestor WHERE {
  ex:verifiedAsset prov:wasDerivedFrom+ ?ancestor .
}
ORDER BY ?ancestor
~~~

### SYN-03. 한 계획 작업의 실패와 재시도 실행을 시간 순서로 구별할 수 있는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX ag: <https://example.org/agent#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?run ?status ?start ?end WHERE {
  ?run ag:implementsTask ex:plan ; ag:status ?status ;
       prov:startedAtTime ?start ; prov:endedAtTime ?end .
}
ORDER BY ?start ?run
~~~

### SYN-04. 현재 주문 상태와 별도로 기록된 상태 전이를 시간 순서로 반환하는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX ecom: <http://example.org/ontology/ecommerce#>
SELECT ?event ?from ?to ?changedAt WHERE {
  ex:order ecom:hasStatusEvent ?event .
  ?event ecom:eventOrder ex:order ; ecom:fromStatus ?from ;
         ecom:toStatus ?to ; ecom:changedAt ?changedAt .
}
ORDER BY ?changedAt ?event
~~~

### SYN-05. 같은 식별자를 쓰는 다른 프로젝트가 선택한 프로젝트의 결과에 섞이지 않는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX mv: <https://example.org/mv#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?asset ?identifier WHERE {
  GRAPH ex:alpha {
    ex:alphaProject mv:hasImage ?asset .
    ?asset dct:identifier ?identifier .
    FILTER(?identifier = "SHARED-001")
  }
}
ORDER BY ?asset
~~~

### SYN-06. 프로젝트 내부 중복 식별자와 프로젝트 간 재사용을 구별할 수 있는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX mv: <https://example.org/mv#>
PREFIX dct: <http://purl.org/dc/terms/>
SELECT ?scope ?identifier (COUNT(DISTINCT ?asset) AS ?count) WHERE {
  VALUES ?scope { ex:alpha ex:beta }
  GRAPH ?scope { ?asset a mv:ImageAsset ; dct:identifier ?identifier }
}
GROUP BY ?scope ?identifier
HAVING(COUNT(DISTINCT ?asset) > 1)
ORDER BY ?scope ?identifier
~~~

### SYN-07. 미디어 하위 클래스가 공통 Artifact로 추론되는 경로를 확인할 수 있는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX mv: <https://example.org/mv#>
PREFIX core: <https://example.org/ontology/core#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?asset ?assertedType ?commonType WHERE {
  VALUES ?asset { ex:inferenceAsset }
  VALUES ?assertedType { mv:ImageAsset }
  VALUES ?commonType { core:Artifact }
  ?asset a ?assertedType, ?commonType .
  ?assertedType rdfs:subClassOf+ ?commonType .
}
~~~

### SYN-08. 공통 실행 결과 관계에서 PROV 생성 및 역관계를 추론하는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?run ?asset WHERE {
  VALUES ?run { ex:inferenceRun }
  ?run prov:generated ?asset .
  ?asset prov:wasGeneratedBy ?run .
}
ORDER BY ?asset
~~~

### SYN-09. 출처가 기록되지 않은 자산에 파생 원본을 만들어 넣지 않는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?source WHERE {
  ex:unverifiedAsset prov:wasDerivedFrom+ ?source .
}
ORDER BY ?source
~~~

### SYN-10. 선택한 프로젝트에 다른 프로젝트 자산을 직접 연결한 경우를 찾는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX mv: <https://example.org/mv#>
SELECT ?asset WHERE {
  GRAPH ex:alpha { ex:alphaProject mv:hasImage ?asset }
  GRAPH ex:beta { ex:betaProject mv:hasImage ?asset }
}
ORDER BY ?asset
~~~

### SYN-11. 파일 무결성 값이 기록되지 않은 자산을 확인된 자산과 구별하는가?

~~~sparql
PREFIX ex: <https://example.test/competency/>
PREFIX mv: <https://example.org/mv#>
SELECT ?asset WHERE {
  VALUES ?asset { ex:verifiedAsset ex:unverifiedAsset }
  FILTER NOT EXISTS { ?asset mv:checksum ?checksum }
}
ORDER BY ?asset
~~~

## 업무 시나리오: 커밋·배포, 인계·검수, 미디어 전달

BUS 질문은 `tests/fixtures/business_scenarios.trig`의 normal, missing, conflict 그래프를 각각 조회한다. 모든 기록은 합성 자료다. 성공 기록이 있어도 같은 실행에 실패 기록이 함께 있으면 성공으로 반환하지 않는다. 근거 누락은 실제 사실의 부재를 의미하지 않는다.

### BUS-01. 어떤 커밋의 산출물이 성공적으로 배포됐고 같은 파이프라인의 취약점 수는 얼마인가?

~~~sparql
PREFIX dev: <http://example.org/ontology/devops#>
SELECT ?case ?commit ?artifact ?environment ?vulnerabilities WHERE {
  GRAPH ?case {
    ?pipeline a dev:DevOpsPipeline ; dev:commitHash ?commit ; dev:hasTask ?build, ?deploy, ?scan .
    ?build a dev:BuildTask ; dev:executionStatus "SUCCESS" ; dev:producesArtifact ?artifact .
    ?deploy a dev:DeploymentTask ; dev:executionStatus "SUCCESS" ; dev:deploysArtifact ?artifact ; dev:deployedTo ?environment .
    ?scan a dev:SecurityScanTask ; dev:executionStatus "SUCCESS" ; dev:vulnerabilityCount ?vulnerabilities .
    FILTER NOT EXISTS { ?deploy dev:executionStatus ?other . FILTER(?other != "SUCCESS") }
  }
}
ORDER BY ?case ?commit ?artifact
~~~

### BUS-02. 배포 근거가 누락됐거나 성공·실패 기록이 충돌하는 파이프라인은 무엇인가?

~~~sparql
PREFIX dev: <http://example.org/ontology/devops#>
SELECT ?case ?pipeline ?reason WHERE {
  GRAPH ?case {
    ?pipeline a dev:DevOpsPipeline ; dev:hasTask ?deploy .
    ?deploy a dev:DeploymentTask .
    BIND(IF(EXISTS { ?deploy dev:executionStatus "SUCCESS", "FAILED" }, "conflicting-status",
      IF(NOT EXISTS { ?deploy dev:deploysArtifact ?artifact }, "missing-deployed-artifact",
        IF(NOT EXISTS { ?pipeline dev:hasTask ?build . ?build a dev:BuildTask ; dev:executionStatus "SUCCESS" ; dev:producesArtifact ?built .
                        ?deploy dev:deploysArtifact ?built }, "unbuilt-deployment-artifact", "complete"))) AS ?reason)
    FILTER(?reason != "complete")
  }
}
ORDER BY ?case ?pipeline
~~~

### BUS-03. 인계된 결과물을 수신 담당자가 검수하고 프로젝트의 최종 결과물로 승인했는가?

~~~sparql
PREFIX ag: <https://example.org/agent#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?case ?project ?handoff ?artifact ?reviewer WHERE {
  GRAPH ?case {
    ?project a ag:Project ; ag:hasTask ?task ; ag:hasFinalArtifact ?artifact .
    ?handoff a ag:Handoff ; ag:toTask ?task ; ag:toAgent ?reviewer ; ag:containsArtifact ?artifact .
    ?review a ag:ReviewRun ; ag:implementsTask ?task ; prov:wasAssociatedWith ?reviewer ;
      ag:reviews ?artifact ; ag:hasDecision ?decision .
    ?decision ag:decisionAbout ?artifact ; ag:decision "approved" .
    FILTER NOT EXISTS { ?review ag:hasDecision ?otherDecision . ?otherDecision ag:decisionAbout ?artifact ; ag:decision "rejected" }
  }
}
ORDER BY ?case ?project ?artifact
~~~

### BUS-04. 최종 결과물의 인계·검수 연결이 누락됐거나 같은 검수에서 판정이 충돌하는가?

~~~sparql
PREFIX ag: <https://example.org/agent#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?case ?project ?reason WHERE {
  GRAPH ?case {
    ?project a ag:Project ; ag:hasFinalArtifact ?artifact .
    BIND(IF(EXISTS { ?review ag:reviews ?artifact ; ag:hasDecision ?accepted, ?rejected .
                       ?accepted ag:decisionAbout ?artifact ; ag:decision "approved" .
                       ?rejected ag:decisionAbout ?artifact ; ag:decision "rejected" }, "conflicting-review",
      IF(NOT EXISTS { ?project ag:hasTask ?task .
                      ?handoff ag:containsArtifact ?artifact ; ag:toTask ?task ; ag:toAgent ?reviewer .
                      ?review ag:implementsTask ?task ; prov:wasAssociatedWith ?reviewer ; ag:reviews ?artifact ; ag:hasDecision ?decision .
                      ?decision ag:decisionAbout ?artifact ; ag:decision "approved" }, "missing-review-chain", "complete")) AS ?reason)
    FILTER(?reason != "complete")
  }
}
ORDER BY ?case ?project
~~~

### BUS-05. 프로젝트와 일치하는 최종 영상의 사용 이미지와 생성 근거 기록 범위는 무엇인가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?case ?project ?video ?image ?knowledge WHERE {
  GRAPH ?case {
    ?project a mv:MusicVideoProject ; mv:hasFinalVideo ?video ; mv:hasAudio ?audio ; mv:hasTimeline ?timeline .
    ?video mv:usesAudio ?audio ; mv:hasTimeline ?timeline .
    ?timeline mv:hasShot ?shot . ?shot mv:usesImage ?image .
    BIND(IF(EXISTS { ?image prov:wasGeneratedBy ?run . ?run mv:modelVersion ?model ; mv:promptText ?prompt ; prov:used ?evidence },
      "generation-metadata-recorded", "generation-metadata-not-recorded") AS ?knowledge)
  }
}
ORDER BY ?case ?project ?image
~~~

### BUS-06. 최종 영상의 음원이 프로젝트와 다르거나 사용 이미지의 생성 근거가 누락됐는가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?case ?project ?reason WHERE {
  GRAPH ?case {
    ?project a mv:MusicVideoProject ; mv:hasFinalVideo ?video ; mv:hasAudio ?audio ; mv:hasTimeline ?timeline .
    BIND(IF(NOT EXISTS { ?video mv:usesAudio ?audio }, "project-audio-mismatch",
      IF(EXISTS { ?timeline mv:hasShot ?shot . ?shot mv:usesImage ?image .
                  FILTER NOT EXISTS { ?image prov:wasGeneratedBy ?run . ?run mv:modelVersion ?model ; mv:promptText ?prompt ; prov:used ?evidence } },
        "generation-evidence-not-recorded", "complete")) AS ?reason)
    FILTER(?reason != "complete")
  }
}
ORDER BY ?case ?project
~~~

## 합성 미디어 아카이브의 운영 질의와 성능 작업 부하

BMV 질문은 `benchmark_workload.py`가 생성하는 정본 MV 스키마의 합성 아카이브에서 실행한다. 8개 프로젝트의 타임라인에는 각 4개 장면이 있고, 등록 이미지 수를 늘려 규모별 성능을 비교한다. 음원·최종 영상·등록 이미지·샷 관계를 별도로 조회하며, 파일이나 생성 이력의 미기록 상태를 실제 부재로 해석하지 않는다.

### BMV-01. 최종 전달 영상의 프로젝트 음원·타임라인 연결이 일치하는가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
SELECT ?project ?video ?audio ?timeline WHERE {
  ?project a mv:MusicVideoProject ; mv:hasFinalVideo ?video ; mv:hasAudio ?audio ; mv:hasTimeline ?timeline .
  ?video mv:usesAudio ?audio ; mv:hasTimeline ?timeline .
}
ORDER BY ?project
~~~

### BMV-02. 프로젝트별 등록 이미지 수는 얼마인가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
SELECT ?project (COUNT(DISTINCT ?image) AS ?imageCount) WHERE {
  ?project a mv:MusicVideoProject ; mv:hasImage ?image . ?image a mv:ImageAsset .
}
GROUP BY ?project
ORDER BY ?project
~~~

### BMV-03. 프로젝트별 실제 배치 장면 수와 배치 시간 합계는 얼마인가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
SELECT ?project (COUNT(?shot) AS ?shotCount) (SUM(?end - ?start) AS ?scheduledSeconds) WHERE {
  ?project a mv:MusicVideoProject ; mv:hasTimeline ?timeline . ?timeline mv:hasShot ?shot .
  ?shot mv:startSecond ?start ; mv:endSecond ?end .
}
GROUP BY ?project
ORDER BY ?project
~~~

### BMV-04. 지정 이미지의 여러 단계 파생 원본은 무엇인가?

~~~sparql
PREFIX ex: <https://example.test/benchmark/>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?ancestor WHERE { ex:image000001 prov:wasDerivedFrom+ ?ancestor }
ORDER BY ?ancestor
~~~

### BMV-05. 프로젝트별 파일 해시가 기록되지 않은 이미지 수는 얼마인가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
SELECT ?project (COUNT(?image) AS ?missingChecksumCount) WHERE {
  ?project a mv:MusicVideoProject ; mv:hasImage ?image .
  FILTER NOT EXISTS { ?image mv:checksum ?checksum }
}
GROUP BY ?project
ORDER BY ?project
~~~

### BMV-06. 프로젝트별 파생 원본 관계가 기록되지 않은 이미지 수는 얼마인가?

~~~sparql
PREFIX mv: <https://example.org/mv#>
PREFIX prov: <http://www.w3.org/ns/prov#>
SELECT ?project (COUNT(?image) AS ?unknownSourceCount) WHERE {
  ?project a mv:MusicVideoProject ; mv:hasImage ?image .
  FILTER NOT EXISTS { ?image prov:wasDerivedFrom ?source }
}
GROUP BY ?project
ORDER BY ?project
~~~

## 실행 및 예상 결과 관리

`tests/test_competency_questions.py`는 기존 SPARQL 25개와 `tests/fixtures/competency_answers.json`의 고정 예상 결과를 비교하고, BUS 6개와 `business_answers.json`, BMV 6개와 작업 부하 설계에서 별도로 계산한 답을 비교한다. 총 37개 질문의 변수·행이 예상과 다르면 실패한다. SYN-09와 SYN-10은 정상 합성 사례에서 빈 결과가 예상되며, 별도 테스트에서 관계를 추가하면 실제 결과가 나타나는지도 확인한다. BUS 사례는 정상·누락·충돌뿐 아니라 한 관계의 제거와 잘못된 대상 연결에도 답이 달라지는지 검사한다. 격리 테스트는 기본 그래프의 union을 비활성화하며, named graph 범위가 접근 제어 자체를 구현한다는 의미는 아니다. 실행 방법과 성능 측정 범위는 `BUSINESS_SCENARIOS.md`에서 설명한다.
