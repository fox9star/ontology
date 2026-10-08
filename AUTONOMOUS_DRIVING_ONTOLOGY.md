# 자율주행 온톨로지

검색 가능한 프로필 목록에서 **자율주행 온톨로지 (autonomous-driving)** 를 선택합니다. 로컬 스튜디오는 [http://127.0.0.1:5000/?ont=autonomous-driving](http://127.0.0.1:5000/?ont=autonomous-driving)에서 열 수 있습니다.

## 모델 범위

0.1.0 초안은 클래스 15개, 속성 92개, 인스턴스 39개와 SPARQL 탐색 질문 11개를 포함합니다.

- 차량별 주행 자동화 기능과 명시적으로 평가된 SAE 수준
- 운행설계영역(ODD)의 도로 유형·지역·속도·날씨·조명 조건
- 카메라·라이다·GNSS/IMU·휠 오도메트리 센서
- 감지, 인지, 위치추정, 경로계획, 제어, 차량 인터페이스와 ODD 감시 모듈
- 지도, 경로, 궤적, 도로 행위자와 재현 가능한 시나리오
- 안전 기능 개념, 시험 상태·결과·증거, 주장별 공식 문서 출처

SAE J3016의 0–5 수준은 용어 항목으로 기록합니다. 수준은 자동차 전체에 일괄 부여하는 값이 아니라, 해당 시점에 작동한 주행 자동화 기능을 설명하는 분류로 다루며 가상 셔틀 기능에는 수준을 평가해 연결하지 않았습니다. [SAE J3016](https://saemobilus.sae.org/standards/j3016_202104-taxonomy-definitions-terms-related-driving-automation-systems-road-motor-vehicles?tabType=viewannotation) 제품 페이지는 여섯 수준과 2026년 9월 개정 이력을 표시합니다.

## 예시 데이터

초기 그래프는 **가상 캠퍼스 셔틀** 구성입니다. 차량 1대, 기능 1개, 자동화 수준 용어 6개, ODD 1개, 센서 4개, 모듈 7개, 지도·경로·궤적 각 1개, 시나리오 2개, 도로 행위자 4개, 안전 기능 개념 2개, 미실행 시험 계획 1개, 출처 6개를 연결합니다.

ODD의 캠퍼스·건조·낮·최고 20 km/h 조건과 센서·모듈·시나리오 값은 **합성 학습 자료**입니다. 테스트 상태는 `planned`, 결과는 `not_run`입니다. 실제 차량 제어, 시뮬레이터 실행, 도로 시험, 주행 성능, SAE 수준 판정 또는 안전 검증을 의미하지 않습니다.

## 공식 참고 문서

- [SAE J3016](https://saemobilus.sae.org/standards/j3016_202104-taxonomy-definitions-terms-related-driving-automation-systems-road-motor-vehicles?tabType=viewannotation): 온로드 주행 자동화 수준 분류와 최신 개정 이력
- [NHTSA Automated Driving Systems](https://www.nhtsa.gov/vehicle-manufacturers/automated-driving-systems): 시스템 안전, ODD, 객체·사건 감지 및 대응, fallback 등 ADS 안전 요소
- [NHTSA testable cases and scenarios](https://www.nhtsa.gov/sites/nhtsa.gov/files/documents/13882-automateddrivingsystems_092618_v1a_tag.pdf): ODD의 도로 유형·속도 범위·조명·날씨 같은 속성
- [Autoware autonomous driving stack](https://autowarefoundation.github.io/autoware-documentation/1.5.0/design/autoware-architecture-v2/roadmap/autonomous-driving-stack-architecture/): 인지·위치추정·계획·궤적 생성 모듈 구조와 진화 중인 E2E 로드맵
- [Autoware Vehicle Interface](https://autowarefoundation.github.io/autoware-documentation/latest/design/autoware-architecture/vehicle/): 차량별 명령 변환과 차량 상태 수신
- [AWSIM Labs](https://autowarefoundation.github.io/AWSIM-Labs/main/Introduction/AWSIM/): 다양한 센서 구성과 시나리오에서 인지·계획·제어를 시험하는 시뮬레이터

각 출처의 URI, 확인 날짜와 뒷받침 범위는 `DocumentationSource` 인스턴스로도 저장했습니다. 링크 문서는 업데이트될 수 있습니다.

## URI 및 검증 상태

네임스페이스 `https://example.org/ontology/custom/autonomous-driving#`는 개발용이며 프로필은 `draft: true`입니다. 영구 공개 URI는 별도로 정하기 전까지 릴리스 주소로 취급하지 않습니다.

등록 과정의 기본 데이터·RDFS 확장 SHACL 검증과 질문 SPARQL 문법 파싱 결과는 [등록·검증 보고서](reports/autonomous-driving-ontology.md)에 있습니다. 탐색 질의 결과·정답 비교, 소비자 호환 사례, 자동 테스트와 브라우저 시각 검토는 수행하지 않았습니다.
