# 온톨로지 웹 스튜디오 사용 매뉴얼

2026-10-04 현재 로컬 구현을 기준으로 작성했습니다. 빠른 시작은 [README](README.md), 안정화 변경 기록은 [walkthrough](walkthrough.md)를 참고합니다.

## 1. 지원 범위와 데이터 선택

이 앱은 컴퓨터 소유자 한 사람이 RDF/OWL 지식 그래프를 조회·편집·검증하는 로컬 도구입니다. 웹 요청은 loopback 클라이언트, 로컬 Host, 같은 Origin으로 제한하며 전달된 proxy 헤더로 요청자를 신뢰하지 않습니다. 로컬 소유자가 모든 기능을 사용하고, UI 역할 전환용 키와 다중 사용자 RBAC는 제공하지 않습니다. 감사 로그와 SSE 이벤트 이력은 제한된 개수를 메모리에 보관해 서버 재시작 시 초기화됩니다.

| 도메인 키 | 데이터 목적 | SHACL |
|---|---|---|
| `mv` | 음원·이미지·장면·제작 작업과 출처 | 지원 |
| `e2e` | 확장 파이프라인의 예제 작업 이력, MV 규칙 공유 | 지원 |
| `devops` | 코드·빌드·배포 과정의 예제 모델 | 지원 |
| `agent` | 작업·실행·인계·검수와 승인 결과 | 지원 |
| `ecommerce` | 상품·주문·재고 관련 예제 모델 | 지원 |
| `healthcare` | 의료 관련 개념·예제 작업 모델 | 지원 |
| `academic` | 대학 수강 모델·과목·학생 관계 예제 | 지원 |

도메인 데이터는 개념과 제약을 실습하는 예제입니다. 7개 프로파일 모두 도메인별 SHACL shapes를 제공합니다. `e2e`는 `mv` schema·namespace를 공유하는 프로파일입니다.

대학 모델은 `academic-schema.ttl`을 정본으로 사용하고 `academic-schema.owl`은 RDF/XML 호환 출력으로 생성합니다. 앱 검증·인스턴스 편집은 정본 schema와 공통 로컬 코어를 읽습니다. `ontology.owl`·`ontology.rdf` 원본 자료는 별도로 보존합니다.

상단에서 도메인과 프로젝트를 선택합니다. 등록 프로젝트를 선택하면 `projects/<id>/data.ttl`을 사용하고, 가상 예제를 선택하면 도메인 설정의 예제 파일을 사용합니다. 조회 시 스키마를 함께 읽지만 CRUD·Codex 결과·새 스냅샷에는 선택한 데이터 파일을 사용합니다. API에서도 `ont`와 `project`를 함께 전달해야 같은 범위의 데이터를 다룹니다.

## 2. 설치·실행·종료

프로젝트 폴더에서 다음 명령을 실행합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
powershell -ExecutionPolicy Bypass -File .\run.ps1
```

`setup.ps1`은 `.venv`를 만들고 필요한 Python 패키지와 호환성을 확인합니다. `run.ps1`은 `127.0.0.1:5000`에서 실행합니다. 다른 포트는 `-Port 5001`을 지정하고, 현재 창의 `Ctrl+C`로 종료합니다.

```powershell
powershell -ExecutionPolicy Bypass -File .\start_all.ps1 -NoBrowser
Invoke-RestMethod http://127.0.0.1:5000/api/health
powershell -ExecutionPolicy Bypass -File .\stop_all.ps1
```

백그라운드 실행기는 `.runtime/web-studio.process.json`에 PID·실행 파일·스크립트·생성 시각을 기록하고 health check를 수행합니다. 포트가 다른 프로세스에 점유돼 있으면 시작을 실패 처리합니다. 중지 시 소유 정보가 일치하는 프로세스의 실제 종료를 확인합니다. 손상되거나 만료된 기록에서는 임의 프로세스를 종료하지 않습니다. 로그는 `.runtime/web-studio.log`와 `.runtime/web-studio.log.err`에 있습니다.

`stop.ps1`은 `run.ps1`으로 실행한 이 프로젝트의 서버를 확인해 중지합니다. 실행 중 Codex worker는 웹 서버와 별도 프로세스입니다. `.codex-jobs/`의 작업 기록과 로그로 처리 상태를 확인하세요.

## 3. 실제 미디어 조회·등록·검증

[Late Night Mood](http://127.0.0.1:5000/?ont=mv&project=late-night-mood)를 열고 **프로젝트 파일**에서 음원과 이미지, 장면 배치 계획을 확인합니다. 등록 사본은 WAV 1개와 JPEG 2개이며 원본 생성 모델·프롬프트를 미확인으로 기록했습니다.

**PySHACL 검증**은 규칙 검사와 등록 파일 검사를 함께 보여 줍니다. 파일 검사는 존재 여부, SHA-256, manifest/RDF 위치·재생 길이·해상도를 확인합니다. HTTP Range를 지원하는 음원 URL을 사용해 재생 위치를 이동할 수 있습니다. 실제 영상 렌더링 결과는 이 등록 프로젝트에 포함되지 않습니다.

새 프로젝트는 `import-plans/late-night-mood.json`을 복사해 고유 ID와 원본 상대 경로를 설정합니다.

```powershell
ffprobe -version
.\.venv\Scripts\python.exe import_media.py --plan import-plans\my-project.json
```

원본은 읽고 사본을 `projects/<id>/assets`에 등록합니다. 길이·해상도는 `ffprobe`로 측정하며, 실패한 프로젝트는 등록하지 않고 기존 ID도 덮어쓰지 않습니다. 등록 후 브라우저를 새로고침해 선택합니다. 계획의 상세 필드는 [README](README.md)에 있습니다.

## 4. API 키 없이 Codex 텍스트 작업 실행

### 자동 실행

호스트에서 저장된 ChatGPT 로그인과 Codex CLI를 확인합니다.

```powershell
codex login status
.\.venv\Scripts\python.exe codex_jobs.py status
```

ChatGPT 로그인이 필요하면 `codex login`을 사용합니다. 앱은 model API 키를 요구하지 않고 worker 환경에서 `OPENAI_API_KEY`·`CODEX_API_KEY`를 제거합니다. 상태 응답의 `cli_available`, `authenticated`, `auto_run_available`, `manual_available`로 자동 실행과 수동 처리 가능 여부를 확인합니다.

웹의 **Codex 작업**에서 요청, 작업 이름, 결과의 그래프 저장 여부를 지정하고 제출합니다. 실제 텍스트 산출물을 요청하고 필요한 사실·조건을 요청에 함께 입력합니다. 현재 worker는 선택 프로젝트의 RDF·manifest를 자동 첨부하지 않습니다. 준비된 CLI는 별도 worker에서 실행하며 준비되지 않은 요청은 대기 상태로 보관합니다.

CLI는 read-only sandbox에서 텍스트를 생성하고 `content`와 `summary`를 반환하도록 실행합니다. 실행된 모델의 이름을 앱에서 확정하지 못하면 모델 출처를 미확인으로 기록합니다.

### 지속 작업 기록과 상태

기본 저장 위치는 `.codex-jobs/codex_<32자리ID>/`입니다. `ONTOLOGY_CODEX_JOBS_DIR`로 저장 위치를 바꿀 수 있습니다.

| 파일 | 내용 |
|---|---|
| `job.json` | 요청, 작업 상태, 실행 시각, 결과, 저장 성공 여부 |
| `request.md` | Codex에 전달하는 요청 |
| `result.json`, `output.txt` | 실제 생성 결과와 텍스트 |
| `result-schema.json`, `cli-result.json` | 자동 실행의 결과 형식과 CLI 최종 출력 |
| `events.jsonl`, `cli.stderr.log`, `worker.log` | 자동 실행 과정과 오류 정보 |

| 상태 | 확인할 사실 |
|---|---|
| `awaiting_codex` | 접수·보관됐으며 아직 실행권을 확보하지 않음 |
| `running` | worker 또는 Codex 채팅이 실행권을 확보함 |
| `completed` | 실제 결과를 기록했고, 요청한 RDF 저장도 성공함 |
| `validation_failed` | 결과는 보관했으나 후보 그래프 검증·저장에 실패함 |
| `failed` | CLI 실행 오류·형식 오류·제한 시간 등으로 완료하지 못함 |

HTTP `202`와 요청 파일 생성은 접수 증거입니다. 생성 완료는 상태와 실제 결과 파일로 확인합니다. `save_to_graph: false`로 요청했다면 `completed`여도 RDF 저장을 요청하지 않은 작업입니다. 응답의 `result.persisted`를 함께 확인하세요. 실패한 실행은 자동으로 중복 제출하지 않습니다.

### CLI 명령

| 명령 | 동작 |
|---|---|
| `status` | CLI·ChatGPT 로그인 상태 |
| `list` | 저장된 작업 목록 |
| `show JOB_ID` | 특정 작업의 공개 상태·결과 |
| `enqueue --request-file FILE` | JSON 요청 접수, 준비되면 자동 실행 |
| `enqueue --request-file FILE --no-auto-run` | 요청만 보관 |
| `run JOB_ID` | 지정 대기 작업을 CLI로 실행 |
| `run-next` | 대기 작업 한 건을 CLI로 실행 |
| `claim JOB_ID` | Codex 채팅 처리를 위한 실행권·claim token 확보 |
| `complete JOB_ID --result-file FILE --claim-token TOKEN` | 실행권을 확인하고 실제 결과 기록 |

다음 예시는 UTF-8 BOM 없이 요청 JSON을 저장합니다. PowerShell 5의 기본 UTF-8 저장 방식과 Python JSON 읽기의 차이를 피하기 위한 방식입니다.

```powershell
$request = @{
    ont = 'mv'
    project = 'late-night-mood'
    prompt = 'Late Night Mood는 163.509333초 WAV 음원 1개와 1376x768 JPEG 이미지 2개를 등록한 프로젝트입니다. 최종 영상은 배치 계획 상태입니다. 이 사실을 바탕으로 한국어 소개문을 작성해 주세요.'
    agent_name = 'Codex'
    task_name = '프로젝트 소개문'
    save_to_graph = $true
} | ConvertTo-Json
$utf8 = New-Object System.Text.UTF8Encoding -ArgumentList $false
[IO.File]::WriteAllText((Join-Path (Get-Location).Path 'codex-request.json'), $request, $utf8)
.\.venv\Scripts\python.exe codex_jobs.py enqueue --request-file codex-request.json
.\.venv\Scripts\python.exe codex_jobs.py list
```

자동 실행이 시작되지 않았다면 `run JOB_ID` 또는 `run-next`로 처리합니다. 작업 ID는 응답의 실제 `job_id`를 사용합니다.

### 현재 Codex 채팅에서 수동 처리

```powershell
.\.venv\Scripts\python.exe codex_jobs.py enqueue --request-file codex-request.json --no-auto-run
.\.venv\Scripts\python.exe codex_jobs.py claim codex_<실제작업ID>
```

현재 Codex 채팅이 보관된 요청을 읽고 실제 텍스트를 작성합니다. 결과 파일은 다음 구조로 저장합니다.

```json
{
  "content": "실제로 작성한 최종 텍스트 전체",
  "summary": "작성 결과를 요약하는 한 문장"
}
```

```powershell
.\.venv\Scripts\python.exe codex_jobs.py complete codex_<실제작업ID> --result-file codex-result.json --claim-token <claim응답의실제토큰>
```

결과 파일도 UTF-8 BOM 없이 저장합니다. 실행권은 동일 작업의 중복 완료를 차단하며 공개 작업 조회에는 token을 포함하지 않습니다. 실제 텍스트가 없는 성공 기록은 만들지 않습니다.

결과를 그래프에 저장할 때 활동·Codex agent·입력·출력·시각·내용 hash를 PROV-O와 Codex 속성으로 연결합니다. SHACL과 등록 미디어 검사 뒤 선택한 데이터 파일을 잠그고 원자적으로 교체합니다. 실패 시 결과 파일은 남기고 원래 그래프를 유지합니다.

## 5. 개체 편집·스냅샷·복원

### 인스턴스 지식 그래프 확장

인스턴스 탭은 스키마 정의를 제외한 실제 개체와 관계를 표시합니다. 이름·URI 검색, 유형·클래스·관계 필터, 연결/고립 분류, 1·2단계 주변 탐색, 방향별 최단 경로, 속성 값 및 들어오는·나가는 관계를 제공합니다. RDFS/OWL-RL 미리보기의 점선은 추론 관계이며 원본에 자동 저장하지 않습니다.

관계 편집에서 출발 개체·관계·도착 개체를 선택해 연결하거나 해제할 수 있습니다. 스키마의 허용 관계·클래스 범위와 후보 SHACL·미디어 검증이 통과하면 변경 전 자동 스냅샷을 만들고 파일에 저장합니다. 생성 출처와 등록 미디어 구조는 보호합니다. 선택 개체의 사실을 **Codex 관계 제안** 요청문에 넣어 검토한 뒤 필요한 관계를 직접 추가할 수도 있습니다.

자세한 조작·범위·API는 [인스턴스 지식 그래프 가이드](INSTANCE_GRAPH.md)를 참고합니다. 표시 한도나 필터로 일부 개체만 내려받았다면 경로 탐색도 해당 범위에 제한됩니다.

### 개체와 데이터 파일

**새 개체 등록 (CRUD)**에서 클래스·이름·속성을 입력합니다. 생성과 삭제는 동일 파일 잠금 안에서 최신 데이터를 읽고 후보 그래프를 검증한 뒤 저장합니다. 삭제할 개체의 incoming/outgoing 관계도 제거하므로 필수 참조를 깨뜨리는 삭제는 거부합니다. 반환되는 트리플 수는 실제 추가·삭제한 수입니다.

**버전 관리 & 롤백**에서 편집 전 스냅샷을 만듭니다. 새 스냅샷은 데이터만 저장하고 도메인·프로젝트 범위, SHA-256, UUID 기반 고유 ID를 기록합니다. 같은 초에 여러 개를 만들어도 덮어쓰지 않습니다.

Diff는 선택한 범위 안에서 새 스냅샷끼리 또는 새 스냅샷과 현재 데이터 사이를 비교합니다. blank node 이름이 달라도 같은 구조를 동일하게 계산합니다. 수치는 전체 트리플 기준이며 목록은 최대 50개 예시와 전체 URI를 반환합니다.

롤백은 스냅샷 ID·범위·SHA-256을 확인하고 후보 그래프의 SHACL·미디어를 다시 검사합니다. 통과하면 실제 데이터 파일을 원자적으로 교체하고 복원 결과를 반환합니다. 다른 도메인·다른 프로젝트의 스냅샷과 변조된 파일은 거부합니다. 저장에 실패하면 원래 데이터 파일을 유지합니다.

기존 범위·데이터 출처 정보가 없는 스냅샷은 목록에 남지만 웹 비교·복원은 허용하지 않습니다. 파일은 과거 기록으로 열어 확인할 수 있습니다. 스키마가 함께 들어 있던 과거 스냅샷으로 현재 데이터 파일을 덮어쓰지 않도록 새 데이터 전용 스냅샷을 사용합니다.

## 6. 조회·추론·시뮬레이션

SPARQL은 선택한 도메인·프로젝트의 RDF를 조회합니다. 자연어 질의는 로컬 패턴에 대응하는 쿼리를 실행하며, 지원하지 않는 표현에는 제한이 있습니다. 유사 개체 기능은 구조·라벨 특징을 비교하므로 학습된 외부 embedding 모델의 추론 결과로 해석하지 않습니다.

**OWL-RL 추론 확장**은 스키마·데이터의 OWL-RL 또는 RDFS 관계를 계산해 조회용 확장 그래프를 반환합니다. 원본 파일은 별도 저장 동작이 있어야 변경됩니다. 중심성 분석은 그래프 구조를 보여 주는 보조 지표이며 실제 운영 장애를 자동 진단한 증거로 사용하지 않습니다.

출처 보고서는 RDF에 기록된 활동·입력·출력·파일 정보를 보여 주는 출력물입니다. 모델·원본 출처가 확인되지 않은 항목은 미확인으로 유지하고, 보고서 자체를 공인 인증서나 보증으로 취급하지 않습니다.

**에이전트 시뮬레이터**와 `run_pipeline.py`는 작업 과정·메타데이터를 실습합니다. 실제 음악·음성·이미지·영상 생성 또는 외부 배포를 수행한 증거가 아닙니다.

```powershell
.\.venv\Scripts\python.exe run_pipeline.py --output-dir exports\demo-runs
```

각 실행은 별도 폴더에 데모 RDF, SHACL 보고서, summary를 저장합니다. 외부 SPARQL 쓰기나 webhook은 `--update-endpoint`, `--notify-webhook`을 명시적으로 지정했을 때 실행합니다. 원본 예제 파일은 덮어쓰지 않습니다.

## 7. Docker와 호스트 Codex worker

```powershell
$env:ONTOLOGY_REGISTERED_ROOT_URI = & .\.venv\Scripts\python.exe -c "from pathlib import Path; print(Path.cwd().as_uri() + '/')"
docker compose up -d --build
docker compose ps
docker compose down
```

Compose는 웹만 기본 실행하고 `127.0.0.1:5000`에 공개합니다. 컨테이너 내부의 `0.0.0.0` 바인딩은 명시적 로컬 Docker 모드와 설정한 bridge subnet에서만 허용합니다.

호스트의 ChatGPT 로그인은 호스트 Codex CLI가 사용합니다. 웹 컨테이너는 공유 큐에 작업을 보관합니다. Compose의 `./:/app` 디렉터리 bind mount로 프로젝트·예제 데이터·스냅샷·큐와 파일의 원자적 교체를 공유합니다. 같은 checkout에서 worker를 실행합니다.

```powershell
$env:ONTOLOGY_CODEX_JOBS_DIR = Join-Path (Get-Location).Path '.codex-jobs'
.\.venv\Scripts\python.exe codex_jobs.py status
.\.venv\Scripts\python.exe codex_jobs.py run-next
```

컨테이너의 큐 경로는 `/app/.codex-jobs`이고 호스트는 같은 폴더의 `.codex-jobs`입니다. 사용자 지정 큐는 환경 변수와 volume 매핑을 함께 수정합니다. `run-next`는 한 번 실행할 때 한 작업을 처리하므로 필요할 때 반복 실행합니다.

등록 미디어의 원래 URI는 호스트의 파일 위치입니다. `ONTOLOGY_REGISTERED_ROOT_URI`에는 미디어를 등록한 원래 작업 폴더의 절대 로컬 디렉터리 URI(`file:///.../`)를 지정합니다. 위 명령은 현재 checkout에서 등록한 경우의 값입니다. 다른 위치로 옮긴 프로젝트는 최초 등록 폴더를 명시합니다. 이 설정은 컨테이너의 실제 파일을 원래 등록 위치에 대응시켜 검사하며 RDF·manifest의 원본 출처 URI를 변경하지 않습니다. 설정한 원래 범위 밖의 파일 URI와 변조된 hash는 계속 거부합니다.

## 8. 선택 Fuseki와 외부 스튜디오

로컬 앱은 Fuseki 없이 동작합니다. 기존 Fuseki를 사용하면 `FUSEKI_ENDPOINT`를 지정하고 웹에서 상태를 확인한 뒤 명시적으로 동기화합니다. 기본 endpoint는 `http://127.0.0.1:3030/ds`입니다. 동기화는 대상 named graph를 교체하는 쓰기 동작입니다.

선택 컨테이너는 실행 전에 비밀번호를 설정합니다. 값을 문서나 소스 파일에 보관하지 말고 실행 환경에서 설정합니다.

```powershell
# 먼저 실행 환경에 FUSEKI_ADMIN_PASSWORD를 설정합니다.
docker compose -f docker-compose.yml -f compose.fuseki.yml up -d --build
docker compose -f docker-compose.yml -f compose.fuseki.yml ps
docker compose -f docker-compose.yml -f compose.fuseki.yml down
```

Native 웹과 선택 Fuseki를 함께 시작할 때는 `start_all.ps1 -WithFuseki`를 사용하고 `stop_all.ps1 -WithFuseki`로 이 실행기가 소유한 서비스를 중지합니다. API 동기화 성공 여부는 Fuseki의 쓰기 허용·인증 설정과 실제 응답으로 확인해야 합니다.

`start_all.ps1 -WithMvStudio`는 별도 sibling 폴더 `demo/02_maketing/web_server.py`의 스튜디오를 명시적으로 요청합니다. 해당 폴더와 실행 환경이 필요하고, 종료에는 `stop_all.ps1 -WithMvStudio`를 사용합니다. 기본 실행 범위는 온톨로지 스튜디오입니다.

## 9. 주요 API

모든 HTTP 예시는 로컬 주소에서 실행합니다. 별도 API 키 헤더는 필요하지 않습니다.

| Method | Endpoint | 동작 |
|---|---|---|
| `GET` | `/api/health` | 서비스 health |
| `GET` | `/api/projects?ont=mv` | 등록 프로젝트 목록 |
| `GET` | `/api/v1/codex/status` | Codex 가용성 |
| `POST` | `/api/v1/codex/jobs` | 텍스트 작업 접수, `202` |
| `GET` | `/api/v1/codex/jobs` | 작업 목록 |
| `GET` | `/api/v1/codex/jobs/<job_id>` | 작업 상태·결과 |
| `POST` | `/api/v1/codex/jobs/<job_id>/run` | 대기 작업의 자동 worker 시작 |
| `POST`, `DELETE` | `/api/v1/instances` | 검증된 개체 생성·삭제 |
| `GET` | `/api/v1/snapshots` | 선택 범위 스냅샷 목록 |
| `POST` | `/api/v1/snapshots/create` | 검증된 데이터 전용 스냅샷 생성 |
| `GET` | `/api/v1/snapshots/diff` | 새 스냅샷의 의미적 Diff |
| `POST` | `/api/v1/snapshots/rollback` | 검증된 영속 복원 |
| `POST` | `/api/v1/reasoning/expand` | 조회용 OWL-RL/RDFS 확장 |
| `GET` | `/api/v1/auth/identity` | 로컬 소유자 identity |
| `GET` | `/api/v1/auth/audit-logs` | 메모리 최근 감사 로그 |
| `GET` | `/api/v1/stream/events` | SSE 이벤트 |
| `GET` | `/api/v1/fuseki/status` | 선택 Fuseki 연결 상태 |
| `POST` | `/api/v1/fuseki/sync` | 명시적 Fuseki 그래프 쓰기 |
| `POST` | `/api/v1/simulate` | 메타데이터 시뮬레이션 |
| `GET` | `/api/docs` | API 화면 |

기존 `/api/v1/llm/status`, `/api/v1/llm/generate` 경로는 Codex 상태·작업 접수의 호환 alias입니다. 모델 목록이나 다른 provider 선택 경로로 사용하지 않습니다.

```powershell
$body = @{
    ont = 'mv'
    project = 'late-night-mood'
    description = '편집 전 데이터 보관'
} | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:5000/api/v1/snapshots/create -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($body))
```

## 10. 검사와 운영 기록

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\pyshacl.exe -s mv-shapes.ttl -e mv.owl -i rdfs projects\late-night-mood\data.ttl
.\.venv\Scripts\python.exe -m pip check
```

테스트는 임시 데이터에서 변경·실패·복원·worker 동시 실행을 확인하고 실제 fixture와 등록 미디어를 보존해야 합니다. 최근 안정화 범위와 전체 확인 결과는 [walkthrough](walkthrough.md)에 기록합니다. `.codex-jobs/`, `.snapshots/`, 등록 프로젝트 데이터는 작업·복구 자료이므로 운영 환경에서 별도 백업 대상으로 관리합니다.
