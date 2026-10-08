# 사용자 온톨로지 추가

화면의 온톨로지 검색 영역에서 **새 온톨로지**를 선택하고 ID, 이름, 설명을 입력합니다. ID는 영문 소문자로 시작하는 2~48자의 소문자·숫자·하이픈입니다. 이름과 설명은 한글을 사용할 수 있습니다. 같은 ID는 다시 만들 수 없습니다.

추가된 항목은 검색 목록에서 선택할 수 있으며 서버를 다시 실행해도 유지됩니다. 기본 생성기는 `Record` 클래스와 `displayName` 속성, 그에 대한 필수 값 검증, 합성 예시 기록, 실행 가능한 SPARQL 질문을 생성합니다. 이는 **도메인 모델을 작성할 초안**입니다. 영화 제작·교육·재고 관리처럼 주제가 정해지면 그 주제의 개념, 관계, 제약과 업무 질문을 추가해야 합니다.

## 저장 구조

각 온톨로지는 `custom-ontologies/<id>/` 안에 별도로 저장됩니다.

| 파일 | 역할 |
| --- | --- |
| `profile.json` | 화면 이름, 설명, 버전, 초안 상태와 소유 파일 경로 |
| `schema.ttl` | 정식 편집 대상 RDF 스키마 |
| `schema.owl` | 동일한 스키마의 RDF/XML 표현 |
| `shapes.ttl` | SHACL 검증 규칙 |
| `example.ttl` | 해당 온톨로지의 합성 예시 데이터 |
| `questions.md` | 실행 가능한 업무 질문과 기대 결과 |

생성 버전은 `0.1.0`, 초안 상태는 `draft: true`입니다. 개발 URI는 `https://example.org/ontology/custom/<id>#`를 사용합니다. 공개 URI가 정해지기 전까지 릴리스하지 않습니다. 영문 이름과 설명은 선택 사항이며, 입력하지 않으면 모델을 완성했다고 주장하지 않는 일반적인 영문 초안 설명을 사용합니다.

## 개발자 연결

`ontology_catalog.create_ontology(payload, builtin_configs, root)`는 `{id, config, module, draft, message}`를 반환합니다. 필수 입력은 `id`, `name`, `description`이며 선택 입력은 `name_en`, `description_en`입니다. 잘못된 입력은 `ValueError`, 중복 ID는 `FileExistsError`, 잠금 대기 초과는 `TimeoutError`입니다.

`load_custom_profiles(root)`는 앱 설정에 합칠 `{id: config}`를 반환합니다. `custom_modules(root)`는 모듈 레지스트리에 합칠 스키마·검증·예시·질문 경로를 반환합니다. `public_catalog(builtin_configs, root)`는 검색용 메타데이터 배열을 반환합니다. 파일 경로는 프로필 디렉터리 내부의 정해진 파일명과 정확히 일치해야 합니다. 링크, 정션, 경로 이탈, 누락 파일과 잘못된 메타데이터는 거부됩니다.

생성은 동일 파일 잠금 안에서 임시 디렉터리에 모든 파일을 쓴 뒤 디렉터리를 한 번에 이동하여 완료합니다. 같은 ID로 동시에 생성해도 한 요청만 성공하며, 기존 디렉터리와 파일은 덮어쓰지 않습니다. 생성 중 서버가 강제 종료되어 남은 `.creating-*` 디렉터리는 프로필로 읽지 않습니다. 이를 정리할 때에는 실행 중인 생성 작업이 없음을 먼저 확인합니다.

`schema.ttl`을 편집했다면 `schema.owl`도 같은 그래프로 다시 생성해야 합니다. Turtle 문법과 SHACL, 기대 SPARQL 결과를 검사하고 도메인 모델의 검토가 끝난 뒤 초안 상태를 바꿉니다. 검증은 각 파일의 품질을 확인하며 실제 도메인 전문가의 판단을 대신하지 않습니다.
