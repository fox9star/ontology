# 전기기능사 자격·시험 온톨로지 (`electricity-craftsman`)

## 목적과 범위

전기기능사의 자격 식별정보, 필기·실기 단계, 시험 과목과 작업 범위, 합격 기준, 지참 공구·안전 안내를 공식 출처와 확인 시점에 연결한다. 실제 전기 시공 절차를 가르치거나 현장 작업을 안전 검증하는 온톨로지는 아니다.

프로필은 `0.1.0` 초안이며, 릴리스 URI는 미정이다. 2026-10-08 현재 큐넷에서 확인한 정보를 출처가 연결된 스냅샷으로 기록했다. 시험 일정·요건·지참 품목은 바뀔 수 있으므로 응시 시점의 큐넷 회차별 안내를 확인해야 한다.

## 모델

- 11개 클래스, 102개 속성으로 자격, 출제기준 버전, 시험 단계, 지식 영역, 역량, 실기 과제, 평가 기준, 지참 품목, 안전 요건, 출처 문서와 근거 기록을 표현한다.
- 큐넷 종목 코드 `7780`, 관련 부처, 시행기관을 기록하고 필기(전기이론·전기기기·전기설비)와 실기(전기설비작업)를 분리한다.
- 큐넷에 게시된 필기 60문항·4지택일형, 실기 약 270분, 각 단계의 100점 중 60점 합격 기준을 출처 기록과 함께 포함한다.
- 큐넷이 공개한 실기 범위인 배관·배선공사와 시퀀스 제어회로 완성, 지참 품목 22개, 보호구·공구 제한·안전 안내를 연결한다.
- 2024-01-01~2026-12-31 출제기준은 현재 적용 버전으로 두되 상세 세부 항목은 부분 반영 상태다. 2027-01-01~2029-12-31 차기 기준은 제목·적용기간만 게시 사실을 기록하고 세부 기준은 미반영으로 표시했다.

## 출처와 근거 원칙

주요 사실은 큐넷의 [종목별 상세정보](https://www.q-net.or.kr/crf005.do?gId=&gSite=Q&id=crf00503&jmCd=7780), [시험정보·취득방법](https://www.q-net.or.kr/crf005.do?gId=&gSite=Q&id=crf00503s02&jmCd=7780&jmInfoDivCcd=B0), [출제기준 목록](https://www.q-net.or.kr/cst006.do?artlSeq=5212053&brdId=Q006&id=cst00602), [공개문제](https://www.q-net.or.kr/cst006.do?artlSeq=5208377&brdId=Q006&code=1204&id=cst00602), [수험자 지참준비물](https://www.q-net.or.kr/rcv013.do?IMPL_ID=PL2024557010&JM_CD=7780&JM_FLD_NM=%EC%A0%84%EA%B8%B0%EA%B8%B0%EB%8A%A5%EC%82%AC&SELFLD_CD=00&SERIES_CD=04&gSite=Q&id=rcv01314)에서 확인했다. 출처별로 확인일, 지지하는 사실, 적용 범위와 한계를 데이터에 기록했다.

차기 기준은 큐넷 페이지에서 적용기간만 확인했다. 첨부 원문을 읽고 구조화하기 전까지 기존 과목·평가 조건이 차기 버전에도 그대로 이어진다고 가정하지 않는다. 필기 과목의 세부 능력단위와 기술 기준도 출제기준 원문을 추출해 검토하기 전까지 포함하지 않는다.

## 검증 결과

2026-10-08 확인:

- 예시 데이터 848개 트리플, 인스턴스 58개
- SHACL 원본 데이터 및 추론 데이터 모두 적합, 결과 0건
- Turtle·OWL 스키마 그래프 일치
- 역량 질문 12개 SPARQL 문법 파싱 및 수동 답변 계약의 ID·행 구조 확인
- 로컬 카탈로그 31개 프로필에 `electricity-craftsman` 포함
- 스튜디오 탐색기: 클래스 11, 속성 102, 인스턴스 58; 질문 템플릿 `ELEC-01`–`ELEC-12`; 선택 메뉴 HTTP 200 및 프로필 옵션 확인

질문은 실행하거나 예상 답변과 대조하지 않았다. 소비자 TriG 사례도 파싱만 했고 실행하지 않았다. 자동 테스트와 브라우저 시각 검수는 하지 않았다. 자세한 확인 내역은 [등록 보고서](reports/electricity-craftsman-ontology.md)와 [JSON 보고서](reports/electricity-craftsman-ontology.json)를 참고한다.

## 파일

- [Turtle 스키마](custom-ontologies/electricity-craftsman/schema.ttl) · [OWL/RDF/XML](custom-ontologies/electricity-craftsman/schema.owl) · [SHACL](custom-ontologies/electricity-craftsman/shapes.ttl)
- [예시 그래프](custom-ontologies/electricity-craftsman/example.ttl) · [질문](custom-ontologies/electricity-craftsman/questions.md) · [답변 계약](custom-ontologies/electricity-craftsman/question-answers.json)
- [질문 fixture](custom-ontologies/electricity-craftsman/question-fixture.ttl) · [소비자 호환 예시](custom-ontologies/electricity-craftsman/consumer-cases.trig)
