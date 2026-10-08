# 출처 검증 근거 모델

파일 등록이 확인됐다는 사실과 원본의 생성 과정·최초 출처가 확인됐다는
사실은 각각 별도의 주장으로 기록합니다. 동일한 자산이 한 범위에서는
확인되고 다른 범위에서는 미확인일 수 있습니다.

| 확인 범위 | 사용할 상태 | 확인한 내용 |
|---|---|---|
| `LocalFileIntegrity` | `Observed`, `Failed`, `Unverified` | 등록 복사본의 존재, 등록 지문 일치, 로컬 원본 복사본과의 현재 바이트 대조 |
| `OriginalGeneration` | `Verified`, `Unverified` | 독립 검토 근거가 확인한 원본 생성 모델과 프롬프트 |
| `OriginalOrigin` | `Verified`, `Unverified` | 독립 검토 근거가 확인한 원본 최초 출처 |

`VerificationClaim`은 대상 자산·프로젝트·범위·상태·검사 시점·검사 수행자를
기록합니다. 실제로 읽은 파일에만 `EvidenceRecord`의 위치와 SHA-256을
부여합니다. `Unverified`는 미확인 사유를 반드시 기록하고 모델·프롬프트·
원본 출처·긍정 근거·독립 확인 시점을 갖지 않습니다. 누락 파일에는 실제
관찰 지문을 만들지 않습니다. `expectedSHA256`은 등록 기준값입니다.

`Verified`인 원본 주장은 별도로 검토한 문서 근거와 `verifiedAt`이 필요합니다.
생성 주장은 모델과 프롬프트 모두, 출처 주장은 원본 출처 IRI를 갖습니다.
로컬 등록 도구 버전과 원본 생성 모델을 혼동하지 않도록 SHACL로 제한합니다.
스키마는 독립 검토 주장을 표현하지만 문서 내용의 진실이나 검사자의
신원을 자동으로 인증하지 않습니다.

## 실행

프로젝트에는 기존 등록 파일을 그대로 두고 별도 근거 파일을 생성합니다.

```powershell
.venv/Scripts/python.exe evidence.py refresh --project projects/late-night-mood --report reports/provenance-evidence.json
.venv/Scripts/python.exe evidence.py check --project projects/late-night-mood --report reports/provenance-evidence-check.json
.venv/Scripts/python.exe -m unittest tests.test_evidence -v
```

`refresh`는 등록 명세와 RDF의 자산·지문·위치를 대조하고 복사본 및 기록된
로컬 원본을 읽어 검사합니다. 원본 생성·출처의 독립 근거를 입력받아
검증하는 기능은 제공하지 않으므로 자동으로 생성한 두 원본 주장은 항상
`Unverified`입니다. 사람이 검토한 주장은 별도 검토 그래프에서 관리해야
합니다. 합성 예제의 `Verified` 주장은 스키마 사용 예이며 실제 미디어의
출처 확인 결과가 아닙니다.

`check`는 저장된 근거를 다시 읽고 현재 파일·등록 스냅샷·주장 완전성·SHACL을
검사합니다. 저장 근거 그래프의 지문도 JSON과 대조합니다. 미디어가 바뀌거나
사라지면 종료 코드 1, 입력 오류나 근거 파일 부재는 2입니다. 정상은 0입니다.
실패한 검사 결과도 구조적으로 올바른 근거 그래프일 수 있으므로
`evidence_graph_conforms`만으로 무결성 통과라고 해석하지 않습니다.

등록 복사본이 정상이고 로컬 원본 복사본이 없어진 경우에는 등록 무결성은
유효하며 로컬 원본 대조를 `missing`으로 보고합니다. 원본 복사본을 실제로
읽었는데 등록 바이트와 달라진 경우에는 실패로 보고합니다. 어느 경우에도
원본 생성 또는 최초 출처의 상태를 승격하지 않습니다.

`refresh`가 만든 출력:

- `evidence.ttl`: 자산마다 세 범위의 주장과 실제 관찰한 파일 근거
- `evidence.json`: 로컬 경로·지문을 포함한 비공개 검사 스냅샷
- `evidence-validation.txt`: 근거 그래프의 SHACL 결과
- `evidence-summary.md`: 등록 자산별 확인 범위와 미확인 이유
- `--report` 출력: 자산 수와 상태 수만 포함한 공유 집계 JSON

이미 기준선이 존재하면 manifest.json·data.ttl·project.json의 변경을 발견한
`refresh`는 기존 근거를 덮어쓰지 않습니다. 변경 사유와 이전 근거를 보존하고
검토한 뒤 새 프로젝트 버전으로 등록하여 새 기준선을 만드세요.

이 도구는 원본 파일·등록 미디어·등록 명세·등록 RDF를 쓰지 않습니다. 고정
출력 위치의 심볼릭 링크와 자산 디렉터리 밖으로 벗어나는 복사본 경로는
거부합니다. 파일 검사 중 크기 또는 수정 시점이 바뀌어도 실패시킵니다.

## 검증과 한계

`evidence-example.ttl`은 전체가 합성 데이터입니다. `EVIDENCE_QUESTIONS.md`의
세 운영 질문은 현재 파일 상태, 원본 미확인 사유, 독립 검토 주장의 근거와
시점을 조회합니다. 테스트는 고정 정답뿐 아니라 문서 근거 누락, 미확인
주장의 모델·프롬프트 오염, 복사본 근거를 원본 근거로 대체한 경우,
파일 누락·변조, 등록 명세와 RDF의 불일치 및 일괄 변경을 검사합니다.

현재 검사는 기록된 시점의 바이트 관찰입니다. 동일한 해시는 원본 생성
과정·권리·작성자·최초 출처를 증명하지 않습니다. 근거 sidecar 전체가 함께
다시 작성되는 공격을 독립적으로 방지하는 서명·외부 앵커는 아직 없습니다.
원본 생성 또는 출처를 확인하려면 권위 있는 생성 기록이나 출처 문서를
실제로 확보하고 검토한 사람과 시점 및 근거 범위를 기록해야 합니다.
