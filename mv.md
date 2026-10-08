# AI 에이전트가 음원·이미지·뮤직비디오를 만드는 온톨로지 구축 방법

## 1. 목표와 범위

이 온톨로지는 하나의 제작 요청에서 **음원 생성 → 이미지 생성 → 음원과 이미지를 타임라인에 배치 → 뮤직비디오 렌더링**까지 이어지는 대상, 작업, 결과물, 의존 관계를 정의한다. 온톨로지는 미디어를 직접 생성하는 프로그램이 아니다. 에이전트와 작업 실행기가 이 지식 구조를 읽고 필요한 생성 도구를 호출하며, 각 실행 결과를 다시 기록하도록 만드는 공통 데이터 모델이다.

첫 버전의 범위는 *한 곡의 음원과 여러 장의 정지 이미지를 사용해 한 편의 뮤직비디오를 만드는 과정*으로 잡는다. 가사 영상, 생성형 영상 클립, 다국어 버전은 이후 확장할 수 있다. 이미지와 음원만 있다고 영상이 완성되는 것은 아니다. 각 이미지의 표시 시간, 순서, 화면 비율, 전환 방식, 최종 인코딩 조건을 담은 타임라인이 필요하다.

온톨로지가 답해야 할 질문은 다음과 같다.

- 현재 제작 요청에서 어떤 음원과 이미지가 확정되었는가?
- 각 결과물을 어느 에이전트, 생성 작업, 모델 버전, 프롬프트가 만들었는가?
- 음원의 어느 시간 구간에 어떤 이미지가 표시되는가?
- 렌더링을 시작하는 데 필요한 입력과 검증 조건이 충족되었는가?
- 최종 영상이 어떤 음원·이미지·타임라인에서 만들어졌는가?

## 2. 핵심 개념(클래스)

| 클래스 | 의미 | 주요 정보 |
|---|---|---|
| `CreativeBrief` | 제작 요청과 스타일 기준 | 주제, 분위기, 목표 길이, 화면 비율, 전달물 형식 |
| `MusicVideoProject` | 하나의 제작 단위 | 요청, 채택한 음원·이미지, 타임라인, 최종 영상 |
| `MediaAsset` | 파일로 저장된 미디어 결과물의 상위 개념 | 파일 URI, MIME 유형, 체크섬, 생성 시각 |
| `AudioAsset` | 생성되거나 채택된 음원 | 길이(초), 샘플레이트, 선택적 BPM·구간 정보 |
| `ImageAsset` | 장면에 사용할 이미지 | 폭·높이, 장면 설명, 파일 URI |
| `MusicVideo` | 렌더링된 최종 영상 | 길이, 해상도, 프레임레이트, 파일 URI |
| `Timeline` | 영상의 시간 배치 계획 | 장면 목록, 목표 길이 |
| `Shot` | 한 이미지가 표시되는 구간 | 시작·끝 시간, 순서, 사용 이미지, 화면 움직임·전환 |
| `GenerationTask` | 결과물 생성의 실행 기록 | 입력, 출력, 상태, 프롬프트, 도구·모델 버전 |
| `AudioGenerationTask`, `ImageGenerationTask`, `RenderTask`, `QualityCheckTask` | 작업 종류 | 각 작업의 입력·출력과 담당 에이전트 |
| `AIAgent` | 작업을 수행하거나 조정하는 소프트웨어 에이전트 | 역할, 사용 가능한 도구, 버전 |

`AudioAsset`, `ImageAsset`, `MusicVideo`는 출처를 추적할 수 있는 `prov:Entity`로, 실행 작업은 `prov:Activity`로, 에이전트는 `prov:Agent`로 연결한다. 그러면 **작업이 무엇을 사용했는지**(`prov:used`), **무엇을 만들었는지**(`prov:wasGeneratedBy`), **최종 결과가 어떤 자산에서 파생되었는지**(`prov:wasDerivedFrom`)를 공통 어휘로 표현할 수 있다. [W3C PROV-O](https://www.w3.org/TR/prov-o/)

## 3. 핵심 관계와 데이터 속성

| 관계 | 주체 → 대상 | 쓰임 |
|---|---|---|
| `hasBrief` | 프로젝트 → 제작 요청 | 모든 작업이 같은 목표를 참조 |
| `hasAudio`, `hasImage` | 프로젝트 → 음원·이미지 | 채택한 결과물 연결 |
| `hasTimeline`, `hasShot` | 프로젝트 → 타임라인 → 장면 | 최종 영상의 시간 구성 |
| `usesImage` | 장면 → 이미지 | 해당 구간의 화면 자산 |
| `usesAudio`, `hasTimeline` | 뮤직비디오 → 음원·타임라인 | 최종 영상의 필수 구성 |
| `dependsOn` | 작업 → 선행 작업 | 에이전트 실행 순서 |
| `prov:used`, `prov:wasGeneratedBy`, `prov:wasAssociatedWith` | 작업·자산·에이전트 사이 | 실행과 출처 추적 |

시간은 `startSecond`, `endSecond`, `durationSeconds`처럼 **초 단위의 숫자**로 통일한다. 파일에는 안정적인 URI를 부여하고, 실제 바이너리 파일은 별도 저장소에 둔다. 그래프에는 `fileUri`, `mimeType`, `checksum`, `width`, `height`, `sampleRate`, `frameRate`, `status`, `modelVersion`, `promptText` 같은 메타데이터를 기록한다. 실패 후 재시도할 때 기존 결과물을 덮어쓰지 말고 새 `GenerationTask` 실행과 새 자산으로 남기면 어느 버전이 최종 영상에 쓰였는지 추적할 수 있다.

## 4. 작업 흐름을 온톨로지로 연결하기

1. **요청 해석 에이전트**가 `CreativeBrief`를 만들고 목표 길이, 분위기, 시각 스타일, 화면 비율을 확정한다.
2. **음원 에이전트**가 `AudioGenerationTask`를 실행한다. 결과 `AudioAsset`의 길이·형식·파일 위치를 기록하고, 필요하면 구간이나 박자 정보를 추출한다.
3. **이미지 에이전트**가 요청과 음악 구간에 맞는 `ImageGenerationTask`들을 실행한다. 생성된 각 `ImageAsset`을 장면 설명과 함께 등록한다.
4. **편집 에이전트**가 `Timeline`과 `Shot`들을 만든다. 각 장면에 `usesImage`, `startSecond`, `endSecond`, `orderIndex`를 지정하고, 필요하면 정지 이미지에 팬·줌·전환 효과를 적용한다.
5. **렌더 에이전트**는 채택한 음원과 이미지, 검증된 타임라인을 입력으로 `RenderTask`를 실행해 `MusicVideo`를 만든다. 영상에는 사용한 자산과 작업의 출처를 연결한다.
6. **검수 에이전트**가 파일 재생 가능 여부, 오디오 포함 여부, 길이, 해상도, 장면 구간의 빈틈을 확인한다. 통과하면 프로젝트의 최종 결과물로 채택한다.

작업 실행기는 `dependsOn` 관계와 각 작업의 `status`를 읽어 준비된 작업만 시작한다. 예를 들어 이미지 생성은 음원 생성과 동시에 일부 진행할 수 있지만, 최종 장면의 시간 배치와 렌더링에는 **확정된 음원 길이와 채택된 이미지**가 필요하다. 온톨로지의 관계는 의존성을 설명하고, 실제 대기·재시도·도구 호출은 작업 실행기가 담당한다.

## 5. 제약과 검증의 구분

OWL로 `MusicVideo`에는 음원과 타임라인이 있어야 한다는 개념적 조건, `Shot`은 이미지를 사용한다는 관계의 주체·대상 범위 등을 표현한다. 그러나 OWL은 누락된 파일 경로나 코드 값을 일반적인 데이터 검증처럼 강제하지 않는다. 값이 기록되지 않았어도 알려지지 않은 값이 존재할 수 있기 때문이다. **필수 필드의 누락과 값의 형식**은 SHACL로 검사하고, **시간 계산과 실제 미디어 검사**는 검수 프로그램으로 처리한다. [W3C OWL 2 입문서](https://www.w3.org/TR/owl2-primer/), [W3C SHACL](https://www.w3.org/TR/shacl/)

첫 버전의 검증 조건은 다음과 같이 정한다.

- `AudioAsset`: 파일 URI가 있고 길이가 0초보다 커야 한다.
- `ImageAsset`: 파일 URI가 있고 폭과 높이가 0보다 커야 한다.
- `Shot`: 사용 이미지, 순서, 시작·끝 시간이 있어야 하며 `시작 < 끝`이어야 한다.
- `Timeline`: 장면이 1개 이상 있고, 장면들이 목표 구간을 빈틈 없이 덮어야 한다. 겹침 허용 여부는 전환 효과 정책에 따라 정한다.
- `MusicVideo`: 음원·타임라인·파일 URI가 있고, 실제 렌더 파일의 길이가 음원 길이와 허용 오차 안에서 일치하며 재생 가능해야 한다.

SHACL의 `sh:minCount`, `sh:datatype`, `sh:class`로 기본 필드를 검사할 수 있다. 장면 간 겹침이나 음원 길이와 영상 길이의 비교는 SHACL-SPARQL 또는 작업 실행기의 별도 검사 로직으로 구현한다. 검증 실패는 `QualityCheckTask`의 결과로 남기고, 수정이 필요한 선행 작업을 다시 생성한다.

예를 들어 다음 OWL 정의는 최종 영상에 음원과 타임라인이 연결되어야 한다는 **의미상의 조건**을 표현한다. 이어지는 SHACL 정의는 장면 데이터에 이미지와 시작·끝 시간이 실제로 기재되어 있는지 검사한다.

```turtle
@prefix mv:   <https://example.org/mv#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix sh:   <http://www.w3.org/ns/shacl#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

mv:MusicVideo a owl:Class ;
    rdfs:subClassOf
        [ a owl:Restriction ; owl:onProperty mv:usesAudio ; owl:someValuesFrom mv:AudioAsset ],
        [ a owl:Restriction ; owl:onProperty mv:hasTimeline ; owl:someValuesFrom mv:Timeline ] .
mv:usesAudio a owl:ObjectProperty ;
    rdfs:domain mv:MusicVideo ; rdfs:range mv:AudioAsset .
mv:hasTimeline a owl:ObjectProperty ;
    rdfs:domain mv:MusicVideo ; rdfs:range mv:Timeline .

mv:ShotShape a sh:NodeShape ;
    sh:targetClass mv:Shot ;
    sh:property
        [ sh:path mv:usesImage ; sh:minCount 1 ; sh:class mv:ImageAsset ],
        [ sh:path mv:startSecond ; sh:minCount 1 ; sh:datatype xsd:decimal ],
        [ sh:path mv:endSecond ; sh:minCount 1 ; sh:datatype xsd:decimal ] .
```

## 6. 작은 RDF/Turtle 예시

다음은 **가상의 60초 프로젝트**를 데이터 그래프로 표현한 예시다. 실제 파일이나 생성된 작품을 뜻하지 않는다. 이 예시는 두 이미지가 각각 0–30초와 30–60초에 나타나며, 최종 영상이 음원과 이미지에서 파생되었음을 보여준다.

```turtle
@prefix mv:   <https://example.org/mv#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

mv:project01 a mv:MusicVideoProject ;
    mv:hasBrief mv:brief01 ;
    mv:hasAudio mv:audio01 ;
    mv:hasImage mv:image01, mv:image02 ;
    mv:hasTimeline mv:timeline01 ;
    mv:hasFinalVideo mv:video01 .

mv:brief01 a mv:CreativeBrief ;
    mv:targetDurationSeconds "60"^^xsd:decimal .

mv:audioTask01 a mv:AudioGenerationTask, prov:Activity ;
    prov:used mv:brief01 ;
    prov:wasAssociatedWith mv:musicAgent01 .
mv:audio01 a mv:AudioAsset, prov:Entity ;
    mv:durationSeconds "60"^^xsd:decimal ;
    mv:fileUri <https://example.org/assets/song.wav> ;
    prov:wasGeneratedBy mv:audioTask01 .

mv:imageTask01 a mv:ImageGenerationTask, prov:Activity ;
    prov:used mv:brief01 ;
    prov:wasAssociatedWith mv:imageAgent01 .
mv:image01 a mv:ImageAsset, prov:Entity ;
    mv:fileUri <https://example.org/assets/image01.png> ;
    mv:width 1920 ; mv:height 1080 ;
    prov:wasGeneratedBy mv:imageTask01 .
mv:image02 a mv:ImageAsset, prov:Entity ;
    mv:fileUri <https://example.org/assets/image02.png> ;
    mv:width 1920 ; mv:height 1080 ;
    prov:wasGeneratedBy mv:imageTask01 .

mv:timeline01 a mv:Timeline ;
    mv:hasShot mv:shot01, mv:shot02 .
mv:shot01 a mv:Shot ;
    mv:orderIndex 1 ;
    mv:startSecond "0"^^xsd:decimal ;
    mv:endSecond "30"^^xsd:decimal ;
    mv:usesImage mv:image01 .
mv:shot02 a mv:Shot ;
    mv:orderIndex 2 ;
    mv:startSecond "30"^^xsd:decimal ;
    mv:endSecond "60"^^xsd:decimal ;
    mv:usesImage mv:image02 .

mv:renderTask01 a mv:RenderTask, prov:Activity ;
    mv:dependsOn mv:audioTask01, mv:imageTask01 ;
    prov:used mv:audio01, mv:image01, mv:image02, mv:timeline01 ;
    prov:wasAssociatedWith mv:editorAgent01 .
mv:video01 a mv:MusicVideo, prov:Entity ;
    mv:usesAudio mv:audio01 ;
    mv:hasTimeline mv:timeline01 ;
    mv:durationSeconds "60"^^xsd:decimal ;
    mv:fileUri <https://example.org/assets/video.mp4> ;
    prov:wasGeneratedBy mv:renderTask01 ;
    prov:wasDerivedFrom mv:audio01, mv:image01, mv:image02 .

mv:musicAgent01 a mv:AIAgent, prov:Agent .
mv:imageAgent01 a mv:AIAgent, prov:Agent .
mv:editorAgent01 a mv:AIAgent, prov:Agent .
```

## 7. 실제 구축 순서

1. 위의 핵심 질문과 전달물 형식을 기준으로 첫 제작 사례 3~5개를 수집한다.
2. 클래스·관계·속성의 이름과 의미를 정의하고, RDF/Turtle 또는 OWL 파일로 스키마를 만든다. 화면에 보이는 한국어 이름은 `rdfs:label`로 붙인다.
3. 필수 메타데이터용 SHACL 형태(shape)를 만들고, 정상·누락·시간 충돌 사례로 검증한다.
4. 음원·이미지 생성 도구의 응답을 `AudioAsset`·`ImageAsset`로 변환하는 어댑터를 만든다. 작업 실행기는 그래프에서 의존성을 읽고 각 도구를 호출한다.
5. 실제 파일의 길이·해상도·재생 가능 여부를 검사해 그래프의 메타데이터와 비교한다.
6. 최종 영상에서 사용한 모든 자산과 작업을 거슬러 올라갈 수 있는지 질의로 확인하고, 부족한 개념만 확장한다.

처음부터 모든 영상 효과와 모델별 옵션을 클래스화하면 유지가 어렵다. 첫 버전은 **제작 요청, 작업, 자산, 타임라인, 출처, 검증 결과**를 안정적으로 연결하는 데 집중한다. RDF는 연결된 사실을 기록하고, OWL은 개념·관계의 의미를 정의하며, SHACL은 입력 데이터의 필수 조건을 검증한다. [W3C RDF 1.1 입문서](https://www.w3.org/TR/rdf11-primer/), [W3C OWL 2 개요](https://www.w3.org/TR/owl-overview/), [W3C SHACL](https://www.w3.org/TR/shacl/)
