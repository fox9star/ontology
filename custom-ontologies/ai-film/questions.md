# AI 영화 제작 업무 질문

화면에서는 `example.ttl`의 합성 제작 계획에 실행한다. 고정 정답 검사는 별도 `question-fixture.ttl`을 사용한다. 두 그래프의 예시 개체 IRI는 저장 공간을 구분하며 업무 구조는 같다. 순서는 장면 및 샷 안에서 해석한다.
계획 자산과 실행 근거를 구분하며, 결과가 없다는 사실은 완료나 승인의 증거가 아니다.

### AIF-01. 어떤 샷을 어떤 순서와 목표 길이로 생성할 계획인가?

~~~sparql
PREFIX film: <https://example.org/ontology/custom/ai-film#>
SELECT ?project ?sceneOrder ?shotOrder ?shot ?seconds ?task ?status ?prompt
WHERE {
  ?project a film:FilmProject ; film:hasScreenplay ?screenplay .
  ?screenplay a film:Screenplay ; film:hasScene ?scene .
  ?scene a film:Scene ; film:sceneOrder ?sceneOrder ; film:hasShot ?shot .
  ?shot a film:Shot ; film:shotOrder ?shotOrder ; film:targetDurationSeconds ?seconds ; film:hasGenerationTask ?task .
  ?task a film:GenerationTask ; film:taskStatus ?status ; film:promptText ?prompt .
  FILTER (?status IN ("planned", "failed"))
}
ORDER BY ?project ?sceneOrder ?shotOrder ?task
~~~

### AIF-02. 모델 식별 정보나 실행 근거가 아직 없는 생성 작업은 무엇인가?

~~~sparql
PREFIX film: <https://example.org/ontology/custom/ai-film#>
SELECT ?task ?status ?modelState ?model ?executionEvidence ?asset
WHERE {
  ?task a film:GenerationTask ; film:taskStatus ?status ; film:modelKnowledgeStatus ?modelState ; film:plannedAsset ?asset .
  OPTIONAL { ?task film:modelIdentifier ?model }
  OPTIONAL { ?task film:generationEvidenceUri ?executionEvidence }
  FILTER (?modelState = "unknown" || !BOUND(?executionEvidence))
}
ORDER BY ?task ?asset
~~~

### AIF-03. 확보 상태와 출처를 함께 볼 때 각 자산의 권리·품질 검토는 어디까지 되었는가?

~~~sparql
PREFIX film: <https://example.org/ontology/custom/ai-film#>
SELECT ?asset ?media ?availability ?file ?source ?kind ?decision ?reason ?reviewEvidence
WHERE {
  ?asset a film:MediaAsset ; film:mediaType ?media ; film:assetStatus ?availability ; film:hasReview ?review .
  ?review a film:ReviewDecision ; film:reviewKind ?kind ; film:decision ?decision ; film:decisionReason ?reason .
  OPTIONAL { ?asset film:assetUri ?file }
  OPTIONAL { ?asset film:sourceEvidenceUri ?source }
  OPTIONAL { ?review film:reviewEvidenceUri ?reviewEvidence }
}
ORDER BY ?asset ?kind
~~~

### AIF-04. 편집 버전의 승인을 막고 있는 자산별 미완료 항목은 무엇인가?

~~~sparql
PREFIX film: <https://example.org/ontology/custom/ai-film#>
SELECT ?edit ?version ?asset ?blocker
WHERE {
  ?project film:hasEditVersion ?edit .
  ?edit a film:EditVersion ; film:versionLabel ?version ; film:usesAsset ?asset .
  {
    FILTER NOT EXISTS { ?asset film:assetStatus "available" ; film:assetUri ?file ; film:sourceEvidenceUri ?source }
    BIND ("asset-or-source-unavailable" AS ?blocker)
  } UNION {
    FILTER NOT EXISTS { ?asset film:hasReview ?rights . ?rights film:reviewKind "rights" ; film:decision "approved" ; film:reviewEvidenceUri ?e }
    BIND ("rights-review-incomplete" AS ?blocker)
  } UNION {
    FILTER NOT EXISTS { ?asset film:hasReview ?quality . ?quality film:reviewKind "quality" ; film:decision "approved" ; film:reviewEvidenceUri ?e }
    BIND ("quality-review-incomplete" AS ?blocker)
  }
}
ORDER BY ?edit ?asset ?blocker
~~~

### AIF-05. 필요한 자산과 두 검토 근거가 모두 준비된 승인 편집본은 무엇인가?

~~~sparql
PREFIX film: <https://example.org/ontology/custom/ai-film#>
SELECT ?project ?edit ?version (COUNT(DISTINCT ?asset) AS ?assetCount)
WHERE {
  ?project a film:FilmProject ; film:hasEditVersion ?edit .
  ?edit a film:EditVersion ; film:versionLabel ?version ; film:editStatus "approved" ; film:usesAsset ?asset .
  FILTER NOT EXISTS {
    ?edit film:usesAsset ?missing .
    FILTER NOT EXISTS {
      ?missing a film:MediaAsset ; film:assetStatus "available" ; film:assetUri ?file ; film:sourceEvidenceUri ?source ; film:hasReview ?rights, ?quality .
      ?rights a film:ReviewDecision ; film:reviewKind "rights" ; film:decision "approved" ; film:reviewEvidenceUri ?re .
      ?quality a film:ReviewDecision ; film:reviewKind "quality" ; film:decision "approved" ; film:reviewEvidenceUri ?qe .
    }
  }
}
GROUP BY ?project ?edit ?version
ORDER BY ?project ?edit
~~~

합성 계획의 고정 정답은 각각 2행, 2행, 4행, 6행, 0행이다. 마지막 질문은 별도 합성
승인 시나리오에서 1행을 확인하고, 권리 검토 근거 하나를 제거하면 0행으로 바뀌는지 검사한다.
