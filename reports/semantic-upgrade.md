# 온톨로지 후속 개선·검색·AI 영화 제작 구현 기록

2026-10-05 로컬 작업 기록. 앞선 302개 검사 결과는 `quality-upgrade.md`의 당시 범위다. 이 기록은 후속 일곱 항목과 이후 요청한 검색·새 온톨로지 추가·AI 영화 제작 모델을 다룬다.

| 요청 | 구현 결과 | 근거 |
|---|---|---|
| 업무 질문 강화 | 기존 25개에 업무 성공/진단 6개, 실제 스키마 성능 질문 6개, 출처 질문 3개 추가. AI 영화 제작 질문 5개를 포함해 현재 45개 | `COMPETENCY_QUESTIONS.md`, `EVIDENCE_QUESTIONS.md`, `custom-ontologies/ai-film/questions.md` 및 고정 정답·관계 변조 반례 |
| 원자료와 추론 검증 분리 | 명시 타입·스키마 선언을 검사한 뒤 별도 RDFS 사본을 진단. API·저장·가져오기·제작 파이프라인에 적용 | `validation_pipeline.py`, `raw-validation-project.json` |
| 출처 확인 상태 | 실제 자산 3개의 로컬 파일 관찰 3건, 원본 생성 미확인 3건, 원본 출처 미확인 3건. 파일 지문 비교 통과 | `provenance-evidence-check.json`, 프로젝트 `evidence.*` |
| 소비자 호환성 | 고정 SHACL 계약·수용/거절 사례·OpenAPI·실제 API 응답 2종·질문 정답 계약 비교. 현재 수집 9개 shape 프로파일/18개 사례/45개 질문 | `consumer-compatibility.json`, 원래 8개 프로파일/16개 사례/40개 질문 기준선 보존 |
| 모듈 로더 | ontology/version IRI로 로컬 전이 import 해석, 충돌·순환·미해결·경로 이탈 거절, 실제 파싱한 바이트의 해시 기록 | `ontology_modules.json`, `ontology_loader.py`, 로더 반례 검사 |
| 성능 측정 | 10,008/100,000 triple, 6개 질의, 예열+각 10회+별도 메모리 측정. 세 번의 측정 실행 360회 정답 일치, 전체 SHACL 통과 | `sparql-benchmark-baseline.json`, `sparql-benchmark.json`, `sparql-benchmark-idle.json` |
| FHIR 가져오기 | 제한된 R5 collection Bundle→독립 RDF, 지원 필드/손실 행렬, 원문 제한 접근 보관, 임의 입력 Unverified | `fhir-roundtrip-evidence.json`, `fhir-field-loss-matrix.json` |
| 검색 메뉴 | 이름·영문 이름·코드 검색, 한국어 조합 처리, 키보드 선택, 결과 없음 안내, 최대 50개 표시, 프로젝트 갱신 동기화 | `search-and-creation-verification.json`, Node DOM 동작 검사 |
| 새 온톨로지 | 입력 폼→로컬 API→완성된 디렉터리 원자 등록→즉시 선택. 중복/경로/재시작/동시 생성 검사 | `ontology_catalog.py`, `ONTOLOGY_SEARCH.md` |
| AI 영화 제작 | 0.1.0 초안, 8개 클래스·26개 속성, 실제 실행을 주장하지 않는 합성 계획, 생성·권리·품질 근거 제약 | `AI_FILM_ONTOLOGY.md`, `custom-ontologies/ai-film/` |

스키마는 10개 모듈에 231개 named class/property를 갖고 모두 한국어·영어 이름과 정의가 있다. SHACL과 연결된 용어는 222개, 질문에 직접 등장하는 용어는 131개다. 기존 질문 공백 21개를 해소했고 남은 100개는 `ontology-quality-policy.json`에 미완료로 유지한다. 현재 품질 게이트는 앱 예제 8개, 증거 예제 1개, 실제 프로젝트 1개를 검사하여 통과했다. 포괄적인 코어·분류 개념의 구조 예외 10개는 이유와 함께 유지한다.

FHIR 합성 왕복은 지원하는 사실 25개가 일치했다. 공식 R5 5.0.0 구조 검사 결과는 fatal/error 0, warning 6, information 5다. 이번 왕복 검사는 오프라인 구조 검사이며 새 용어 서비스 검증·임상 적합성·모든 FHIR 필드의 무손실 변환을 의미하지 않는다.

성능 비교는 통과로 바꾸지 않았다. 첫 재측정에서 25% 기준 초과 시간 지표 16개, 독립 재측정에서 3개가 남았다. 정답과 데이터 적합성은 통과했지만 타이밍 회귀 게이트는 실패 상태다. 동일 머신의 실행 변동과 코드 효과를 분리할 추가 관측이 필요하다. 이전 기준선과 모든 관측 결과를 보존했다.

첫 통합 검사 468개 중 4개가 실패했다. 두 건은 새 프로파일/질문 수를 고정했던 검사 기대값이었고, 두 건은 AI 영화 예제 IRI가 기존 도메인 탐색 필터와 맞지 않아 화면 개체 수가 0이 되는 문제였다. 고정된 이전 호환성 기준선을 유지하면서 추가 항목의 기대를 동적으로 비교하도록 고쳤고, 화면 예제 개체를 해당 도메인 네임스페이스에 등록했다. 관련 19개 재검사는 통과했다. 최종 전체 결과는 `semantic-upgrade-verification-final.json`, 최초 결과는 `semantic-upgrade-verification.json`에 보존한다.

최종 전체 검사: **468개 통과, 실패 0·오류 0·건너뜀 0**. Python 3.13.15에서 총 201.5초, 2026-10-05 08:45 KST에 완료했다. 생성 RDF/XML 7개 일치, 어휘 12개 체계, namespace/생애주기/스키마 호환성/소비자 호환성/품질 집계도 통과했다. 수정된 성능 비교기의 누락 규모·질의 차단 반례는 추가 4개 검사로 확인했고 최종 전체 검사에도 포함했다. CI YAML 파서 모듈은 로컬 환경에 없어 파서 검사는 수행하지 못했으며 클라우드 실행은 별도로 남는다.

기존 로컬 서버를 소유 프로세스 확인 후 재시작했고 `http://127.0.0.1:5000/?ont=ai-film`에서 검색 모듈·생성 폼·도메인 목록·예제 개체 14개·검증 API를 확인했다. 실제 브라우저 자동 접속은 도구의 `ERR_BLOCKED_BY_CLIENT`로 막혀 시각적 렌더링 검증은 완료하지 못했다. 검색의 키보드/IME/대량 결과/텍스트 처리 동작은 Node DOM 하네스로 검사했다.

API 키 없이 동작한다. 공개 URI는 미정이며 example.org 예약 URI로 `--release`가 거절되는 정책을 유지한다. 원본 미디어와 기존 등록 그래프·명세는 수정하지 않았다. 새 초안 모델과 실제 확인된 생성·출처 사실을 혼동하지 않도록 상태와 근거를 나눠 기록했다. CI 설정은 수정했으며 이번에 클라우드 CI를 실행했다고 주장하지 않는다.
