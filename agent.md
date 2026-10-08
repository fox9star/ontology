# AI 에이전트 협업 온톨로지

## 1. 목적과 범위

AI 에이전트 협업 온톨로지는 여러 에이전트가 하나의 목표를 수행할 때 **역할, 작업, 인계 자료, 결과물, 검수와 책임의 관계**를 공통 어휘로 정의한 지식 모델이다. 예를 들어 조사 에이전트가 근거 자료를 모으고, 작성 에이전트가 초안을 만들며, 검수 에이전트가 출처와 품질을 확인하는 과정을 하나의 그래프로 표현한다. 온톨로지는 실행 순서와 기록의 의미를 알려 주고, 실제 도구 호출·대기·재시도·접근 제어는 작업 실행기와 서비스가 수행한다.

첫 버전은 하나의 프로젝트에서 여러 에이전트가 작업을 나누고 결과물을 인계하는 상황으로 제한한다. 에이전트 간 자연어 대화 전체를 그래프에 복사하기보다, 다음 작업에 필요한 **구조화된 인계 정보와 결과물의 위치·버전**을 기록한다.

이 모델이 답해야 할 질문은 다음과 같다.

- 지금 어떤 작업이 준비되었고, 어떤 선행 작업의 완료를 기다리는가?
- 각 작업의 담당자와 실제 수행자는 누구인가?
- 어떤 결과물이 어느 실행에서 만들어졌고, 다음 작업의 입력으로 사용되었는가?
- 인계할 때 어떤 결과물, 제한 조건, 완료 기준을 전달했는가?
- 검수에서 무엇을 승인하거나 반려했고, 어떤 수정 작업이 이어졌는가?
- 최종 결과가 어떤 입력과 에이전트 실행에서 파생되었는가?

## 2. 핵심 개념

| 클래스 | 의미 | 대표 정보 |
|---|---|---|
| `Project` | 공동 목표를 수행하는 단위 | 목표, 요청자, 상태, 최종 전달물 |
| `Agent` | 작업에 참여하는 소프트웨어 또는 사람 | 식별자, 버전, 역할, 사용 가능한 기능 |
| `Role` | 프로젝트 안에서 맡는 책임 | 조사, 작성, 검수, 조정 등 |
| `Capability` | 에이전트가 수행할 수 있는 기능 | 검색, 작성, 코드 실행, 이미지 생성 등 |
| `Task` | 계획된 작업 | 목표, 입력 조건, 완료 기준, 선행 작업 |
| `TaskRun` | 작업의 한 번의 실행 | 수행 에이전트, 시작·종료 시각, 상태, 오류 |
| `Artifact` | 실행이 만들거나 사용한 결과물 | URI, 버전, 유형, 체크섬, 출처 |
| `Handoff` | 한 작업에서 다음 작업으로 넘기는 인계 묶음 | 받는 작업·에이전트, 결과물, 지시, 완료 기준 |
| `ReviewDecision` | 결과물에 대한 검수 결과 | 검수 대상, 판정, 사유, 수정 요구 |

`Task`와 `TaskRun`을 나누면 실패 후 다시 실행해도 계획은 하나이고 실행 기록은 여러 개로 남는다. `Artifact`는 초안, 검색 결과, 코드, 이미지, 보고서처럼 실제로 주고받는 대상을 뜻한다. 같은 이름의 파일을 수정할 때도 새 버전의 `Artifact`를 만들고 앞선 버전에서 파생되었음을 기록한다.

출처 기록에는 [W3C PROV-O](https://www.w3.org/TR/prov-o/)를 재사용할 수 있다. `Agent`는 `prov:Agent`, `TaskRun`은 `prov:Activity`, `Artifact`와 `Handoff`는 `prov:Entity`의 하위 개념으로 둔다. 그러면 실행이 무엇을 사용했는지(`prov:used`), 결과물이 어떤 실행에서 생성되었는지(`prov:wasGeneratedBy`), 실행에 어떤 에이전트가 참여했는지(`prov:wasAssociatedWith`), 결과물이 무엇에서 파생되었는지(`prov:wasDerivedFrom`)를 표준 어휘로 연결할 수 있다. 다른 에이전트를 대신하여 활동했다는 책임 관계를 기록할 때는 `prov:actedOnBehalfOf`를 사용할 수 있다. 단순한 작업 인계만으로 대리 관계를 단정해서는 안 된다.

## 3. 관계와 데이터 속성

| 관계 | 주체 → 대상 | 의미 |
|---|---|---|
| `hasTask` | 프로젝트 → 계획 작업 | 프로젝트를 이루는 작업 |
| `dependsOn` | 계획 작업 → 선행 계획 작업 | 완료를 기다리는 의존성 |
| `assignedTo` | 계획 작업 → 에이전트 | 계획상의 담당자 |
| `implementsTask` | 실행 → 계획 작업 | 어떤 작업을 실행했는지 |
| `hasCapability` | 에이전트 → 기능 | 담당 가능 여부를 판단할 근거 |
| `hasHandoff` | 실행 → 인계 묶음 | 실행이 전달한 구조화된 정보 |
| `toTask`, `toAgent`, `containsArtifact` | 인계 → 받는 작업·에이전트·결과물 | 인계의 대상과 내용 |
| `reviews`, `hasDecision` | 검수 실행 → 결과물·판정 | 검수 대상과 결과 |
| `prov:used` | 실행 → 입력 결과물 | 실제로 사용한 자료 |
| `prov:wasGeneratedBy` | 결과물 → 실행 | 결과물의 생성 출처 |
| `prov:wasAssociatedWith` | 실행 → 에이전트 | 실제 수행 또는 참여 |

문자열·숫자 속성으로 `status`, `version`, `artifactUri`, `checksum`, `acceptanceCriteria`, `decision`, `reason`, `errorCode` 등을 둔다. 시각에는 시간대가 포함된 `xsd:dateTime`을 쓰고, 실행마다 고유 ID를 부여한다. `status`는 예를 들어 `planned → ready → running → completed` 또는 `failed`로 관리한다. 상태 값의 변경 규칙은 실행기에서 적용하고, 그래프에는 관측된 상태와 시각을 기록한다.

계획의 `assignedTo`와 실행의 `prov:wasAssociatedWith`는 다를 수 있다. 담당 에이전트의 장애로 다른 에이전트가 재시도하면 계획상의 배정과 실제 수행 기록을 모두 보존해야 한다. 한 실행에 여러 에이전트가 참여한다면 PROV-O의 `prov:qualifiedAssociation`과 `prov:hadRole`로 각 참여자의 역할을 자세히 기록할 수 있다.

## 4. 협업 흐름

1. **조정 에이전트**가 요청을 `Project`로 만들고 목표를 `Task`들로 분해한다. 작업마다 입력 조건, 담당자, 완료 기준, 선행 작업을 지정한다.
2. **작업 실행기**가 `dependsOn`과 상태를 확인해 준비된 작업을 시작한다. 서로 의존하지 않는 조사와 이미지 제작처럼 독립된 작업은 병렬로 진행할 수 있다.
3. **수행 에이전트**가 `TaskRun`을 만들고 사용한 입력을 `prov:used`, 산출물을 `prov:wasGeneratedBy`로 연결한다. 도구·모델 버전과 오류도 실행 기록에 남긴다.
4. **보내는 에이전트**가 `Handoff`에 채택한 결과물, 받는 작업, 다음 에이전트가 지켜야 할 조건을 담는다. 인계의 완료는 메시지 발송 여부만으로 판단하지 않고, 받는 작업이 해당 버전의 결과물을 실제로 읽을 수 있는지도 확인한다.
5. **받는 에이전트**가 인계의 결과물을 입력으로 사용해 다음 작업을 수행한다. 누락된 근거나 읽을 수 없는 파일이 있으면 인계를 보류하고 보완 작업을 요청한다.
6. **검수 에이전트**가 결과물을 평가해 `ReviewDecision`을 만든다. 승인되면 최종 결과물로 채택하고, 반려되면 이유와 수정 요구를 새 작업 또는 다음 실행에 연결한다.

작업 의존성에 순환이 있으면 시작 가능한 작업이 사라질 수 있으므로 실행기가 이를 검사해야 한다. 병렬 실행이 같은 결과물을 갱신하려고 할 때에는 버전과 채택 정책을 정해 충돌을 처리한다. 실행의 `completed`와 결과물의 `approved`는 다른 의미이므로 별도로 기록한다.

## 5. 간단한 RDF/Turtle 예시

아래는 **자료 조사 → 글 작성 → 검수**로 이어지는 가상 사례다. `https://example.org/agent#`의 이름과 데이터는 설명용이며, 실제 구현에서는 조직이 관리하는 URI를 쓴다. 표준 PROV-O 개념과 이 문서의 도메인 개념을 함께 사용한다.

```turtle
@prefix ag:   <https://example.org/agent#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ag:Agent rdfs:subClassOf prov:Agent .
ag:TaskRun rdfs:subClassOf prov:Activity .
ag:Artifact rdfs:subClassOf prov:Entity .
ag:Handoff rdfs:subClassOf prov:Entity .
ag:ReviewDecision rdfs:subClassOf prov:Entity .

ag:project01 a ag:Project ;
    ag:hasTask ag:researchTask, ag:draftTask, ag:reviewTask .

ag:researchAgent a ag:Agent .
ag:writerAgent   a ag:Agent .
ag:reviewAgent   a ag:Agent .

ag:researchTask a ag:Task ; ag:assignedTo ag:researchAgent .
ag:draftTask    a ag:Task ; ag:assignedTo ag:writerAgent ;
    ag:dependsOn ag:researchTask .
ag:reviewTask   a ag:Task ; ag:assignedTo ag:reviewAgent ;
    ag:dependsOn ag:draftTask .

ag:researchRun01 a ag:TaskRun ;
    ag:implementsTask ag:researchTask ;
    ag:status "completed" ;
    prov:wasAssociatedWith ag:researchAgent ;
    ag:hasHandoff ag:handoff01 .

ag:notesV1 a ag:Artifact ;
    ag:artifactUri <https://example.org/files/notes-v1.md> ;
    ag:version "1" ;
    prov:wasGeneratedBy ag:researchRun01 .

ag:handoff01 a ag:Handoff ;
    ag:toTask ag:draftTask ;
    ag:toAgent ag:writerAgent ;
    ag:containsArtifact ag:notesV1 ;
    ag:acceptanceCriteria "주요 주장마다 출처를 표시한다" ;
    prov:wasGeneratedBy ag:researchRun01 .

ag:draftRun01 a ag:TaskRun ;
    ag:implementsTask ag:draftTask ;
    ag:status "completed" ;
    prov:wasAssociatedWith ag:writerAgent ;
    prov:used ag:handoff01, ag:notesV1 .

ag:articleV1 a ag:Artifact ;
    ag:artifactUri <https://example.org/files/article-v1.md> ;
    ag:version "1" ;
    prov:wasGeneratedBy ag:draftRun01 ;
    prov:wasDerivedFrom ag:notesV1 .

ag:reviewRun01 a ag:TaskRun ;
    ag:implementsTask ag:reviewTask ;
    ag:status "completed" ;
    prov:wasAssociatedWith ag:reviewAgent ;
    prov:used ag:articleV1 ;
    ag:reviews ag:articleV1 ;
    ag:hasDecision ag:decision01 .

ag:decision01 a ag:ReviewDecision ;
    ag:decision "approved" ;
    ag:reason "주장과 출처의 대응을 확인함" ;
    prov:wasGeneratedBy ag:reviewRun01 .
```

이 예시에서 `ag:draftTask ag:dependsOn ag:researchTask`는 **계획상 순서**를 뜻하고, `ag:draftRun01 prov:used ag:notesV1`은 **실제로 사용한 입력**을 뜻한다. 두 관계를 함께 보아야 계획과 실제 실행이 일치했는지 확인할 수 있다.

## 6. 규칙과 검증

[OWL 2](https://www.w3.org/TR/owl2-primer/)로 클래스 계층, 관계의 주체·대상과 개념적 제약을 표현할 수 있다. OWL의 열린 세계 가정에서는 값이 기록되지 않았다는 이유만으로 누락을 오류로 판정하지 않는다. 필수 입력과 데이터 형식은 [SHACL](https://www.w3.org/TR/shacl/)로 검증한다. 다음 모양은 모든 `TaskRun`에 계획 작업, 상태, 수행 에이전트가 있고, 모든 `Handoff`에 받는 작업과 결과물 및 완료 기준이 있는지 확인한다.

```turtle
@prefix ag:   <https://example.org/agent#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

ag:TaskRunShape a sh:NodeShape ;
    sh:targetClass ag:TaskRun ;
    sh:property [ sh:path ag:implementsTask ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:class ag:Task ] ;
    sh:property [ sh:path ag:status ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:datatype xsd:string ] ;
    sh:property [ sh:path prov:wasAssociatedWith ; sh:minCount 1 ;
                  sh:class ag:Agent ] .

ag:HandoffShape a sh:NodeShape ;
    sh:targetClass ag:Handoff ;
    sh:property [ sh:path ag:toTask ; sh:minCount 1 ;
                  sh:maxCount 1 ; sh:class ag:Task ] ;
    sh:property [ sh:path ag:containsArtifact ; sh:minCount 1 ;
                  sh:class ag:Artifact ] ;
    sh:property [ sh:path ag:acceptanceCriteria ; sh:minCount 1 ;
                  sh:datatype xsd:string ] .
```

이 모양은 예시의 일부 필수 필드만 검사한다. 운영 단계에서는 상태 값의 허용 목록, 승인 판정의 필수 사유, 고유 버전, 작업별 입력 조건을 추가한다. **의존성 순환, 읽기 권한, 외부 파일의 존재, 사람의 승인 여부**는 그래프 검증만으로 충분하지 않으므로 실행기·저장소·승인 시스템에서 확인한다. 민감한 입력은 그래프에 본문을 넣지 않고 접근 가능한 참조와 분류 등급을 저장한다.

## 7. 구축 순서

1. 실제 협업 사례 한 개를 정하고 완료 기준과 추적해야 할 질문을 적는다.
2. `Project`, `Task`, `TaskRun`, `Artifact`, `Handoff`, `ReviewDecision`에 안정적인 URI와 최소 속성을 부여한다.
3. PROV-O 어휘와 도메인 관계를 연결하고, 계획·실행·검수를 별도 기록으로 저장한다.
4. SHACL로 필수 필드와 인계 형식을 검사하고, 실행기로 의존성·권한·파일 상태를 확인한다.
5. 실패·재시도·병렬 실행·검수 반려 사례를 입력해 어느 결과물이 최종 채택되었는지 추적한다.
6. 사용자가 “누가 무엇을 만들고 검토했는가?”를 그래프에서 조회할 수 있으면 역할과 작업 유형을 점진적으로 확장한다.

관련 표준: [PROV-O](https://www.w3.org/TR/prov-o/) · [OWL 2 Primer](https://www.w3.org/TR/owl2-primer/) · [SHACL](https://www.w3.org/TR/shacl/)
