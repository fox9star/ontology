# 무선공유기 온톨로지 질문 목록

이 질문은 기록된 사실·계획·관측되지 않은 상태를 분리한다. 기본 예시는 합성 데이터이며 실제 장치와 연결되어 있지 않다.

### WR-01. 시스템에 어떤 장치·무선망·상위 연결이 기록되어 있고, 실제 관측 자료인지 합성 자료인지?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?system ?recordStatus ?device ?deviceStatus ?network ?networkStatus ?uplink ?uplinkStatus WHERE { ?system a wr:RouterSystem; wr:systemRecordStatus ?recordStatus; wr:systemHasDevice ?device; wr:systemHasNetwork ?network; wr:systemHasUplink ?uplink. ?device wr:deviceObservationStatus ?deviceStatus. ?network wr:networkLifecycleStatus ?networkStatus. ?uplink wr:uplinkConnectionStatus ?uplinkStatus. } ORDER BY ?network
~~~

### WR-02. 무선 대역·지원 표준 주장과 현재 설정 상태는 각각 무엇이며 어떤 근거가 있는가?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?radio ?band ?standard ?evidence ?configured WHERE { ?radio a wr:RadioInterface; wr:radioBand ?band; wr:radioSupportedStandard ?standard; wr:radioCapabilityEvidenceStatus ?evidence; wr:radioConfiguredState ?configured. } ORDER BY ?band
~~~

### WR-03. 실제 SSID 없이 어떤 무선망 별칭·용도·식별자 처리 상태가 기록되는가?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?network ?alias ?purpose ?identifierHandling ?lifecycle WHERE { ?network a wr:WirelessNetwork; wr:networkProfileAlias ?alias; wr:networkPurpose ?purpose; wr:networkIdentifierHandling ?identifierHandling; wr:networkLifecycleStatus ?lifecycle. } ORDER BY ?alias
~~~

### WR-04. 보안 프로토콜 표기와 적용 상태는 무엇이며 자격 증명은 어떻게 처리되는가?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?profile ?protocol ?state ?certification ?credentialHandling WHERE { ?profile a wr:SecurityProfile; wr:securityProtocolLabel ?protocol; wr:securityConfigurationStatus ?state; wr:securityCertificationClaimStatus ?certification; wr:securityCredentialHandling ?credentialHandling. } ORDER BY ?profile
~~~

### WR-05. 논리 구간과 망 분리 정책의 의도·실제 적용 상태·근거 상태는 무엇인가?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?segment ?zone ?policy ?policyState ?allowed ?denied ?evidence WHERE { ?segment a wr:NetworkSegment; wr:segmentTrustZone ?zone; wr:segmentUsesIsolationPolicy ?policy. ?policy wr:policyApplicationStatus ?policyState; wr:policyAllowedFlowScope ?allowed; wr:policyDeniedFlowScope ?denied; wr:policyEvidenceStatus ?evidence. } ORDER BY ?segment
~~~

### WR-06. 클라이언트 식별자는 어떻게 가명화되어 있으며 접속은 관측·계획·미관측 중 무엇인가?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?client ?pseudonym ?category ?identityHandling ?association ?associationStatus ?evidence WHERE { ?client a wr:ClientDevice; wr:clientPseudonym ?pseudonym; wr:clientCategory ?category; wr:clientIdentityHandling ?identityHandling; wr:clientHasAssociation ?association. ?association wr:associationStatus ?associationStatus; wr:associationEvidenceStatus ?evidence. }
~~~

### WR-07. 상위 연결의 종류, 상태, 사업자 정보 공개 및 인증 정보 처리 상태는?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?uplink ?type ?state ?providerDisclosure ?credentialHandling ?observation WHERE { ?uplink a wr:UplinkConnection; wr:uplinkConnectionType ?type; wr:uplinkConnectionStatus ?state; wr:uplinkProviderDisclosure ?providerDisclosure; wr:uplinkCredentialHandling ?credentialHandling; wr:uplinkObservationStatus ?observation. }
~~~

### WR-08. 현재 펌웨어 정보의 확실성과 업데이트 진행·재시작·롤백 상태는?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?device ?version ?support ?provenance ?update ?updateState ?reboot ?rollback WHERE { ?device a wr:RouterDevice; wr:deviceHasFirmwareRelease ?release; wr:deviceHasUpdate ?update. ?release wr:firmwareVersionLabel ?version; wr:firmwareSupportStatus ?support; wr:firmwareArtifactProvenance ?provenance. ?update wr:updateLifecycleStatus ?updateState; wr:updateRebootStatus ?reboot; wr:updateRollbackStatus ?rollback. }
~~~

### WR-09. 설정 스냅샷은 계획·적용·보관 중 어디에 있고, 비밀 제거·완전성·출처 상태는?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?snapshot ?lifecycle ?applied ?redaction ?completeness ?provenance ?summary WHERE { ?snapshot a wr:ConfigurationSnapshot; wr:snapshotLifecycleStatus ?lifecycle; wr:snapshotAppliedStatus ?applied; wr:snapshotRedactionStatus ?redaction; wr:snapshotCompletenessStatus ?completeness; wr:snapshotProvenanceStatus ?provenance; wr:snapshotChangeSummary ?summary. }
~~~

### WR-10. 성능 지표가 측정되었는가? 그렇다면 값·단위·방법·시각·표본 수는?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?observation ?metric ?status ?value ?unit ?method ?time ?samples WHERE { ?observation a wr:PerformanceObservation; wr:observationMetric ?metric; wr:observationStatus ?status; wr:observationUnit ?unit; wr:observationMethod ?method. OPTIONAL { ?observation wr:observationValue ?value } OPTIONAL { ?observation wr:observationMeasuredAt ?time } OPTIONAL { ?observation wr:observationSampleCount ?samples } } ORDER BY ?observation
~~~

### WR-11. 장애·보안 사건의 상태·분류·심각도·영향·근거 상태는?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?incident ?state ?category ?severity ?impact ?response ?evidence WHERE { ?incident a wr:IncidentRecord; wr:incidentLifecycleStatus ?state; wr:incidentCategory ?category; wr:incidentSeverity ?severity; wr:incidentImpactScope ?impact; wr:incidentResponseStatus ?response; wr:incidentEvidenceStatus ?evidence. }
~~~

### WR-12. 자료 출처가 뒷받침하는 범위와 이 예시 또는 개별 장비에 대한 한계는?

~~~sparql
PREFIX wr: <https://example.org/ontology/custom/wireless-router#>
SELECT ?source ?title ?publisher ?year ?uri ?scope ?limitations WHERE { ?source a wr:DocumentationSource; wr:sourceTitle ?title; wr:sourcePublisher ?publisher; wr:sourceYear ?year; wr:sourceUri ?uri; wr:sourceScope ?scope; wr:sourceLimitations ?limitations. } ORDER BY ?year
~~~
