# 뮤직비디오 AI 에이전트 온톨로지 구축 계획

현재 작업 폴더에는 온톨로지 개념 설명(`itis.md`), 에이전트 협업 온톨로지 수강/일반 모델(`agent-schema.ttl`, `agent.owl`), 그리고 **음원·이미지·뮤직비디오 생성 에이전트 온톨로지 명세서(`mv.md`)**가 포함되어 있습니다.

`mv.md`에는 클래스, 속성, 협업 흐름 및 검증 규칙이 상세히 기재되어 있으나, 이를 실행/검증 가능한 실제 온톨로지 데이터 파일(`mv-schema.ttl`, `mv.owl`, `mv-shapes.ttl`, `mv-example.ttl`)이 구현되지 않은 상태입니다.

따라서 `mv.md` 명세와 기존 `agent` 온톨로지 구축 방식을 참고하여 실행 가능한 **뮤직비디오 AI 에이전트 온톨로지 모듈**을 구축하고자 합니다.

---

## User Review Required

> [!NOTE]
> `mv.md` 명세를 기반으로 온톨로지 스키마(`mv-schema.ttl`), RDF/XML 형태(`mv.owl`), SHACL 검증 규칙(`mv-shapes.ttl`), 가상 프로젝트 실행 데이터(`mv-example.ttl`)를 구축하고 PySHACL 검증까지 완료하는 방안입니다.
> 
> 혹시 `mv.md` 기반 구축 외에 다른 커스텀 온톨로지(예: 특정 업무 도메인 온톨로지 추가)를 원하시거나 추가하고 싶으신 요구사항이 있으시면 제안해 주시기 바랍니다.

---

## Open Questions

1. **온톨로지 대상 범위 확인**:
   * 현재 작업 폴더에 구현 명세로 기재된 `mv.md`(뮤직비디오 생성 에이전트 온톨로지) 파일 세트 구축을 진행하는 것이 맞는지, 아니면 별도의 새로운 도메인 온톨로지를 구축하고자 하시는지 확인 부탁드립니다.

---

## Proposed Changes

### 온톨로지 구축 (`c:/Users/wood/Desktop/aiwork/ontology`)

#### [NEW] [mv-schema.ttl](file:///c:/Users/wood/Desktop/aiwork/ontology/mv-schema.ttl)
* **목적**: OWL 2 어휘 기반의 뮤직비디오 생성 에이전트 온톨로지 스키마 정의 (Turtle 포맷)
* **주요 요소**:
  * 클래스: `mv:MusicVideoProject`, `mv:CreativeBrief`, `mv:MediaAsset`, `mv:AudioAsset`, `mv:ImageAsset`, `mv:MusicVideo`, `mv:Timeline`, `mv:Shot`, `mv:GenerationTask`, `mv:AudioGenerationTask`, `mv:ImageGenerationTask`, `mv:RenderTask`, `mv:QualityCheckTask`, `mv:AIAgent` 등
  * PROV-O 매핑 (`prov:Entity`, `prov:Activity`, `prov:Agent` 하위 클래스 지정)
  * 객체 및 데이터 속성: `mv:hasBrief`, `mv:hasAudio`, `mv:hasImage`, `mv:hasTimeline`, `mv:hasShot`, `mv:usesImage`, `mv:usesAudio`, `mv:startSecond`, `mv:endSecond`, `mv:durationSeconds`, `mv:fileUri`, `mv:width`, `mv:height` 등

#### [NEW] [mv.owl](file:///c:/Users/wood/Desktop/aiwork/ontology/mv.owl)
* **목적**: Protégé 등 온톨로지 도구 및 PySHACL 연동을 위한 RDF/XML 변환 직렬화 온톨로지 파일

#### [NEW] [mv-shapes.ttl](file:///c:/Users/wood/Desktop/aiwork/ontology/mv-shapes.ttl)
* **목적**: SHACL 기반 필수 정보 및 데이터 타입 검증 스키마
* **검증 규칙**:
  * `AudioAsset`: `fileUri` 필수, `durationSeconds` > 0
  * `ImageAsset`: `fileUri` 필수, `width`, `height` 지정
  * `Shot`: `usesImage` 1개 이상, `startSecond`, `endSecond`, `orderIndex` 필수
  * `Timeline`: `hasShot` 1개 이상
  * `MusicVideo`: `usesAudio`, `hasTimeline`, `fileUri` 필수

#### [NEW] [mv-example.ttl](file:///c:/Users/wood/Desktop/aiwork/ontology/mv-example.ttl)
* **목적**: 60초 분량 가상 뮤직비디오 생성 프로젝트의 실제 데이터 그래프
* **내용**: 요청 생성 → 음원 생성 (`mv:audio01`) → 이미지 생성 (`mv:image01`, `mv:image02`) → 타임라인 샷 배치 (`mv:shot01`: 0~30s, `mv:shot02`: 30~60s) → 최종 비디오 렌더링 (`mv:video01`)

---

## Verification Plan

### Automated Tests
1. **PySHACL 검증**:
   * 실행 명령어: `pyshacl -s mv-shapes.ttl -e mv.owl -i rdfs mv-example.ttl`
   * 기대 결과: `Validation Report / Conforms: True` 출력 및 종료 코드 0 확인

2. **RDFLib 문법 검증**:
   * Python 스크립트로 생성된 모든 Turtle 및 RDF/XML 파일의 구문 파싱 정상 동작 검증

### Manual Verification
* PySHACL 검증에서 일부 필수 데이터(예: `fileUri` 또는 `usesImage`)를 의도적으로 누락시켰을 때 `Conforms: False` 오류 보고서가 올바르게 감지되는지 테스트

