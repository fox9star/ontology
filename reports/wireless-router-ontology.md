# 무선공유기 온톨로지 등록 기록

- 프로필 `wireless-router` v0.1.0 초안을 로컬 카탈로그에 등록했다.
- 스키마: 16 클래스, 137 속성; 질문 12개.
- 합성 예시: 22개 인스턴스, 230개 트리플.
- SHACL 입력 검증: conforms=True, raw=True, RDFS-expanded=True; 결과 수 raw=0, expanded=0.
- SPARQL 질문 12개 문법 파싱 완료. 질문 결과 비교, 소비자 케이스 실행, 자동화 테스트, 브라우저 시각 검토는 하지 않았다.
- 로컬 스튜디오: 카탈로그 29개, 탐색기 {'classes': 16, 'properties': 137, 'instances': 22}, 질문 템플릿 12개, 선택기 페이지 HTTP 200 (옵션 존재=True).
- 릴리스 URI는 미정이며 네임스페이스는 `example.org` 초안으로 남아 있다.
- 예시는 가상 구성 계획만 포함한다. 비밀번호·관리자 자격 증명·실제 SSID·MAC·IP·일련번호를 포함하지 않는다.
- 근거: [NIST SP 800-153](https://csrc.nist.gov/pubs/sp/800/153/final), WLAN의 수명주기 보안 구성과 모니터링 지침. 문서가 합성 예시 장치의 동작을 검증하지는 않는다.
