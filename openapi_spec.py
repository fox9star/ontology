"""
OpenAPI 3.0 Specification Generator & Interactive Documentation Engine
Generates complete OpenAPI 3.0 schemas for the AI Agent Ontology Ecosystem.
"""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "AI Agent Ontology Ecosystem REST API",
        "description": "Comprehensive RESTful APIs for Multi-Domain Knowledge Graphs, Vis.js 2D Network Visualization, SPARQL Query Engine, Natural Language GraphRAG, PySHACL Validation, and Multi-Format Exports.",
        "version": "3.3.0",
        "contact": {
            "name": "Ontology Ecosystem Engineering Team"
        }
    },
    "servers": [
        {"url": "http://127.0.0.1:5000", "description": "Local Development Server"}
    ],
    "paths": {
        "/api/v1/ontologies": {
            "get": {"summary": "기본 및 사용자 온톨로지 검색 목록",
                    "responses": {"200": {"description": "ontologies에 코드별 프로파일 반환"}}},
            "post": {"summary": "로컬 온톨로지 초안 생성", "description": "이름과 범위로 독립된 기본 기록 모델을 생성합니다. API 키를 사용하지 않습니다.",
                     "requestBody": {"required": True, "content": {"application/json": {"schema": {
                         "type": "object", "required": ["id", "name", "description"], "properties": {
                             "id": {"type": "string", "minLength": 2, "maxLength": 48, "pattern": "^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$"},
                             "name": {"type": "string", "minLength": 1, "maxLength": 160},
                             "description": {"type": "string", "minLength": 1, "maxLength": 2000},
                             "name_en": {"type": "string", "maxLength": 160},
                             "description_en": {"type": "string", "maxLength": 2000}}}}}},
                     "responses": {"201": {"description": "key, profile, draft, message를 반환"},
                                   "400": {"description": "잘못된 입력"}, "403": {"description": "로컬 접근 정책 위반"},
                                   "409": {"description": "기존 코드 또는 저장 중 충돌"}, "413": {"description": "요청 크기 초과"}}}
        },
        "/api/v1/domains": {
            "get": {
                "summary": "도메인 목록 및 상세 메타데이터 조회",
                "description": "8개 산업 및 학술 도메인 온톨로지(mv, e2e, devops, agent, ecommerce, healthcare, academic, stock)의 스키마, 셰이프, 네임스페이스 목록을 반환합니다.",
                "responses": {
                    "200": {
                        "description": "도메인 목록 성공 반환",
                        "content": {
                            "application/json": {
                                "example": {
                                    "domains": ["mv", "e2e", "devops", "agent", "ecommerce", "healthcare", "academic", "stock"]
                                }
                            }
                        }
                    }
                }
            }
        },
        "/api/v1/metrics": {
            "get": {
                "summary": "전체 지식 그래프 실시간 메트릭",
                "description": "전체 도메인의 트리플 총합, 클래스/속성/인스턴스 분포, SPARQL 평균 응답속도(ms) 및 SHACL 검증 이력을 반환합니다.",
                "responses": {
                    "200": {
                        "description": "메트릭 통계 성공 반환"
                    }
                }
            }
        },
        "/api/v1/validate-all": {
            "get": {
                "summary": "7개 온톨로지 프로파일 SHACL 일괄 검증",
                "description": "모든 도메인에 대해 PySHACL 제약조건 검증을 일괄 실행하고 통과 여부 및 소요시간을 기록합니다.",
                "responses": {
                    "200": {"description": "검증 완료 및 결과 요약"}
                }
            }
        },
        "/api/v1/export": {
            "get": {
                "summary": "온톨로지 그래프 다중 포맷 직렬화 및 다운로드",
                "description": "선택된 도메인/프로젝트의 온톨로지 지식 그래프를 Turtle, JSON-LD, RDF/XML, N-Triples 표준 형식으로 직렬화하여 반환하거나 파일로 즉시 다운로드합니다.",
                "parameters": [
                    {"name": "ont", "in": "query", "required": False, "schema": {"type": "string", "default": "mv"}},
                    {"name": "project", "in": "query", "required": False, "schema": {"type": "string"}},
                    {"name": "format", "in": "query", "required": False, "schema": {"type": "string", "enum": ["turtle", "jsonld", "xml", "nt"], "default": "turtle"}},
                    {"name": "download", "in": "query", "required": False, "schema": {"type": "string", "enum": ["0", "1"], "default": "0"}}
                ],
                "responses": {
                    "200": {"description": "직렬화된 RDF 텍스트 또는 다운로드 파일"}
                }
            }
        },
        "/api/graph-data": {
            "get": {
                "summary": "Vis.js 2D 인터랙티브 네트워크 노드 및 엣지 데이터",
                "description": "Vis.js Network 시각화 캔버스에 바인딩할 의미론적 그룹별 노드(Agent, Task, Asset 등)와 엣지 데이터를 반환합니다.",
                "parameters": [
                    {"name": "ont", "in": "query", "required": False, "schema": {"type": "string", "default": "mv"}},
                    {"name": "project", "in": "query", "required": False, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {"description": "노드 및 엣지 배열"}
                }
            }
        },
        "/api/sparql": {
            "post": {
                "summary": "W3C 표준 대화형 SPARQL 질의 실행",
                "description": "클라이언트가 전송한 SPARQL SELECT 질의문을 지정된 온톨로지 그래프에 대해 실행하고 결과 테이블을 반환합니다.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "ont": {"type": "string", "example": "mv"},
                                    "query": {"type": "string", "example": "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 10"}
                                },
                                "required": ["query"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "질의 결과 행 및 변수 목록"}
                }
            }
        },
        "/api/v1/nl-query": {
            "post": {
                "summary": "자연어 기반 SPARQL 자동 질의 (NL-to-SPARQL / GraphRAG)",
                "description": "한국어 또는 영어 자연어 질문을 입력받아 온톨로지 스키마에 맞는 SPARQL을 자동 추론 및 실행하고 자연어 요약 답변을 반환합니다.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "ont": {"type": "string", "example": "mv"},
                                    "question": {"type": "string", "example": "보컬 추출이 완료된 작업과 담당 에이전트를 알려줘"}
                                },
                                "required": ["question"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "자연어 답변, 생성된 SPARQL 및 원시 행 데이터"}
                }
            }
        },
        "/api/v1/instances": {
            "post": {
                "summary": "신규 온톨로지 개체(인스턴스) 등록 및 실시간 SHACL 검증",
                "description": "선택한 온톨로지에 정의된 클래스와 사용 중인 편집 가능 속성으로 새 인스턴스를 만들고 SHACL·등록 미디어 검증 후 원자적으로 저장합니다. 프로젝트 미디어는 해시·출처를 기록하는 미디어 등록 도구로 추가합니다.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "ont": {"type": "string", "example": "mv"},
                                    "class_uri": {"type": "string", "example": "https://example.org/mv#Agent"},
                                    "label": {"type": "string", "example": "새로운 이미지 생성 에이전트"},
                                    "properties": {"type": "object"}
                                },
                                "required": ["class_uri", "label"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "인스턴스 생성 성공 여부 및 SHACL 검증 리포트"}
                }
            },
            "delete": {
                "summary": "온톨로지 인스턴스 삭제",
                "description": "선택한 데이터에 있는 실제 인스턴스만 삭제합니다. 스키마 정의를 대상으로 삼거나 출처·미디어·등록 프로젝트 보호 관계를 제거하는 요청은 거부합니다.",
                "parameters": [
                    {"name": "ont", "in": "query", "required": True, "schema": {"type": "string"}},
                    {"name": "uri", "in": "query", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {"description": "삭제 성공 여부 및 제거된 트리플 수"},
                    "403": {"description": "대상이 보호된 관계에 연결되어 있어 삭제할 수 없음"},
                    "422": {"description": "대상이 선택한 그래프의 실제 인스턴스가 아님"}
                }
            }
        },
        "/api/v1/simulate": {
            "post": {
                "summary": "멀티 에이전트 파이프라인 단계별 시뮬레이션",
                "description": "기획, 프롬프트, 음원, 자막, 비디오 확산, 품질 검증의 6단계 멀티 에이전트 워크플로우를 단계별로 가상 실행하고 PROV-O 온톨로지 트리플을 반환합니다.",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "step": {"type": "integer", "minimum": 1, "maximum": 6, "example": 1},
                                    "session_id": {"type": "string", "example": "sim001"}
                                },
                                "required": ["step"]
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "시뮬레이션 단계 결과, 발생된 노드/엣지 및 RDF 서술"}
                }
            }
        },
        "/api/v1/fuseki/status": {
            "get": {
                "summary": "Apache Jena Fuseki 연결 상태 점검",
                "description": "원격 Apache Jena Fuseki SPARQL triplestore 서버와의 연결 가용성 및 핑 레이턴시를 확인합니다.",
                "responses": {
                    "200": {"description": "연결 상태 및 응답 지연 시간(ms)"}
                }
            }
        },
        "/api/v1/fuseki/sync": {
            "post": {
                "summary": "온톨로지 그래프 Fuseki 실시간 동기화",
                "description": "로컬 온톨로지 도메인 또는 전체 도메인을 원격 Apache Jena Fuseki의 Named Graph로 즉시 동기화합니다.",
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "ont": {"type": "string", "example": "mv"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "동기화 성공 및 반영된 트리플 수"}
                }
            }
        },
        "/api/v1/recommend-similar": {
            "get": {
                "summary": "지식 그래프 기반 유사 개체(인스턴스) 추천",
                "description": "그래프 토폴로지 및 속성 임베딩 벡터의 코사인 유사도를 계산하여 대상 개체와 가장 유사한 TOP 3 개체를 추천합니다.",
                "parameters": [
                    {"name": "ont", "in": "query", "required": False, "schema": {"type": "string", "default": "mv"}},
                    {"name": "uri", "in": "query", "required": True, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {"description": "추천 유사 개체 목록 및 유사도 점수"}
                }
            }
        },
        "/api/v1/audit-report": {
            "get": {
                "summary": "기록된 W3C PROV-O 출처 보고서 (HTML)",
                "description": "RDF에 기록된 출처와 미확인 정보를 출력합니다. 외부 인증이나 품질 판정은 제공하지 않습니다.",
                "parameters": [
                    {"name": "ont", "in": "query", "required": False, "schema": {"type": "string", "default": "mv"}},
                    {"name": "project", "in": "query", "required": False, "schema": {"type": "string"}}
                ],
                "responses": {
                    "200": {"description": "인쇄용 출처 증명서 HTML 문서"}
                }
            }
        },
        "/api/v1/cross-domain/align": {
            "get": {
                "summary": "크로스 도메인 온톨로지 연계 및 교차 추론",
                "description": "MV, 전자상거래, DevOps, 에이전트, 헬스케어 도메인을 의미론적으로 연결하고 교차 추론된 관계 트리플을 도출합니다.",
                "responses": {
                    "200": {"description": "융합 그래프 통계 및 추론된 연결 관계"}
                }
            }
        }
    }
}

# Key-free local routes: every request is protected by the loopback/Host/Origin boundary.
OPENAPI_SPEC['info']['description'] += ' Local single-user studio. Codex jobs use saved ChatGPT authentication, without model API keys. Academic has no SHACL rules.'
_scope = [
    {'name': 'ont', 'in': 'query', 'schema': {'type': 'string', 'default': 'mv'}},
    {'name': 'project', 'in': 'query', 'schema': {'type': 'string'}, 'description': 'Omit or use empty for the global example; otherwise select this project only.'},
]
_job = {'type': 'object', 'properties': {
    'ont': {'type': 'string', 'default': 'mv'}, 'project': {'type': 'string', 'nullable': True},
    'prompt': {'type': 'string', 'minLength': 1, 'maxLength': 20000},
    'agent_name': {'type': 'string'}, 'task_name': {'type': 'string'},
    'save_to_graph': {'type': 'boolean', 'default': True}}, 'required': ['prompt']}
_body = lambda schema: {'required': True, 'content': {'application/json': {'schema': schema}}}
_responses = {'200': {'description': 'Recorded state'}, '400': {'description': 'Invalid input'}, '403': {'description': 'Trusted local request required'}}
OPENAPI_SPEC['paths'].update({
    '/api/health': {'get': {'summary': 'Local service readiness', 'responses': _responses}},
    '/api/v1/codex/status': {'get': {'summary': 'Codex CLI and ChatGPT login availability', 'responses': _responses}},
    '/api/v1/codex/jobs': {
        'get': {'summary': 'List durable Codex jobs', 'parameters': _scope, 'responses': _responses},
        'post': {'summary': 'Queue an actual Codex text task', 'requestBody': _body(_job), 'responses': {
            '202': {'description': 'Saved job; awaiting/running does not mean generated'},
            '400': {'description': 'Invalid request'}, '403': {'description': 'Trusted local request required'}}}},
    '/api/v1/codex/jobs/{job_id}': {'get': {'summary': 'Reload saved request, state and actual output',
        'parameters': [{'name': 'job_id', 'in': 'path', 'required': True, 'schema': {'type': 'string', 'pattern': '^codex_[0-9a-f]{32}$'}}],
        'responses': {**_responses, '404': {'description': 'Job not found'}}}},
    '/api/v1/codex/jobs/{job_id}/run': {'post': {'summary': 'Run an awaiting job using host Codex CLI',
        'description': 'CLI absent or not logged in: started=false and request remains awaiting. No automatic resubmission of failed/running work.',
        'parameters': [{'name': 'job_id', 'in': 'path', 'required': True, 'schema': {'type': 'string'}}],
        'responses': {'202': {'description': 'Worker availability and saved job state'}, '409': {'description': 'Job is not awaiting'}}}},
    '/api/v1/snapshots': {'get': {'summary': 'List snapshots of the selected domain and project', 'parameters': _scope, 'responses': _responses}},
    '/api/v1/snapshots/create': {'post': {'summary': 'Capture validated data only (schema excluded)',
        'requestBody': _body({'type': 'object', 'properties': {'ont': {'type': 'string'}, 'project': {'type': 'string', 'nullable': True}, 'description': {'type': 'string'}}}),
        'responses': {**_responses, '422': {'description': 'SHACL or registered-file validation failed'}}}},
    '/api/v1/snapshots/rollback': {'post': {'summary': 'Validate scoped snapshot and persist an atomic rollback',
        'description': 'Checks SHA-256, exact domain/project, SHACL and registered assets. Legacy snapshots cannot be restored.',
        'requestBody': _body({'type': 'object', 'properties': {'ont': {'type': 'string'}, 'project': {'type': 'string', 'nullable': True}, 'snapshot_id': {'type': 'string'}}, 'required': ['snapshot_id']}),
        'responses': {**_responses, '422': {'description': 'Validation failed; original data preserved'}}}},
    '/api/v1/snapshots/diff': {'get': {'summary': 'Semantic data diff in one domain/project scope',
        'parameters': _scope + [{'name': 'snapshot_a', 'in': 'query', 'required': True, 'schema': {'type': 'string'}}, {'name': 'snapshot_b', 'in': 'query', 'schema': {'type': 'string'}}], 'responses': _responses}},
    '/api/v1/reasoning/expand': {'post': {'summary': 'Preview OWL-RL/RDFS closure without persisting inference',
        'requestBody': _body({'type': 'object', 'properties': {'ont': {'type': 'string'}, 'project': {'type': 'string'}, 'semantics': {'type': 'string', 'enum': ['owlrl', 'rdfs']}}}), 'responses': _responses}},
    '/api/v1/auth/identity': {'get': {'summary': 'Trusted local owner identity (single user)', 'responses': _responses}},
    '/api/v1/auth/audit-logs': {'get': {'summary': 'Persistent tamper-evident audit events', 'responses': _responses}},
    '/api/v1/auth/audit-integrity': {'get': {'summary': 'Verify the local audit hash chain', 'responses': _responses}},
    '/api/v1/healthcare/fhir-bundle': {'get': {
        'summary': 'Export synthetic healthcare data as a FHIR R5 collection Bundle',
        'parameters': [{'name': 'project', 'in': 'query', 'required': False,
                       'schema': {'type': 'string'}}],
        'responses': {'200': {'description': 'Privacy-filtered FHIR R5 application/fhir+json Bundle'},
                      '403': {'description': 'Trusted local request required'},
                      '500': {'description': 'FHIR structural validation failed'}}}},
})
OPENAPI_SPEC['paths']['/api/v1/llm/status'] = OPENAPI_SPEC['paths']['/api/v1/codex/status']
OPENAPI_SPEC['paths']['/api/v1/llm/generate'] = {'post': {**OPENAPI_SPEC['paths']['/api/v1/codex/jobs']['post'], 'deprecated': True}}

# Instance-focused exploration and validated relation editing.
OPENAPI_SPEC['info']['version'] = '3.3.0'
_inference_parameter = {'name': 'inference', 'in': 'query', 'schema': {'type': 'string', 'enum': ['none', 'rdfs', 'owlrl'], 'default': 'none'},
                        'description': 'Read-only preview; inferred relationships are never persisted by this route.'}
OPENAPI_SPEC['paths']['/api/graph-data']['get'].update({
    'summary': 'Explore instances in one domain/project without schema nodes',
    'description': 'Returns stable URI nodes, hashed edge IDs, actual types, degree counts, predicate/group catalogs and protected editing flags. Schema declarations are excluded. The response is capped at 1,000 nodes and 10,000 visible edges; truncated indicates a partial download.',
    'parameters': _scope + [_inference_parameter,
        {'name': 'include_external', 'in': 'query', 'schema': {'type': 'string', 'enum': ['0', '1'], 'default': '0'}},
        {'name': 'limit', 'in': 'query', 'schema': {'type': 'integer', 'minimum': 1, 'maximum': 1000, 'default': 500}}],
})
OPENAPI_SPEC['paths']['/api/instance-detail'] = {'get': {
    'summary': 'Inspect literals and incoming/outgoing instance relationships',
    'parameters': _scope + [_inference_parameter, {'name': 'uri', 'in': 'query', 'required': True, 'schema': {'type': 'string'}}],
    'responses': {**_responses, '404': {'description': 'Instance is not present or referenced in the selected data'}}}}
_relation_schema = {'type': 'object', 'properties': {
    'ont': {'type': 'string', 'default': 'mv'}, 'project': {'type': 'string', 'nullable': True},
    'subject': {'type': 'string', 'format': 'uri'}, 'predicate': {'type': 'string', 'format': 'uri'},
    'object': {'type': 'string', 'format': 'uri'}}, 'required': ['subject', 'predicate', 'object']}
_relation_operation = {
    'description': 'Only cataloged object predicates between existing instances in the selected scope can be edited. Provenance attribution and registered-media structural relationships are protected. Candidate SHACL/media validation precedes a scoped data snapshot and atomic write. Duplicate additions and missing deletions do not write.',
    'requestBody': _body(_relation_schema),
    'responses': {**_responses, '422': {'description': 'Candidate validation failed; source data unchanged'}}}
OPENAPI_SPEC['paths']['/api/v1/relations'] = {
    'post': {**_relation_operation, 'summary': 'Add a validated instance relationship'},
    'delete': {**_relation_operation, 'summary': 'Remove a validated instance relationship'},
}

# Cognitive, Frontier, Singular, and Transcendent Cognitive API Specifications
OPENAPI_SPEC['info']['version'] = '6.0.0'
cognitive_routes = {
    '/api/v2/causal/what-if': {'post': {'summary': 'Causal SCM What-If Simulation'}},
    '/api/v2/evolver/mine-and-verify': {'post': {'summary': 'Self-Evolving Neuro-Symbolic Loop'}},
    '/api/v2/kge/verify-axiom': {'post': {'summary': 'Geometric Box KGE Zero-Hallucination Verification'}},
    '/api/v2/arbiter/arbitrate': {'post': {'summary': 'Multi-Agent Semantic Court'}},
    '/api/v2/temporal/snapshot': {'get': {'summary': '4D Fluents Point-in-Time Snapshot'}},
    '/api/v3/distill/dataset': {'get': {'summary': 'Axiom-to-LoRA Synthetic Dataset Generator'}},
    '/api/v3/aesthetic/tension-curve': {'get': {'summary': 'Neuro-Aesthetic Tension Curve'}},
    '/api/v3/probabilistic/infer': {'post': {'summary': 'Probabilistic Soft Logic (PSL) Inference'}},
    '/api/v4/wormhole/teleport': {'post': {'summary': 'Category-Theoretic Semantic Wormhole'}},
    '/api/v4/zk/prove-and-verify': {'post': {'summary': 'Zero-Knowledge Knowledge Graph Verification'}},
    '/api/v4/quantum/superposition': {'get': {'summary': 'Quantum Cognitive Superposition'}},
    '/api/v4/quantum/collapse': {'post': {'summary': 'Quantum Wavefunction Measurement Collapse'}},
    '/api/v4/immune/scan-and-heal': {'post': {'summary': 'Autonomous Semantic Immune Defense'}},
    '/api/v5/spatial/simulate': {'post': {'summary': '3D Spatial & Physical World-Model Simulation'}},
    '/api/v5/multiverse/mcts-search': {'post': {'summary': 'Multiverse MCTS Golden Path Search'}},
    '/api/v5/darwin/evolve': {'post': {'summary': 'Darwinian Schema Genetic Evolution'}},
    '/api/v5/neurobio/resonate': {'post': {'summary': 'Neuro-Bio Adaptive Resonance'}},
    '/api/v6/hdc/query': {'post': {'summary': 'Hyperdimensional Vector Symbolic Architecture O(1) Holographic Query'}},
    '/api/v6/active-inference/evaluate': {'post': {'summary': 'Active Inference Variational Free Energy Minimization & Epistemic Probes'}},
    '/api/v6/autopoiesis/repair': {'post': {'summary': 'Autopoietic Self-Compiling Quine Ontology Regeneration'}},
    '/api/v6/crdt-swarm/sync': {'post': {'summary': 'Decentralized Byzantine Semantic CRDT Swarm Consensus'}},
    '/api/v7/tda/persistent-homology': {'post': {'summary': 'Topological Data Analysis (TDA) & Persistent Homology Filtration'}},
    '/api/v7/neuromorphic/simulate-spikes': {'post': {'summary': 'Neuromorphic Spiking Neural Network & STDP Plasticity'}},
    '/api/v7/neural-ode/integrate': {'post': {'summary': 'Continuous-Time Neural ODE RK4 Trajectory Integration'}},
    '/api/v7/gauge/holonomy': {'post': {'summary': 'Gauge-Theoretic Fiber Bundle & Semantic Holonomy Curvature'}},
    '/api/v8/poincare/embed-and-distance': {'post': {'summary': 'Poincare Ball Hyperbolic Embedding & Geodesic Horosphere Depth'}},
    '/api/v8/sgwt/wavelet-transform': {'post': {'summary': 'Spectral Graph Wavelet Transform & Multiresolution Analysis'}},
    '/api/v8/free-monad/compose-and-execute': {'post': {'summary': 'Category-Theoretic Free Monad Composition & Reversible Execution'}},
    '/api/v8/transfinite/dissolve-paradox': {'post': {'summary': 'Transfinite Ordinal Metacognition & Godelian Paradox Dissolution'}},
}
OPENAPI_SPEC['info']['version'] = '8.0.0'
for path, spec in cognitive_routes.items():
    OPENAPI_SPEC['paths'][path] = spec
