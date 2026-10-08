# 모방학습 온톨로지

카탈로그 ID는 imitation-learning, 버전은 0.1.0 초안이다. 네임스페이스는 https://example.org/ontology/custom/imitation-learning#이며, 소유한 공개 URI가 정해지기 전까지 draft 상태로 유지한다.

## 모델 범위

16개 클래스와 84개 속성으로 시연 데이터부터 학습·평가 기록까지 연결한다.

- 프로젝트와 학습 과제, 시연자 또는 참조 정책
- 시연 데이터셋, 에피소드, 순서가 있는 관측·행동 레이블 단계
- 행동복제, DAgger, 역강화학습 및 정책
- 학습 실행, 평가 실행, 측정 상태를 분리한 평가 지표
- 상태 분포 변화, 안전 제약, 문헌 출처와 주장 범위

### 방법의 의미 구분

- 행동복제(behavior cloning)는 관측과 행동 쌍을 지도 신호로 사용해 정책을 근사한다. ALVINN은 카메라·레이저 입력에서 조향 출력을 학습한 초기 입력-출력 사례다.
- DAgger는 학습 정책이 방문하는 상태에서 전문가 레이블을 구하고 데이터를 반복 누적하는 접근이다. 이는 전문가 시연 분포와 학습 정책 유도 분포의 차이를 다루기 위한 구조다.
- 역강화학습(inverse RL)은 행동을 직접 레이블로 예측하기보다 관측 행동을 설명하는 보상 함수를 추론하는 문제다.

## 예시와 데이터 경계

예시 그래프에는 가상 로봇팔 집기·놓기 과제, 두 단계의 설명용 관측·행동 레이블, 미학습 정책, 계획 상태의 학습·평가 실행, 측정하지 않은 세 지표가 있다. 이 데이터는 합성 픽스처이며 실제 센서 기록, 전문가 수집, 데이터 분할, 모델 학습, 하드웨어 구동 또는 성능 측정을 나타내지 않는다. example.ttl은 온톨로지의 example.org 초안 namespace를 사용하고, competency-question fixture는 example.test namespace를 사용한다.

안전 제약은 이 픽스처를 실제 장비에 전송하지 않는다는 범위 메모다. 실제 로봇 운용 안전 검증이나 안전 인증을 주장하지 않는다.

## 탐색 질문

IL-01부터 IL-10까지 과제와 데이터 상태, 단계별 행동, 세 방법의 구분과 출처, 학습·평가 상태, 정책, 분포 변화, 안전 제약 및 문헌 주장을 탐색한다. questions.md에는 SPARQL을 두고 question-answers.json에는 기대 행을 보관한다. 등록 검증에서는 SPARQL 파싱만 수행했으며 질의를 실행하거나 결과를 golden answers와 대조하지 않았다.

## 출처

- Ross, Gordon, Bagnell, [A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning](https://proceedings.mlr.press/v15/ross11a.html), PMLR 2011.
- Ng and Russell, [Algorithms for Inverse Reinforcement Learning](https://ai.stanford.edu/~ang/papers/icml00-irl.pdf), ICML 2000.
- Pomerleau, [ALVINN: An Autonomous Land Vehicle in a Neural Network](https://publications.ri.cmu.edu/alvinn-an-autonomous-land-vehicle-in-a-neural-network), 1989.

## 검증과 남은 범위

등록 시 기본 데이터 그래프와 RDFS 확장 그래프 모두 SHACL을 통과했고, competency question 10개의 SPARQL 문법을 파싱했다. Studio API의 카탈로그, 탐색기, 질문 템플릿 및 선택 메뉴를 별도 확인했다. 질의 정답 비교, consumer compatibility 실행, 자동 테스트, 브라우저 시각 검증은 수행하지 않았다.

기계 판독 보고서: reports/imitation-learning-ontology.json.
