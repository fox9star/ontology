# 무선공유기 온톨로지

## 프로필

- ID: `wireless-router`
- 버전: `0.1.0` (초안)
- 네임스페이스: `https://example.org/ontology/custom/wireless-router#`
- 릴리스 URI: 미정. 소유 도메인 확정 전까지 초안 네임스페이스를 유지한다.
- 범위: 공유기 장치, 무선 인터페이스, 무선망 프로필, 보안 설정, 논리 구간·망 분리, 상위 연결, 클라이언트 접속, 펌웨어, 설정 스냅샷, 성능 관측, 사건 기록, 문서 근거.

## 모델 원칙

지원 가능성은 라디오의 `radioSupportedStandard`와 근거 상태로, 적용 설정은 `radioConfiguredState` 및 보안 프로필의 설정 상태로, 실제 동작은 접속·관측 기록으로 표현한다. `unknown`, `not_observed`, `not_assessed`, `planned`는 서로 다른 상태다.

SSID 원문, 비밀번호·PSK, 관리자 인증정보, 실제 MAC·IP 주소, 일련번호를 저장하는 속성은 정의하지 않았다. 클라이언트와 망은 합성 별칭이나 가명으로 표현한다. 채널 번호는 선택적 운영 관측값으로만 두며 국가별 허용 채널이나 출력 규정을 정의하지 않는다.

보안 표기(WPA2/WPA3 등)는 검색 가능한 어휘 값이다. 값이 기록됐다는 사실만으로 장치가 해당 기능을 지원하거나, 인증을 받았거나, 해당 설정이 적용됐다고 해석하면 안 된다. `securityCertificationClaimStatus`와 `securityConfigurationStatus`가 그 구분을 보존한다.

## 주요 클래스

`RouterSystem`, `RouterDevice`, `RadioInterface`, `WirelessNetwork`, `SecurityProfile`, `NetworkSegment`, `IsolationPolicy`, `UplinkConnection`, `ClientDevice`, `AssociationRecord`, `FirmwareRelease`, `FirmwareUpdate`, `ConfigurationSnapshot`, `PerformanceObservation`, `IncidentRecord`, `DocumentationSource`.

현재 스키마는 클래스 16개, 객체·데이터 속성 137개다. 예시 그래프는 22개의 합성 개체와 230개 트리플을 담는다.

## 역량 질문

- **WR-01** — 시스템에 어떤 장치·무선망·상위 연결이 기록되어 있고, 실제 관측 자료인지 합성 자료인지?
- **WR-02** — 무선 대역·지원 표준 주장과 현재 설정 상태는 각각 무엇이며 어떤 근거가 있는가?
- **WR-03** — 실제 SSID 없이 어떤 무선망 별칭·용도·식별자 처리 상태가 기록되는가?
- **WR-04** — 보안 프로토콜 표기와 적용 상태는 무엇이며 자격 증명은 어떻게 처리되는가?
- **WR-05** — 논리 구간과 망 분리 정책의 의도·실제 적용 상태·근거 상태는 무엇인가?
- **WR-06** — 클라이언트 식별자는 어떻게 가명화되어 있으며 접속은 관측·계획·미관측 중 무엇인가?
- **WR-07** — 상위 연결의 종류, 상태, 사업자 정보 공개 및 인증 정보 처리 상태는?
- **WR-08** — 현재 펌웨어 정보의 확실성과 업데이트 진행·재시작·롤백 상태는?
- **WR-09** — 설정 스냅샷은 계획·적용·보관 중 어디에 있고, 비밀 제거·완전성·출처 상태는?
- **WR-10** — 성능 지표가 측정되었는가? 그렇다면 값·단위·방법·시각·표본 수는?
- **WR-11** — 장애·보안 사건의 상태·분류·심각도·영향·근거 상태는?
- **WR-12** — 자료 출처가 뒷받침하는 범위와 이 예시 또는 개별 장비에 대한 한계는?

SPARQL 질문은 문법 파싱까지만 확인했다. 질문 fixture의 기대 답과 쿼리 결과는 실행·비교하지 않았다.

## 근거와 한계

- [NIST SP 800-153: Guidelines for Securing Wireless Local Area Networks](https://csrc.nist.gov/pubs/sp/800/153/final) — WLAN 구성요소의 설계·배포·유지보수·모니터링과 보안 구성을 다룬다. 별도 보안 프로필을 쓰는 WLAN(예: 내부·게스트)의 분리와 보안 평가·지속 모니터링을 참고한다.
- DOI: [10.6028/NIST.SP.800-153](https://doi.org/10.6028/NIST.SP.800-153)

이 자료는 2012년 지침이다. 현재 제품의 기능, 펌웨어 지원, 인증, 실제 설정, 전파 규정 또는 이 초안의 합성 장치 상태를 입증하지 않는다. 채널·출력·대역 허용 범위는 국가와 장치에 따라 달라 이 온톨로지에서 판정하지 않는다.

## 파일과 검증

- `custom-ontologies/wireless-router/schema.ttl` 및 `schema.owl`: OWL 스키마 (Turtle 및 RDF/XML)
- `shapes.ttl`: SHACL 필수 속성, 타입, 통제 어휘와 숫자 범위
- `example.ttl`: 탐색기에 표시되는 합성 예시
- `questions.md`, `question-fixture.ttl`, `question-answers.json`: 질문·별도 합성 fixture·수동 기대 답 메모
- `consumer-cases.trig`: 예상 수용/거부 예시. 소비자 호환성 검사는 실행하지 않음.
- `reports/wireless-router-ontology.json`: 검증 요약, 파일 해시 및 로컬 스튜디오 관측

SHACL 입력 검증: 전체 적합 `True`, 명시 데이터 적합 `True`, RDFS 확장 진단 적합 `True`; 결과 0 / 0건, 확장 추론 타입 38건.
