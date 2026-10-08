# ROS 2 시스템 온톨로지

검색 가능한 온톨로지 목록에서 **ROS 2 시스템 온톨로지 (ros2)** 를 선택합니다. 로컬 스튜디오 주소는 [http://127.0.0.1:5000/?ont=ros2](http://127.0.0.1:5000/?ont=ros2)입니다.

## 범위

ROS 2 응용의 구성요소와 통신 관계를 한 그래프로 연결합니다. 0.1.0 초안에는 13개 클래스, 71개 속성, 40개 인스턴스, 10개 탐색 질문이 있습니다.

- 시스템, 패키지, 노드와 사용자 정의/표준 인터페이스 형식
- 토픽, 서비스, 액션과 발행자·구독자·서버·클라이언트
- QoS 이력·깊이·신뢰성·지속성 정책
- 하드웨어 구성요소, 상태·명령 인터페이스와 컨트롤러
- tf2 좌표 프레임과 부모 관계
- 개념 및 예시 주장을 직접 뒷받침하는 문서 출처

## 학습용 예시

초기 그래프는 **가상 온실 계측·관수 시스템**입니다. 9개 패키지, 4개 노드, 2개 토픽, 1개 서비스, 1개 액션, 3개 QoS 프로파일, 3개 하드웨어 구성요소, 1개 컨트롤러와 4개 좌표 프레임이 연결되어 있습니다.

온도 형식 `sensor_msgs/msg/Temperature`와 `std_srvs/srv/SetBool` 서비스는 공식 인터페이스 출처를 기록합니다. `farm_interfaces/msg/SoilMoisture`, `farm_interfaces/action/IrrigationCycle`, 온실 노드, 펌프 배선 및 컨트롤러는 **설명용 합성 예시**입니다. 실제 온실 배포, 하드웨어 회로, 동작 시험이나 안전 검증을 의미하지 않습니다. ROS 2 일반 개념에 관한 설명과 이 가상 구성의 값을 구분하려면 각 인스턴스의 출처·설명 속성을 확인하세요.

## 공식 참고 문서

- [Topics, Services, Actions](https://github.com/ros2/ros2_documentation/blob/rolling/source/ROS-Framework/Interfaces-Topics-Services-Actions.rst): 토픽의 비동기 스트림, 서비스의 요청·응답, 액션의 목표·피드백·취소·결과
- [Quality of Service settings](https://github.com/ros2/ros2_documentation/blob/rolling/source/ROS-Framework/interfaces/topics/About-Quality-of-Service-Settings.rst): 정책 조합과 엔드포인트 QoS 호환성
- [rclcpp QoS definitions](https://github.com/ros2/rclcpp/blob/rolling/rclcpp/include/rclcpp/qos.hpp): `SensorDataQoS`와 `ServicesQoS` 프로파일 값
- [tf2](https://github.com/ros2/ros2_documentation/blob/rolling/source/ROS-Framework/interfaces/About-Tf2/About-Tf2.rst): 시간에 따라 관리되는 좌표 프레임 관계
- [ros2_control Getting Started](https://control.ros.org/rolling/doc/getting_started/getting_started.html): Controller Manager와 하드웨어 읽기·컨트롤러 갱신·명령 쓰기 흐름
- [sensor_msgs README](https://github.com/ros2/common_interfaces/blob/rolling/sensor_msgs/README.md) 및 [SetBool.srv](https://github.com/ros2/common_interfaces/blob/rolling/std_srvs/srv/SetBool.srv): 예시에서 쓰는 표준 형식

출처 URL과 이 온톨로지에서 뒷받침하는 주장은 `DocumentationSource` 인스턴스에도 저장됩니다. 확인일은 2026-10-07이며, 링크의 `rolling` 문서는 변경될 수 있습니다.

## URI 상태

네임스페이스 `https://example.org/ontology/custom/ros2#`와 프로필은 개발용 초안(`draft: true`)입니다. 조직이 통제하는 영구 URI로 이전하기 전에는 공개 배포용으로 취급하지 않습니다.

## 검증 기록

등록 과정에서 입력 그래프의 기본/RDFS 확장 SHACL 검증을 수행하고, 10개 SPARQL 질문의 문법을 파싱합니다. 질문 정답 비교, 호환성 소비 사례 실행, 자동 테스트와 브라우저 시각 확인은 이 작업에서 수행하지 않았습니다. 실제 실행 상태는 스튜디오의 노드·토픽 목록이나 이 가상 예시로부터 추론할 수 없습니다. 자세한 등록 기록은 [ROS 2 온톨로지 보고서](reports/ros2-ontology.md)를 확인하세요.
