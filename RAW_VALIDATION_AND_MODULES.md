# 명시 데이터 검증과 로컬 모듈 관리

`validation_pipeline.validate_phases(data, schema, shapes)`는 입력 그래프를 바꾸지 않고 두 결과를 반환한다. 웹 검증, 일괄 검증, 개체 편집·스냅샷 복원, Codex 결과 저장, 미디어 가져오기와 제작 파이프라인에 적용한다.

| 단계 | 입력과 처리 | 용도 |
|---|---|---|
| `raw_conforms` | 원자료와 로컬 스키마에 실제 기록된 선언, 추론 없음 | 저장·수용의 필수 조건 |
| `inferred_conforms` | 별도 사본에 RDFS 적용 | 추론으로 드러나는 제약 위반 진단 |
| `conforms` | 두 단계 모두 통과 | 최종 수용 여부 |

SHACL 클래스 제약은 명시된 하위 클래스 계층을 따른다. 예를 들어 `ImageAsset`로 기록한 개체에 `MediaAsset` 타입을 중복 기록할 필요가 없다. 스키마가 직접 선언한 통제 어휘 개체의 타입도 유효한 근거다. 그러나 `hasImage`의 range만으로 이미지 타입을 만들어 원자료 누락을 숨길 수 없다. 로컬의 named class와 그 union domain/range에 대해 주어·목적어에 명시적으로 호환되는 타입이 있는지 확인한다. 모든 OWL class expression을 해석하는 일반 추론기 기능은 제공하지 않는다.

`inferred_type_count`는 인스턴스 관련 노드에 추가된 타입 수이며, 확인된 원본 사실 수가 아니다. 공유 보고서와 의료 API의 요약은 식별자·값·원문 검증 메시지를 포함하지 않는다.

```powershell
.\.venv\Scripts\python.exe verify_all.py
.\.venv\Scripts\python.exe validation_pipeline.py --data projects/late-night-mood/data.ttl --schema mv-schema.ttl --shapes mv-shapes.ttl --json reports/raw-validation-project.json
```

`ontology_modules.json`이 정본 모듈, 공유 shapes, 보조 질문·예제를 등록한다. `ontology_loader.load_schema_bundle()`은 ontology IRI와 version IRI를 로컬 파일에 매핑하여 전이 import를 따라 읽는다. 알 수 없는 import, IRI 충돌, 순환, 누락 파일과 경로 이탈은 실패한다. 명시적으로 허용한 외부 PROV-O import는 참조로만 기록하며 네트워크에서 내려받지 않는다.

각 파일은 한 번 캡처한 바이트를 파싱하고 같은 바이트의 SHA-256을 보고한다. RDF/XML 등 별도 표현을 요청하면 등록된 Turtle과 그래프가 같은지 확인한다. 이 기록은 한 번의 로딩에서 읽은 바이트의 근거이며, 여러 파일의 동시 변경에 대한 파일시스템 트랜잭션을 보장하지 않는다.

검증 기준을 강화했으므로, 타입을 기록하지 않고 range 추론에 의존하던 외부 데이터는 거절될 수 있다. 이는 개발 중 수용 정책의 변경이다. 배포 시 소비자 호환성 검토와 버전 결정이 필요하며, 현재 공개 릴리스 URI는 미정이다.
