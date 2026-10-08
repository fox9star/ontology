# 온톨로지 웹 스튜디오

RDF/OWL 데이터와 작업 출처를 조회·편집·검증하는 **단일 사용자 로컬 웹 앱**입니다. 뮤직비디오, 가사·자막·번역, DevOps, 에이전트 협업, 전자상거래, 헬스케어, 대학 수강, 주식투자, 식이·운동, 캠핑, 한국전쟁, 정치·선거 정보, 놀이공원 운영의 13개 온톨로지 프로파일을 제공합니다. e2e는 별도 namespace를 만들지 않고 뮤직비디오 어휘를 확장해 사용합니다. 실제 **Late Night Mood** 프로젝트에는 음원 1개와 이미지 2개를 등록했습니다.

텍스트 생성은 **ChatGPT로 로그인한 Codex CLI** 또는 현재 Codex 채팅에서 수행합니다. 모델 API 키를 요구하지 않습니다. 요청과 실제 결과를 파일에 보관하고, 검증을 통과한 결과의 PROV-O 출처만 선택한 데이터 그래프에 저장합니다. 음악·이미지·영상 생성과 최종 렌더링은 별도 미디어 실행기를 연결해야 합니다.

## 시작하기

Python 3.10 이상과 PowerShell이 필요합니다. 이 폴더에서 다음 명령을 실행합니다. 기존 확인 환경은 Python 3.13입니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

[http://127.0.0.1:5000](http://127.0.0.1:5000)을 엽니다. `run.ps1`은 현재 창에서 실행하며 `Ctrl+C`로 중지합니다. 설치는 처음 또는 의존성 파일 변경 시 수행하고, 패키지는 프로젝트의 `.venv`에 설치합니다.

`setup.ps1`은 `requirements.txt`의 필요한 패키지를 `requirements.lock.txt`의 검증된 버전 constraints와 함께 설치합니다. 직접 설치할 때도 같은 조합을 사용합니다.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -c requirements.lock.txt
```

`requirements.txt`는 필요한 패키지 범위를, `requirements.lock.txt`는 확인한 직접·간접 의존성 버전을 기록합니다. 버전을 변경할 때는 검증 뒤 두 파일을 함께 검토합니다. 문서 HTML 재생성에 필요한 Markdown은 `pip install markdown -c requirements.lock.txt`로 설치합니다.

백그라운드 실행과 중지는 다음 명령을 사용합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\start_all.ps1 -NoBrowser
powershell -ExecutionPolicy Bypass -File .\stop_all.ps1
```

`start_all.ps1`은 기본적으로 이 폴더의 웹 스튜디오만 실행합니다. `.runtime/`에 프로세스 소유 정보와 로그를 저장하고 `/api/health`를 확인합니다. `stop_all.ps1`은 실행 파일·스크립트 경로·프로세스 생성 시각이 일치하는 프로세스의 종료를 확인합니다. `run.ps1`으로 별도 실행한 서버는 `stop.ps1`으로도 중지할 수 있습니다. 실행 중 Codex worker는 별도 프로세스이며 작업 상태는 작업 목록에서 확인합니다.

접속은 로컬 주소와 로컬 요청으로 제한합니다. 웹 화면의 사용자는 이 컴퓨터의 소유자이고 역할 전환용 API 키는 사용하지 않습니다. 공유 서버 운영에는 별도의 사용자 인증·권한 설계가 필요합니다.

## 첫 실습과 실제 등록 미디어

1. [Late Night Mood 프로젝트](http://127.0.0.1:5000/?ont=mv&project=late-night-mood)를 엽니다.
2. **프로젝트 파일**에서 음원을 재생하고 이미지와 장면 배치 계획을 확인합니다.
3. **PySHACL 검증**으로 규칙과 등록 파일의 존재·SHA-256·메타데이터 일치를 검사합니다.
4. **SPARQL 대화형 쿼리**로 파일, 등록 출처, 장면 순서를 조회합니다.
5. **Codex 작업**에서 텍스트 요청을 제출하고 상태와 실제 결과를 확인합니다.
6. 편집 전 **버전 관리 & 롤백**에서 현재 선택한 데이터의 스냅샷을 만듭니다.

등록 파일은 기존 `make/searchmusic/music/Late Night Mood`에서 복사했습니다. 음원은 **163.509333초, 48 kHz stereo PCM WAV**, 두 이미지는 **1376×768 JPEG**입니다. 원본을 수정하지 않았고 등록 당시 사본의 SHA-256이 원본과 같았습니다. 원래 생성 모델과 프롬프트는 **미확인**으로 기록했습니다. 현재 파일 상태는 웹 검증으로 다시 확인할 수 있습니다.

두 장면은 음원 전체 구간을 나눈 배치 계획입니다. 최종 영상 렌더링은 수행하지 않았습니다. `prov:wasGeneratedBy`는 프로젝트에 사본을 생성·등록한 작업을 가리키고 원본 파일은 `prov:wasDerivedFrom`으로 연결됩니다.

All thirteen profiles have SHACL constraints. The camping profile models trips, campgrounds and sites, reservations, participants, equipment checklists, and activities. The politics profile models elections, districts, parties, candidates, aggregate results, campaigns, and source-attributed policy positions; its example data is fictional. The theme-park profile models zones, attractions, wait-time observations, safety inspections, and crowd-management recommendations. Shared Agent and Task terms are in `core-schema.ttl`; domain terms retain their current namespaces. Validation uses canonical Turtle and a locally bundled core; RDF/XML remains a compatibility export. Bootstrap and icons are local in `static/vendor`. Current versions are core 1.1.1, MV/agent/DevOps/e-commerce/academic 1.2.1, stock/diet/camping/politics/theme-park 1.0.0, Korean War 1.0.0, and healthcare 1.3.1. Status codes are checked against SKOS vocabularies and SHACL lists, and healthcare API responses redact unverified, pseudonymized, and sensitive records by default. See [ontology governance](ONTOLOGY_GOVERNANCE.md) and the [FHIR crosswalk](healthcare-fhir-crosswalk.md).

## 사용자 추가 프로필

- [공작류 (Peacock / Peafowl) 온톨로지](PEAFOWL_ONTOLOGY.md)는 peafowl 프로필을 설명한다. 12개 클래스와 59개 속성으로 종·성별 명칭·형태·행동·서식·먹이·번식·근거를 연결하며, 산란·포란 수치는 출처별로 보존한다. [등록·검증 보고서](reports/peafowl-ontology.md).
- [전기자동차 온톨로지](ELECTRIC_VEHICLE_ONTOLOGY.md)는 BEV·PHEV·HEV, 구동계 구성품, AC/DC 에너지 흐름, 충전소·포트·커넥터와 출처 근거를 연결한다. 24개 클래스·46개 속성·12개 역량 질문으로 구성하며 충전 인프라 샘플은 합성 데이터다. [등록·검증 보고서](reports/electric-vehicle-ontology.md).

## Codex가 텍스트 작업을 수행하는 방식

이미 저장된 ChatGPT 로그인을 사용합니다. 다음 명령으로 가용성을 확인합니다.

```powershell
codex login status
.\.venv\Scripts\python.exe codex_jobs.py status
```

ChatGPT 로그인이 필요하면 `codex login`에서 로그인합니다. 웹의 **Codex 작업**에 요청을 입력하면 작업 ID가 생성되고 `.codex-jobs/codex_<id>/`에 요청과 상태가 보관됩니다. CLI가 준비돼 있으면 worker를 실행하고, 준비되지 않았으면 `awaiting_codex`로 보관합니다. HTTP `202`는 작업 접수이며 생성 완료는 작업 상태와 결과 파일로 확인합니다.

```powershell
.\.venv\Scripts\python.exe codex_jobs.py list
.\.venv\Scripts\python.exe codex_jobs.py run-next
.\.venv\Scripts\python.exe codex_jobs.py show codex_<실제작업ID>
```

`run-next`는 대기 작업 한 건을 실행합니다. CLI 작업은 요청한 텍스트를 생성하고 `content`·`summary` JSON으로 반환합니다. 요청에는 생성에 필요한 사실과 조건을 함께 입력합니다. 현재 worker는 선택 프로젝트의 RDF·manifest를 자동으로 첨부하지 않습니다. 모델 이름은 Codex의 설정에 따라 선택되며 실제 사용 모델을 확인하지 못한 경우 출처에 미확인으로 기록합니다. 요청 보관, 텍스트 생성 완료, RDF 저장 성공을 각각 확인할 수 있습니다.

수동으로 현재 Codex 채팅에서 처리할 때는 `enqueue --no-auto-run`으로 요청을 보관하고 `claim`으로 실행권을 확보한 뒤, 실제 결과 파일을 `complete`로 기록합니다. 모든 CLI 명령, 요청·결과 예제, 상태 설명은 [사용 매뉴얼](manual.md)에 있습니다.

## 편집과 복원

**인스턴스 지식 그래프**에서는 실제 개체 중심 검색·유형/관계 필터, 주변 관계, 방향별 최단 경로, 들어오는·나가는 관계 상세와 검증된 관계 편집을 제공합니다. 관계 변경 전에 자동으로 데이터 스냅샷을 만들며, 추론 관계와 출처·등록 미디어 구조는 읽기 전용으로 구분합니다. [탐색·관계 확장 가이드](INSTANCE_GRAPH.md)를 참고하세요.

개체 생성·삭제는 선택한 데이터 파일을 잠그고 후보 그래프를 검증한 뒤 원자적으로 저장합니다. SHACL 또는 등록 미디어 검증에 실패하면 원본 파일을 유지합니다. 파일 잠금은 다른 worker와 편집 요청 사이의 데이터 유실을 방지합니다.

새 스냅샷은 스키마를 제외한 **데이터 전용 그래프**, 도메인·프로젝트 범위, UUID 기반 ID, SHA-256을 저장합니다. 웹 롤백은 범위·해시·SHACL·미디어를 검사하고 실제 데이터 파일을 복원하므로 서버 재시작 후에도 유지됩니다. 기존 범위 정보가 없는 스냅샷은 목록과 파일을 보관하며 웹 복원·비교 대상으로 사용하지 않습니다. Diff는 blank node를 고려하고 전체 증감 수와 최대 50개 예시를 반환합니다.

OWL-RL/RDFS 추론은 조회용 그래프의 관계를 확장합니다. 원본 데이터 파일에 자동 저장하지 않습니다. 자연어 조회와 유사 노드 추천은 로컬 규칙·구조·문자열 특징을 사용하는 기능입니다. 출처 보고서는 기록된 RDF의 조회 출력이며 외부 인증이나 내용의 진실성을 보증하는 문서로 취급하지 않습니다.

## Docker와 선택 서비스

Docker를 사용하는 경우 웹 포트는 호스트의 loopback에만 공개합니다.

```powershell
$env:ONTOLOGY_REGISTERED_ROOT_URI = & .\.venv\Scripts\python.exe -c "from pathlib import Path; print(Path.cwd().as_uri() + '/')"
docker compose up -d --build
docker compose ps
docker compose down
```

컨테이너 안에는 호스트의 Codex 로그인 세션을 복사하지 않습니다. 웹은 공유 `.codex-jobs/`에 작업을 보관하고 **호스트에서 실행한 Codex worker**가 처리합니다.

```powershell
$env:ONTOLOGY_CODEX_JOBS_DIR = Join-Path (Get-Location).Path '.codex-jobs'
.\.venv\Scripts\python.exe codex_jobs.py status
.\.venv\Scripts\python.exe codex_jobs.py run-next
```

Compose는 이 checkout 디렉터리 전체를 `/app`에 bind mount하여 프로젝트·스냅샷·작업 큐·예제 데이터를 host worker와 공유합니다. 디렉터리 공유로 파일의 원자적 교체도 지원합니다. 사용자 지정 큐 경로를 쓰면 `ONTOLOGY_CODEX_JOBS_DIR`와 Compose의 job volume을 같은 저장소에 맞춥니다.

`ONTOLOGY_REGISTERED_ROOT_URI`는 실제 미디어를 등록한 호스트 작업 폴더의 원래 `file:///.../` URI입니다. 이 checkout에서 등록한 프로젝트는 위 명령으로 설정합니다. 컨테이너의 `/app` 경로에서도 기존 RDF/manifest의 원래 파일 출처를 보존하면서 위치·hash를 검증합니다. 다른 위치로 복사한 프로젝트라면 원래 등록 폴더 URI를 명시해야 합니다.

Apache Jena Fuseki는 선택 사항입니다. 기본 로컬 앱은 Fuseki 없이 동작합니다. 선택 Compose 파일은 `compose.fuseki.yml`이며 활성화할 때 `FUSEKI_ADMIN_PASSWORD`를 명시적으로 설정해야 합니다. Fuseki 동기화는 대상 그래프를 쓰는 작업이므로 웹의 동기화 동작이나 명시적 CLI 옵션을 통해 실행합니다. 자세한 실행·중지 명령은 [매뉴얼](manual.md)에 있습니다.

## 다른 실제 미디어 등록하기

`import-plans/late-night-mood.json`을 복사해 새 계획을 만듭니다. `id`는 새 영문·숫자·하이픈 ID, `name`은 표시 이름, `source_directory`는 원본 폴더, `audio`와 `images`는 그 폴더 안 상대 파일 경로입니다. 음원 1개와 이미지 1개 이상이 필요합니다. 생략한 목표 길이는 음원 전체 길이이고 장면은 동일 간격으로 배치합니다.

```powershell
ffprobe -version
.\.venv\Scripts\python.exe import_media.py --plan import-plans\my-project.json
```

미디어 등록에는 PATH의 `ffprobe`가 필요합니다. 다른 위치는 `--ffprobe "C:\path\ffprobe.exe"`로 지정합니다. CLI는 원본을 읽고 `projects/<id>/assets`에 사본을 만들며 `project.json`, `manifest.json`, `data.ttl`, `import-plan.json`, `validation.txt`를 저장합니다. 실패한 가져오기는 등록되지 않고 기존 ID를 덮어쓰지 않습니다. 프로젝트는 별도 그래프로 읽어 예제·다른 프로젝트와 섞이지 않습니다.

## 파일 구성

| 파일·폴더 | 역할 |
|---|---|
| `app.py`, `templates/index.html` | 웹 API와 화면 |
| `codex_jobs.py`, `agent_llm.py`, `.codex-jobs/` | Codex 실행·수동 실행권·지속 작업 기록 |
| `auth.py`, `event_stream.py` | 로컬 접속 제한, 영속 감사 로그·SSE 이벤트 |
| `graph_io.py`, `instance_editor.py` | 공통 파일 잠금·원자적 저장·검증된 CRUD |
| `graph_versioning.py`, `.snapshots/` | 데이터 범위별 스냅샷·해시·Diff·영속 복원 |
| `owl_reasoner.py`, `graph_analytics.py` | 추론·그래프 분석 |
| `project_store.py`, `import_media.py`, `import-plans/` | 프로젝트·미디어 등록·파일 검증 |
| `projects/late-night-mood/` | 실제 미디어 사본·RDF·배치 계획·출처 |
| core-schema.ttl, *-schema.ttl, *-shapes.ttl, *-example.ttl | 공통 코어·도메인 정본·검증 규칙·예제 데이터 |
| *.owl, academic-schema.owl | Turtle 정본에서 생성하는 RDF/XML 호환 출력 |
| ONTOLOGY_GOVERNANCE.md, COMPETENCY_QUESTIONS.md | 모델링·버전·민감 정보 관리 기준 및 도메인 질문 목록 |
| build_ontology_exports.py, ontology_loader.py | OWL 출력 동기화와 로컬 import 스키마 로딩 |
| `ontology.owl`, `ontology.rdf` | 보존한 최초 대학 수강 OWL/RDF 자료 |
| `run_pipeline.py`, `simulation.py` | 미디어 메타데이터·협업 과정 시뮬레이션 |
| `fuseki_sync.py`, `compose.fuseki.yml` | 선택 Fuseki 연동 |
| `static/vendor/` | Bootstrap 5.3.2·Bootstrap Icons 1.11.1 및 라이선스 |
| `setup.ps1`, `run.ps1`, `start_all.ps1`, `stop.ps1`, `stop_all.ps1` | 설치·실행·소유 프로세스 중지 |
| `requirements.txt`, `requirements.lock.txt` | 의존성 범위와 검증된 버전 constraints |
| `tests/`, `manual.md`, `walkthrough.md` | 검사·사용법·현재 안정화 기록 |

## 검증과 데모

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\pyshacl.exe -s agent-shapes.ttl -e agent.owl -i rdfs agent-example.ttl
.\.venv\Scripts\pyshacl.exe -s mv-shapes.ttl -e mv.owl -i rdfs projects\late-night-mood\data.ttl
.\.venv\Scripts\pyshacl.exe -s academic-shapes.ttl -e academic-schema.owl -i rdfs academic-example.ttl
.\.venv\Scripts\python.exe build_ontology_exports.py --check
.\.venv\Scripts\python.exe controlled_vocab_check.py
.\.venv\Scripts\python.exe namespace_policy.py
.\.venv\Scripts\python.exe run_pipeline.py --output-dir exports\demo-runs
```

`run_pipeline.py`는 매번 별도 실행 폴더에 데모 RDF와 검증·요약을 저장합니다. 미디어는 예제 URI와 계획 상태로 표시하며 음원·이미지·영상을 생성하지 않습니다. 외부 SPARQL 쓰기와 webhook 전송은 해당 명령의 명시적 옵션으로만 요청합니다.

뮤직비디오 SHACL은 필수 필드·자료형·IRI 파일 주소, 양수 길이·해상도·순서, 음수가 아닌 시작 시각과 시작 < 종료, 장면 겹침·순번 중복·음원 길이 초과, 최종 영상의 프로젝트 입력 일치, 작업 의존성 순환을 검사합니다. 실제 프로젝트 검증은 파일 존재·SHA-256과 RDF/manifest의 파일 위치·길이·해상도 일치도 확인합니다. 미디어 내용 품질과 장면 사이의 의도된 빈 구간은 별도 검토 대상입니다.

온톨로지 스키마의 정본은 Turtle입니다. 스키마를 수정한 뒤 호환 RDF/XML 출력을 동기화하고 드리프트를 확인합니다.

```powershell
.\.venv\Scripts\python.exe build_ontology_exports.py
.\.venv\Scripts\python.exe build_ontology_exports.py --check
```

2026-10-03 등록 기록에는 실제 Late Night Mood의 SHACL·파일 존재·메타데이터·SHA-256 검사와 당시 자동 테스트 25개 통과가 남아 있습니다. 해당 수치는 당시 범위의 기록입니다. 현재 기능·안정화 범위는 [walkthrough.md](walkthrough.md)를 기준으로 확인합니다. `implementation_plan.md`와 일부 개념 문서는 최초 계획·과거 설계 자료이며 최신 운영 방법은 이 README와 [manual.md](manual.md)에 있습니다.

## Ontology quality, audit, and exchange

- Search ontology and project names or codes in the top selector. Use arrow keys and Enter to choose; Escape restores the current selection. The **새 온톨로지** button creates a persisted local draft with its own schema, shapes, sample and question fixtures. See [search and creation](ONTOLOGY_SEARCH.md).
- [AI 영화 제작](AI_FILM_ONTOLOGY.md) is available as `ai-film`: 8 classes, 26 properties and 5 operational questions covering scripts, scenes, shots, generation plans, reviews and edits. The 0.1.0 example is a synthetic production plan.
- [세계2차대전](WW2_ONTOLOGY.md)은 `ww2`로 선택합니다. 8개 클래스·21개 속성·6개 탐색 질문과 공식 기록관·박물관 출처를 연결한 10개 초기 사건을 제공합니다. 사건별 참여 역할과 항복 발표·문서 서명·작전 중지의 날짜를 구분합니다.
- [고양이](CAT_ONTOLOGY.md)는 `cat`으로 선택합니다. 8개 클래스·32개 속성·6개 탐색 질문으로 공식 품종 특징과 개체·환경·보호자·돌봄·관찰 기록을 연결합니다. 초기 개체와 활동은 가상 예제이며 품종 자료의 출처를 별도로 기록합니다.
- [소풍](PICNIC_ONTOLOGY.md)은 `picnic`으로 선택합니다. 8개 클래스·39개 속성·7개 탐색 질문으로 소풍 계획·일정·참가자·준비물 담당자·예산·날씨 확인 상태를 연결합니다. 초기 자료는 가상 계획 2건입니다.
- [결혼·결혼식](MARRIAGE_ONTOLOGY.md)은 `marriage`로 선택합니다. 8개 클래스·49개 속성·8개 탐색 질문으로 당사자·결혼 정보 기록·행사·초대 응답·준비 작업·예약·예산을 연결합니다. 초기 자료는 가상 계획 2건이며, 결혼 정보 기록과 행사 일정을 별도로 관리합니다.
- [ROS 2 시스템](ROS2_ONTOLOGY.md)은 `ros2`로 선택합니다. 13개 클래스·71개 속성·10개 탐색 질문으로 패키지·노드·토픽·서비스·액션·QoS·하드웨어·컨트롤러·tf2 프레임을 연결합니다. 초기 온실 구성은 합성 예시입니다.
- [자율주행](AUTONOMOUS_DRIVING_ONTOLOGY.md)은 `autonomous-driving`으로 선택합니다. 15개 클래스·92개 속성·11개 탐색 질문으로 차량·자동화 기능·ODD·센서·소프트웨어 스택·시나리오·안전 개념·시험 근거를 연결합니다. 초기 셔틀 구성은 합성 예시이며, 기능별 자동화 수준은 평가하지 않았습니다.
- [제1차 세계대전](WW1_ONTOLOGY.md)은 `ww1`로 선택합니다. 11개 클래스·34개 속성·12개 탐색 질문으로 참전국·진영·전투·지휘관·휴전/강화 협정을 연결합니다. 참전·이탈·전투 참여의 날짜 일관성을 검사하고, 예제의 모든 기록은 출처 확인 전(`unverified`)으로 표시한 간추린 초안입니다.
- [개](DOG_ONTOLOGY.md)는 `dog`로 선택합니다. 7개 클래스·24개 속성·10개 탐색 질문으로 개의 품종·보호자·동물등록·예방접종·진료·체중 기록을 연결하며, 증빙 없이 등록 완료나 접종 완료로 표시하지 못하게 합니다. 예제는 가상의 개 4마리입니다.
- [수영](SWIMMING_ONTOLOGY.md)은 `swimming`으로 선택합니다. 7개 클래스·22개 속성·10개 탐색 질문으로 선수·클럽·대회·수영장·종목·출전 결과·구간 기록을 연결하며, 증빙 없는 공식 기록과 25m·50m 수영장 기록의 혼동을 막습니다. 예제는 가상의 선수와 대회입니다.
- [축구](SOCCER_ONTOLOGY.md)는 `soccer`로 선택합니다. 6개 클래스·24개 속성·10개 탐색 질문으로 클럽·선수·대회·경기·출전 명단·득점과 경고·퇴장 사건을 연결하며, 보고서 없는 결과와 득점 사건과 맞지 않는 점수, 11명이 아닌 선발 명단을 막습니다. 예제는 가상의 클럽과 경기입니다.
- [이혼](DIVORCE_ONTOLOGY.md)은 `divorce`로 선택합니다. 7개 클래스·30개 속성·12개 탐색 질문으로 이혼 사건의 단계·당사자·자녀·양육 결정·양육비·재산분할을 연결하며, 증빙 없는 종결과 날짜 순서의 모순, 비율 합이 100이 아닌 분할을 막습니다. 법정 요건은 담지 않으며 법률 자문이 아닙니다. 예제는 가상 사건 5건입니다.
- [모방학습](IMITATION_LEARNING_ONTOLOGY.md) is available as imitation-learning: 16 classes, 84 properties and 10 questions cover demonstrations, behavior cloning, DAgger, inverse RL, policies, training/evaluation status, state-distribution shift and evidence. The robot-arm example is synthetic; no training or hardware actuation is claimed.
- [개의 비문](CANINE_NOSEPRINT_ONTOLOGY.md) is available as canine-noseprint: 16 classes, 100 properties and 12 questions model capture conditions, sample quality, nose-region processing, 1:1/1:N comparison, study-scoped evidence and data-use permissions. Its examples contain no image binaries or computed identification results.
- [무선공유기 온톨로지](WIRELESS_ROUTER_ONTOLOGY.md)는 `wireless-router`로 등록했다. 16개 클래스, 137개 속성, 12개 질문으로 장치·라디오·보안·망 분리·접속·펌웨어·설정·측정 상태를 모델링하며, 예시는 합성 자료다. [등록·검증 기록](reports/wireless-router-ontology.md).
- [Knowledge and Application Domain Ontology](DOMAIN_ONTOLOGY.md) documents `domain` (11 classes, 99 properties, 12 draft taxonomy concepts); [validation and local studio report](reports/domain-ontology.md).
- [Electricity Craftsman Ontology](ELECTRICITY_CRAFTSMAN_ONTOLOGY.md) documents the source-backed `electricity-craftsman` profile (11 classes, 102 properties, 22 listed practical materials, and 12 competency questions); [validation and studio report](reports/electricity-craftsman-ontology.md).
- See [the follow-up implementation record](reports/semantic-upgrade.md) for the seven improvements, search/creation work and measured limitations. [Explicit-data validation and local modules](RAW_VALIDATION_AND_MODULES.md), [provenance evidence](EVIDENCE_MODEL.md), [consumer compatibility](CONSUMER_COMPATIBILITY.md), [business workloads](BUSINESS_SCENARIOS.md), and [FHIR ingestion](FHIR_IMPORT.md) describe their commands and scope.
- See [the 2026-10-05 implementation and validation record](reports/quality-upgrade.md) for all six improvements, the 302-test result, actual official FHIR runs, and remaining coverage scope.
- The catalog now has 45 competency questions with synthetic fixtures and regression checks. `ontology_docs_check.py` checks Korean and English labels/definitions for all 231 named terms. [Semantic validation](SEMANTIC_VALIDATION.md) describes eight supported conflict patterns and their limits.
- [The quality guide](QUALITY_GUIDE.md) explains the schema/SHACL/CQ/instance coverage gate and the [current report](reports/ontology-quality.md). Explicit structural exceptions and existing query coverage debt remain visible; new gaps fail CI. Optional fields are validated by `property-contract-shapes.ttl` without fabricating missing provenance.
- [Term lifecycle](TERM_LIFECYCLE.md) checks deprecation, replacements, namespace/import integrity and compatibility with the reviewed `ontology-compatibility-baseline.json`. CI never rewrites that baseline automatically.
- Mutation audit events are stored in `.runtime/audit.jsonl` as a SHA-256 hash chain. Configure `ONTOLOGY_AUDIT_LOG_PATH` to move the file and `ONTOLOGY_AUDIT_RETENTION_DAYS` to set an optional retention period; `0` keeps the complete local history. `GET /api/v1/auth/audit-integrity` verifies the chain.
- `GET /api/v1/healthcare/fhir-bundle` exports only explicitly synthetic records as a FHIR R5 collection Bundle. See [the healthcare FHIR crosswalk](healthcare-fhir-crosswalk.md) for field requirements and omissions.
- The release namespace is undecided, so current `example.org` IRIs remain in place. Prepare and review a dry run with `python namespace_migration.py --host <owned-hostname>`; add `--apply` only after the namespace worksheet and consumer plan are complete. Project graphs and snapshots are excluded by default.
- Run `python ontology_quality.py`, `python ontology_docs_check.py`, `python term_lifecycle.py check`, `python term_lifecycle.py compare --previous ontology-compatibility-baseline.json`, `python controlled_vocab_check.py`, `python verify_all.py`, and `python run_tests.py` for the local quality gates.
- `python fhir_validate.py --synthetic-fixture --official structural --fetch-validator` runs the pinned official FHIR R5 validator on a constructed synthetic Bundle. Java is required. CI saves its OperationOutcome and log; structural conformance does not establish terminology-service validation. See [the FHIR crosswalk](healthcare-fhir-crosswalk.md).
