# 전기자동차 온톨로지 등록·검증 보고서

## 결과

| 항목 | 결과 |
| --- | --- |
| 프로필 | electric-vehicle, 0.1.0, draft |
| 클래스 / 속성 | 24 / 46 |
| 자원 인스턴스 / 트리플 | 48 / 675 |
| 출처 / 근거 기록 | 6 / 11 |
| 역량 질문 / 응답 계약 | 12 / 12 |
| SHACL 원시 그래프 | 통과, 위반 0 |
| SHACL 추론 그래프 | 통과, 위반 0 |
| Turtle / RDF/XML 스키마 | 파싱 후 트리플 일치 |
| SPARQL 질문 문법 | 12개 파싱 |
| 질의 실행 및 응답 비교 | 수행하지 않음 |
| 소비자 사례 실행 / 자동화 테스트 | 수행하지 않음 |
| 브라우저 시각 검수 | 수행하지 않음 |

충전소 위치, EVSE 포트, 인터페이스 커넥터, 충전 세션은 6개의 합성 예시다. 차량 유형 기록도 실제 판매 차종이 아닌 설명용 개념 패턴이다.

## 근거 출처

- [미국 에너지부 AFDC: 전기차 유형](https://afdc.energy.gov/vehicles/electric)
- [미국 에너지부 AFDC: 배터리 전기차 작동 방식](https://afdc.energy.gov/vehicles/how-do-all-electric-cars-work)
- [미국 에너지부 AFDC: 플러그인 하이브리드 전기차](https://afdc.energy.gov/vehicles/electric-basics-phev)
- [미국 에너지부 AFDC: 하이브리드 전기차](https://afdc.energy.gov/vehicles/electric-basics-hev)
- [미국 에너지부 AFDC: 전기차 충전소와 충전 용어](https://afdc.energy.gov/fuels/electricity-stations)
- [미국 에너지부: Vehicles-to-Grid Integration Assessment Report (2025-01)](https://www.energy.gov/sites/default/files/2025-01/Vehicle_Grid_Integration_Asseessment_Report_01162025.pdf)

주장은 출처별 설명 범위를 유지한다. 수치 성능, 커넥터 표준별 호환성, 법규·인센티브는 이 초안의 범위에 포함하지 않는다.

## 스튜디오 확인

| 확인 항목 | 결과 |
| --- | --- |
| 로컬 카탈로그 | 33개 프로필 중 electric-vehicle 포함 |
| Explorer | 클래스 24, 속성 46, 인스턴스 48 |
| 질문 템플릿 | 12개, EV-01–EV-12 |
| 검색 선택기 | 항목·영문 검색 키워드 확인, HTTP 200 |
| 쿼리 실행·브라우저 시각 검수 | 수행하지 않음 |
