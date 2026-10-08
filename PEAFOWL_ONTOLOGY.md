# 공작류 (Peacock / Peafowl) 온톨로지

이 문서는 웹 스튜디오에서 peafowl로 선택하는 온톨로지 초안 0.1.0을 설명한다. peacock이 보통 수컷을 가리키는 명칭이라는 점을 반영해 수컷·암컷·어린 개체 용어를 각각 모델링하고, 형태와 행동 설명을 종·성별 범위 및 출처 근거에 연결한다.

## 모델 범위

현재 예시는 인도공작 (*Pavo cristatus*)과 녹색공작 (*Pavo muticus*) 두 종이다. Aves–Galliformes–Phasianidae–Pavo–species의 분류 연결을 기록한다. 이 목록은 공작류의 완전한 분류 목록이 아니다.

12개 클래스와 59개 속성은 다음 개념을 다룬다.

- 분류군과 공작류 종
- 수컷 공작(peacock), 암컷 공작(peahen), 어린 공작(peachick)
- 꼬리덮깃 train, ocelli 눈무늬, 종별 색과 성별 차이
- 구애 전시, lek, 땅 위 먹이 찾기, 걷기·달리기
- 종별 서식·분포와 먹이 항목
- 출처별 산란 수와 포란 기간
- 출처 문서, 개별 주장 근거, 프로필 범위 메모

## 출처와 수치

두 동물원 종 정보 페이지를 2026-10-08에 확인했다. 개별 EvidenceRecord에는 출처, 페이지 위치, 주장의 적용 범위와 상태를 기록했다.

- [Smithsonian National Zoo: Common peafowl](https://nationalzoo.si.edu/animals/common-peafowl) — *Pavo cristatus* 분류, 성별에 따른 형태, 서식지·먹이·사회 행동과 번식 설명을 제공한다.
- [San Diego Zoo: Peafowl](https://animals.sandiegozoo.org/animals/peafowl) — 두 *Pavo* 종, 공작·암컷·새끼 명칭, train과 ocelli, 종별 외형·분포와 번식 설명을 제공한다.

이 자료들은 산란 수를 각각 4–8개와 3–8개로, 포란 기간을 약 30일과 26–30일로 기재한다. 데이터는 각 값을 해당 출처에 그대로 연결하며 하나의 보편값을 추론하지 않는다. 샌디에이고 동물원 페이지의 일반 번식 수치는 특정 종이나 개체군의 추정치로 표시하지 않았다.

## 파일

custom-ontologies/peafowl/에 schema.ttl, 동일한 RDF/XML 표현인 schema.owl, SHACL shapes.ttl, 출처가 연결된 example.ttl, 질문과 예시 데이터, 응답 계약 및 소비자 사례를 저장했다. curated-data.json은 RDF를 만든 큐레이션 자료를 보존한다.

12개 역량 질문은 분류, 성별 용어, train과 눈무늬, 성별 외형 차이, 분포·서식, 먹이, 행동, 번식 수치, 출처 범위, 근거 기록과 초안의 한계를 묻는다. SPARQL 문법과 RDF 파일을 파싱했지만, 질문을 실제로 실행하거나 답 계약과 대조하지는 않았다.

## 제한 사항

- 보전 등급과 법적 보호 상태는 전문 보전 평가 출처로 검증하지 않아 포함하지 않았다.
- 야생 개체군, 동물원 개체 이력, 개별 관찰 자료는 없다. 예시의 생물학 정보는 출처 페이지에 기록된 종 설명이다.
- 도메인 전문가 검토와 브라우저 시각 검수는 하지 않았다.
- 공개 URI가 정해지지 않아 example.org 개발 URI를 사용하고 draft: true로 유지한다.

파일별 검증 지표와 스튜디오 확인 결과는 [등록 보고서](reports/peafowl-ontology.md)와 [기계 판독 보고서](reports/peafowl-ontology.json)에 기록한다.
