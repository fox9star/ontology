# 전기자동차 온톨로지

전기 구동 차량 유형과 구성품, 전력 흐름, 충전 인프라를 출처가 있는 주장과 연결하는 로컬 초안이다. 프로필 ID는 **electric-vehicle**, 버전은 **0.1.0**이며, 공개 URI는 아직 정하지 않아 example.org의 로컬 초안 네임스페이스를 사용한다.

## 범위와 구분

- **BEV**: 전기 모터로 구동하고 외부 충전 설비에 연결해 구동 배터리를 충전하는 유형.
- **PHEV**: 내연기관과 전기 구동을 함께 사용하며 외부 충전과 회생 제동 등으로 배터리를 충전하는 유형. 직렬·병렬 구성을 하나의 고정값으로 취급하지 않는다.
- **HEV**: 내연기관과 전기 모터를 함께 사용하지만 외부 전원에 꽂지 않고 회생 제동과 내연기관으로 배터리를 충전하는 유형.

미국 에너지부 자료는 이 세 유형을 전기를 사용하는 차량 범주로 설명한다. 따라서 ElectrifiedVehicle을 상위 개념으로 두고, 플러그인 가능 여부를 별도 속성으로 기록한다. 일상어의 “전기차”만으로 외부 충전 가능 여부를 추론하지 않는다.

## 모델

| 영역 | 주요 클래스와 관계 |
| --- | --- |
| 차량 유형 | Vehicle, ElectrifiedVehicle, BatteryElectricVehicle, PlugInHybridElectricVehicle, HybridElectricVehicle |
| 구동계 | TractionBatteryPack, AuxiliaryBattery, ElectricTractionMotor, PowerElectronicsController, Inverter, DCDCConverter, OnboardCharger, VehicleChargePort, ThermalManagementSystem |
| 충전 설비 | ChargingStationLocation → EVSEPort → ChargingConnector; ChargingSession은 차량·포트·커넥터·전류 유형·상태를 연결 |
| 에너지 흐름 | EnergyFlow가 출발점, 도착점, 에너지 형태와 조건을 기록. AC/DC 충전, 모터 구동, 회생 제동의 개념 경로를 포함 |
| 근거와 범위 | SourceDocument, EvidenceRecord, CoverageNote가 URL·발행자·확인일·문서 위치·주장 범위와 제외 사항을 보존 |

Schema와 SHACL은 필수 식별자·이름, 데이터 형식, 객체 범위, 제한된 유형 어휘를 검사한다. 차량 예시는 특정 상용 모델이 아닌 유형 설명용 개념 레코드다. 충전소, 포트, 커넥터, 충전 세션은 모두 합성 예시이며 실제 설비 관측값이 아니다.

## 출처와 주의

미국 에너지부 Alternative Fuels Data Center의 유형 개요, BEV/PHEV/HEV 기술 설명, 충전 인프라 용어와 미국 에너지부의 차량-전력망 통합 보고서를 사용한다. 각 근거 레코드에는 출처와 문서 위치, 적용 범위를 연결했다.

AC/DC 인터페이스 수준을 모델링하며, 특정 국가·차종의 커넥터 규격 호환성은 주장하지 않는다. 법규·요금·보조금, 차종별 배터리 용량·주행거리·효율·충전 속도·배터리 건강도 역시 포함하지 않는다. 이런 값은 지역·시점·차종·시험 조건에 맞춘 별도 근거가 필요하다.

## 파일

- 프로필 산출물: custom-ontologies/electric-vehicle 아래에 RDF/OWL 스키마, SHACL, 예시, 질문, 픽스처, 응답 계약과 소비자 사례가 있다.
- 정형 curation 데이터: custom-ontologies/electric-vehicle/curated-data.json
- [등록 및 검증 보고서](reports/electric-vehicle-ontology.md)

릴리스용 URI가 결정되면 초안 네임스페이스를 이관하고 내부·외부 참조를 함께 갱신해야 한다.
