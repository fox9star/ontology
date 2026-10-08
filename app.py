import os
import time
import datetime
from flask import Flask, render_template, request, jsonify, send_file, url_for, Response
import rdflib
from rdflib.collection import Collection
import pyshacl
import project_store
import auth
import codex_jobs
import healthcare_privacy
import ontology_catalog
from graph_io import graph_file_lock, write_graph_atomic
from ontology_loader import (
    load_schema_graph as _parse_schema_graph,
    load_shape_graph as _parse_shape_graph,
)

app = Flask(__name__, template_folder='templates', static_folder='static')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.before_request(auth.authorize_request)
app.config["ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE"] = (
    os.environ.get("ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE", "0").strip().lower() in {"1", "true", "yes"}
)
app.config["ONTOLOGY_AUDIT_LOG_PATH"] = os.environ.get(
    "ONTOLOGY_AUDIT_LOG_PATH", os.path.join(BASE_DIR, ".runtime", "audit.jsonl")
)
app.config["ONTOLOGY_AUDIT_RETENTION_DAYS"] = os.environ.get("ONTOLOGY_AUDIT_RETENTION_DAYS", "0")

ONTOLOGIES = {
    "mv": {
        "name": "뮤직비디오 생성 AI 에이전트 온톨로지 (mv)",
        "schema": "mv-schema.ttl",
        "owl": "mv.owl",
        "shapes": "mv-shapes.ttl",
        "example": "mv-example.ttl",
        "prefix": "https://example.org/mv#",
        "version": "1.2.1"
    },
    "e2e": {
        "name": "가사·자막·번역 엔드투엔드 온톨로지 (e2e)",
        "schema": "mv-schema.ttl",
        "owl": "mv.owl",
        "shapes": "mv-shapes.ttl",
        "example": "e2e_pipeline_output.ttl",
        "prefix": "https://example.org/mv#",
        "profile_of": "mv",
        "version": "1.2.1"
    },
    "devops": {
        "name": "소프트웨어 빌드·배포 CI/CD 에이전트 온톨로지 (devops)",
        "schema": "devops-schema.ttl",
        "owl": "devops.owl",
        "shapes": "devops-shapes.ttl",
        "example": "devops-example.ttl",
        "prefix": "http://example.org/ontology/devops#",
        "version": "1.2.1"
    },
    "agent": {
        "name": "AI 에이전트 협업 온톨로지 (agent)",
        "schema": "agent-schema.ttl",
        "owl": "agent.owl",
        "shapes": "agent-shapes.ttl",
        "example": "agent-example.ttl",
        "prefix": "https://example.org/agent#",
        "version": "1.2.1"
    },
    "ecommerce": {
        "name": "전자상거래 AI 에이전트 온톨로지 (ecommerce)",
        "schema": "ecommerce-schema.ttl",
        "owl": "ecommerce.owl",
        "shapes": "ecommerce-shapes.ttl",
        "example": "ecommerce-example.ttl",
        "prefix": "http://example.org/ontology/ecommerce#",
        "version": "1.2.1"
    },
    "healthcare": {
        "name": "헬스케어 AI 에이전트 온톨로지 (healthcare)",
        "schema": "healthcare-schema.ttl",
        "owl": "healthcare.owl",
        "shapes": "healthcare-shapes.ttl",
        "example": "healthcare-example.ttl",
        "prefix": "http://example.org/ontology/healthcare#",
        "version": "1.3.1"
    },
    "academic": {
        "name": "대학 수강 예시 온톨로지",
        "schema": "academic-schema.ttl",
        "owl": "academic-schema.owl",
        "shapes": "academic-shapes.ttl",
        "example": "academic-example.ttl",
        "prefix": "https://example.org/ontology/academic#",
        "version": "1.2.1"
    },
    "stock": {
        "name": "주식투자 AI 에이전트 온톨로지 (stock)",
        "schema": "stock-schema.ttl",
        "owl": "stock.owl",
        "shapes": "stock-shapes.ttl",
        "example": "stock-example.ttl",
        "prefix": "http://example.org/ontology/stock#",
        "version": "1.0.0"
    },
    "diet": {
        "name": "체중감량 및 식이·운동 AI 에이전트 온톨로지 (diet)",
        "schema": "diet-schema.ttl",
        "owl": "diet.owl",
        "shapes": "diet-shapes.ttl",
        "example": "diet-example.ttl",
        "prefix": "http://example.org/ontology/diet#",
        "version": "1.0.0"
    },
    "camping": {
        "name": "캠핑 계획 및 야영장 관리 온톨로지 (camping)",
        "schema": "camping-schema.ttl",
        "owl": "camping.owl",
        "shapes": "camping-shapes.ttl",
        "example": "camping-example.ttl",
        "questions": "CAMPING_QUESTIONS.md",
        "prefix": "https://example.org/ontology/camping#",
        "version": "1.0.0"
    },
    "korean-war": {
        "name": "한국전쟁 역사 및 전사 분석 AI 에이전트 온톨로지 (korean-war)",
        "schema": "korean-war-schema.ttl",
        "owl": "korean-war.owl",
        "shapes": "korean-war-shapes.ttl",
        "example": "korean-war-example.ttl",
        "prefix": "http://example.org/ontology/korean-war#",
        "version": "1.0.0"
    },
    "politics": {
        "name": "정치·선거 정보 온톨로지 (politics)",
        "schema": "politics-schema.ttl",
        "owl": "politics.owl",
        "shapes": "politics-shapes.ttl",
        "example": "politics-example.ttl",
        "questions": "POLITICS_QUESTIONS.md",
        "prefix": "https://example.org/ontology/politics#",
        "version": "1.0.0"
    },
    "theme-park": {
        "name": "놀이공원 운영 및 스마트 대기 온톨로지 (theme-park)",
        "schema": "theme-park-schema.ttl",
        "owl": "theme-park.owl",
        "shapes": "theme-park-shapes.ttl",
        "example": "theme-park-example.ttl",
        "prefix": "http://example.org/ontology/theme-park#",
        "version": "1.0.0"
    }
}

def refresh_ontology_catalog():
    custom = ontology_catalog.load_custom_profiles(BASE_DIR)
    for key in custom:
        if key in ONTOLOGIES and not ONTOLOGIES[key].get('custom'):
            raise ValueError('사용자 온톨로지 ID가 기본 목록과 충돌합니다.')
    ONTOLOGIES.update(custom)
    return ONTOLOGIES


refresh_ontology_catalog()


def ontology_config(ont_key):
    if isinstance(ont_key, str) and ont_key not in ONTOLOGIES:
        refresh_ontology_catalog()
    if not isinstance(ont_key, str) or ont_key not in ONTOLOGIES:
        raise project_store.ProjectError("알 수 없는 온톨로지입니다.")
    return ONTOLOGIES[ont_key]


def load_schema_graph(ont_key):
    """Load a canonical domain schema plus its bundled local imports."""
    cfg = ontology_config(ont_key)
    return _parse_schema_graph(BASE_DIR, cfg["schema"])


def load_shape_graph(ont_key):
    """Load the profile shapes and shared core constraints."""
    cfg = ontology_config(ont_key)
    if not cfg["shapes"]:
        return rdflib.Graph()
    return _parse_shape_graph(BASE_DIR, cfg["shapes"])


def selected_data_path(ont_key, project_id=None):
    cfg = ontology_config(ont_key)
    if project_id not in (None, ''):
        project_store.load_project(project_id, ont_key)
        return str(project_store.project_file(project_id, "data.ttl"))
    return os.path.join(BASE_DIR, cfg["example"])


def load_graph(ont_key, project_id=None):
    g = rdflib.Graph()
    
    g += load_schema_graph(ont_key)
        
    example_path = selected_data_path(ont_key, project_id)
    if os.path.exists(example_path):
        fmt = "turtle" if example_path.endswith(".ttl") else "xml"
        g.parse(example_path, format=fmt)
        
    return g


def _sensitive_read_requested(payload=None):
    values = [request.args.get("include_sensitive", "")]
    if isinstance(payload, dict):
        values.append(payload.get("include_sensitive", ""))
    return any(value is True or str(value).strip().lower() in {"1", "true", "yes"} for value in values)


def _apply_read_policy(graph, ont_key, include_sensitive=False):
    """Apply response-time privacy rules without changing validation/storage data."""
    if ont_key != "healthcare":
        return graph, False
    if include_sensitive:
        if not app.config.get("ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE", False):
            raise project_store.ProjectError(
                "민감 의료 데이터 열람은 서버에서 ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE=1로 명시적으로 허용해야 합니다.",
                403,
            )
        try:
            auth.log_audit_action(
                "HEALTHCARE_SENSITIVE_READ", "local_owner", "admin", "explicit include_sensitive request"
            )
        except (OSError, ValueError):
            raise project_store.ProjectError("감사 로그를 기록할 수 없어 민감 의료 자료 열람을 거부했습니다.", 503) from None
        return graph, False
    return healthcare_privacy.redact_graph(graph), True


def _load_response_graph(ont_key, project_id=None, include_sensitive=False):
    graph = load_graph(ont_key, project_id)
    return _apply_read_policy(graph, ont_key, include_sensitive)[0]


@app.errorhandler(project_store.ProjectError)
def project_error(error):
    return jsonify({"error": str(error)}), error.status_code

@app.errorhandler(codex_jobs.JobError)
def codex_error(error):
    return jsonify({"error": str(error)}), error.status_code


def _load_data_graph(ont_key, project_id=None):
    path = selected_data_path(ont_key, project_id)
    return rdflib.Graph().parse(path, format='turtle' if path.endswith('.ttl') else 'xml')


def _validate_candidate(graph, ont_key, project_id=None):
    cfg = ontology_config(ont_key)
    supported = bool(cfg['shapes'])
    report = '이 도메인에는 SHACL shapes가 없습니다.'
    if supported:
        shapes = load_shape_graph(ont_key)
        schema = load_schema_graph(ont_key)
        from validation_pipeline import validate_phases
        phases = validate_phases(graph, schema, shapes)
        conforms, report = phases['conforms'], phases['report_text']
        if not conforms:
            details = '의료 원자료 검증 결과에 포함된 식별자와 값은 숨겼습니다.' if ont_key == 'healthcare' else report[:2000]
            raise project_store.ProjectError('SHACL 검증 실패: ' + details, 422)
    if project_id:
        checks = project_store.check_assets(project_id, graph, rdflib.Namespace(cfg['prefix']))
        if not all(item['valid'] for item in checks):
            raise project_store.ProjectError('등록 미디어 무결성 검증이 실패하여 저장하지 않았습니다.', 422)
    return {'shacl_supported': supported, 'shacl_conforms': True if supported else None, 'report': report,
            'raw_conforms': phases['raw_conforms'] if supported else None,
            'inferred_conforms': phases['inferred_conforms'] if supported else None}


@app.route('/api/health')
def api_health():
    return jsonify({'status': 'ok', 'service': 'ontology-web-studio'})

@app.route('/')
def index():
    refresh_ontology_catalog()
    return render_template('index.html', ontologies=ONTOLOGIES)

@app.route('/graph')
def graph_pulse():
    refresh_ontology_catalog()
    return render_template('graph_pulse.html', ontologies=ONTOLOGIES)

@app.route('/api/ontologies')
def api_ontologies():
    return jsonify(refresh_ontology_catalog())


@app.route('/api/v1/ontologies', methods=['GET', 'POST'])
def api_ontology_catalog():
    try:
        if request.method == 'GET':
            return jsonify({'ontologies': refresh_ontology_catalog()})
        if request.content_length and request.content_length > 16_384:
            return jsonify({'error': '입력 내용이 너무 큽니다.'}), 413
        created = ontology_catalog.create_ontology(request.get_json(silent=True), ONTOLOGIES, BASE_DIR)
        ONTOLOGIES[created['id']] = created['config']
        return jsonify({'key': created['id'], 'profile': created['config'],
                        'draft': True, 'message': created['message']}), 201
    except FileExistsError as error:
        return jsonify({'error': str(error)}), 409
    except ValueError as error:
        return jsonify({'error': str(error)}), 400
    except TimeoutError:
        return jsonify({'error': '다른 온톨로지를 저장 중입니다. 잠시 뒤 다시 시도해 주세요.'}), 409
    except OSError:
        return jsonify({'error': '온톨로지 파일을 저장하거나 읽을 수 없습니다.'}), 500


@app.route('/api/projects')
def api_projects():
    ont_key = request.args.get('ont', 'mv')
    ontology_config(ont_key)
    projects = project_store.list_projects(ont_key)
    return jsonify({"projects": projects, "default_project": projects[0]["id"] if projects else None})


@app.route('/api/project-detail')
def api_project_detail():
    project_id = request.args.get('project')
    if project_id is None:
        raise project_store.ProjectError("프로젝트 ID가 필요합니다.")
    ont_key = request.args.get('ont')
    if ont_key is not None:
        ontology_config(ont_key)
    config = project_store.load_project(project_id, ont_key)
    manifest = project_store.load_manifest(project_id)
    assets = []
    for asset in manifest['assets']:
        project_store.asset_path(project_id, asset['file_name'])
        assets.append({**asset, "preview_url": url_for('project_media', project_id=project_id, filename=asset['file_name'])})
    return jsonify({"project": config, "assets": assets, "timeline": manifest['timeline'],
                    "duration_seconds": manifest.get('duration_seconds'),
                    "import_info": manifest.get('import_info', {})})


@app.route('/media/<project_id>/<path:filename>')
def project_media(project_id, filename):
    project_store.load_project(project_id)
    path = project_store.asset_path(project_id, filename)
    if not path.is_file():
        raise project_store.ProjectError("등록된 미디어 파일이 없습니다.", 404)
    return send_file(path, conditional=True)

@app.route('/api/explorer')
def api_explorer():
    ont_key = request.args.get('ont', 'mv')
    cfg = ontology_config(ont_key)
    g = _load_response_graph(ont_key, request.args.get('project'), _sensitive_read_requested())
    
    classes = []
    properties = []
    instances = []
    
    query_classes = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?c ?label ?comment WHERE {
        ?c a owl:Class .
        FILTER (isIRI(?c))
        OPTIONAL { ?c rdfs:label ?label . FILTER(lang(?label) = 'ko' || lang(?label) = '') }
        OPTIONAL { ?c rdfs:comment ?comment . FILTER(lang(?comment) = 'ko' || lang(?comment) = '') }
    } ORDER BY ?c
    """
    for row in g.query(query_classes):
        classes.append({
            "uri": str(row.c),
            "name": str(row.c).split("#")[-1].split("/")[-1],
            "label": str(row.label) if row.label else str(row.c).split("#")[-1],
            "comment": str(row.comment) if row.comment else ""
        })
        
    query_props = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    
    SELECT DISTINCT ?p ?type ?label ?domain ?range WHERE {
        { ?p a owl:ObjectProperty . BIND("ObjectProperty" AS ?type) }
        UNION
        { ?p a owl:DatatypeProperty . BIND("DatatypeProperty" AS ?type) }
        OPTIONAL { ?p rdfs:label ?label . FILTER(lang(?label) = 'ko' || lang(?label) = '') }
        OPTIONAL { ?p rdfs:domain ?domain }
        OPTIONAL { ?p rdfs:range ?range }
    } ORDER BY ?p
    """
    def display_term(term):
        if not term:
            return "-"
        if isinstance(term, rdflib.BNode):
            union_head = g.value(term, rdflib.OWL.unionOf)
            if union_head is not None:
                members = sorted(
                    str(member).rsplit("#", 1)[-1].rsplit("/", 1)[-1]
                    for member in Collection(g, union_head)
                )
                return "UnionOf(" + ", ".join(members) + ")"
            return "AnonymousClass"
        return str(term).rsplit("#", 1)[-1].rsplit("/", 1)[-1]

    for row in g.query(query_props):
        properties.append({
            "uri": str(row.p),
            "name": str(row.p).split("#")[-1].split("/")[-1],
            "type": str(row.type),
            "label": str(row.label) if row.label else str(row.p).split("#")[-1],
            "domain": display_term(row.domain),
            "range": display_term(row.range)
        })

    query_instances = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    
    SELECT DISTINCT ?s ?type ?label WHERE {
        ?s rdf:type ?type .
        ?type a owl:Class .
        FILTER(isIRI(?s) && STRSTARTS(STR(?s), STR(?namespace)))
        OPTIONAL { ?s rdfs:label ?label . FILTER(lang(?label) = 'ko' || lang(?label) = '') }
    } ORDER BY ?type ?s
    """
    instances_by_uri = {}
    for row in g.query(query_instances, initBindings={"namespace": rdflib.Literal(cfg["prefix"])}):
        uri = str(row.s)
        instance = instances_by_uri.setdefault(uri, {
            "uri": uri,
            "name": uri.split("#")[-1].split("/")[-1],
            "types": [],
            "label": str(row.label) if row.label else uri.split("#")[-1]
        })
        type_name = str(row.type).split("#")[-1].split("/")[-1]
        if type_name not in instance["types"]:
            instance["types"].append(type_name)
    for instance in instances_by_uri.values():
        instance["type"] = ", ".join(instance["types"])
        instances.append(instance)
        
    return jsonify({
        "classes": classes,
        "properties": properties,
        "instances": instances
    })

@app.route('/api/instance-detail')
def api_instance_detail():
    import instance_graph
    ont_key, project_id = request.args.get('ont', 'mv'), request.args.get('project') or None
    cfg = ontology_config(ont_key)
    uri = request.args.get('uri')
    if not uri:
        raise project_store.ProjectError('개체 URI가 필요합니다.')
    inference = request.args.get('inference', 'none')
    if inference not in ('none', 'rdfs', 'owlrl'):
        raise project_store.ProjectError('inference는 none, rdfs, owlrl 중 하나여야 합니다.')
    path = selected_data_path(ont_key, project_id)
    with graph_file_lock(path):
        data_graph = _load_data_graph(ont_key, project_id)
    data_graph, _ = _apply_read_policy(data_graph, ont_key, _sensitive_read_requested())
    schema = load_schema_graph(ont_key)
    return jsonify(instance_graph.describe_instance(data_graph, schema, cfg['prefix'], uri,
                                                   project_id=project_id, inference=inference))

@app.route('/api/validate')
def api_validate():
    ont_key = request.args.get('ont', 'mv')
    cfg = ontology_config(ont_key)
    project_id = request.args.get('project') or None
    data_path = selected_data_path(ont_key, project_id)
    if ont_key == "healthcare":
        _apply_read_policy(rdflib.Graph(), ont_key, _sensitive_read_requested())
    
    if not cfg["shapes"]:
        return jsonify({"supported": False, "conforms": None, "message": "SHACL 규칙이 없어 이 온톨로지는 검증하지 않습니다.", "details": [], "report_text": ""})
        
    shapes_path = os.path.join(BASE_DIR, cfg["shapes"])
    try:
        data_graph = rdflib.Graph().parse(data_path, format="turtle" if data_path.endswith(".ttl") else "xml")
        shapes_graph = load_shape_graph(ont_key)
        ont_graph = load_schema_graph(ont_key)
        
        from validation_pipeline import validate_phases, public_summary
        phases = validate_phases(data_graph, ont_graph, shapes_graph)
        shacl_conforms, report_text = phases['conforms'], phases['report_text']
        
        details = []
        for line in report_text.splitlines():
            if line.strip():
                details.append(line)

        file_checks = project_store.check_assets(project_id, data_graph, rdflib.Namespace(cfg['prefix'])) if project_id is not None else []
        files_conform = all(item['valid'] for item in file_checks)
        conforms = bool(shacl_conforms) and files_conform
        for check in file_checks:
            details.extend(f"{check['file_name']}: {error}" for error in check['errors'])
        report_text = '\n'.join(details)
        if ont_key == "healthcare" and not _sensitive_read_requested() and not conforms:
            details = ["의료 그래프 검증에 실패했습니다. 기본 개인정보 정책에 따라 상세 결과를 숨겼습니다."]
            report_text = details[0]
            file_checks = []
                
        return jsonify({
            "supported": True,
            "conforms": conforms,
            "shacl_conforms": bool(shacl_conforms),
            "validation_phases": public_summary(phases),
            "files_conform": files_conform,
            "file_checks": file_checks,
            "message": ("SHACL 및 등록 파일 검증 성공" if conforms else "SHACL 또는 등록 파일 검증 실패") if project_id is not None else ("PySHACL 검증 성공 (Conforms: True)" if conforms else "PySHACL 검증 실패 (Conforms: False)"),
            "details": details,
            "report_text": report_text
        })
    except project_store.ProjectError:
        raise
    except Exception as e:
        return jsonify({"supported": True, "conforms": None, "error": str(e), "message": f"검증 오류: {str(e)}", "details": [str(e)], "report_text": str(e)})

@app.route('/api/sparql', methods=['POST'])
def api_sparql():
    data = request.json or {}
    ont_key = data.get('ont', 'mv')
    query_str = data.get('query', '')
    
    if not query_str:
        return jsonify({"error": "Query string is empty"}), 400
        
    backend = data.get('backend')
    if backend:
        if ont_key == "healthcare":
            if not _sensitive_read_requested(data):
                raise project_store.ProjectError(
                    "원격 의료 그래프 조회에는 ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE=1과 include_sensitive=true가 모두 필요합니다.",
                    403,
                )
            _apply_read_policy(rdflib.Graph(), ont_key, True)
        from graph_store import GraphStoreConnector
        gs = GraphStoreConnector()
        try:
            results = gs.execute_query(query_str, backend=backend)
        except Exception as e:
            return jsonify({"error": f"Graph backend query error: {str(e)}"}), 500
        return jsonify(results)
    else:
        g = _load_response_graph(ont_key, data.get('project'), _sensitive_read_requested(data))
        try:
            results = g.query(query_str)
            vars_list = [str(v) for v in results.vars] if results.vars else []
            rows = []
            for row in results:
                row_dict = {}
                for v in vars_list:
                    val = row[v]
                    row_dict[v] = str(val) if val is not None else ""
                rows.append(row_dict)
            return jsonify({"vars": vars_list, "rows": rows, "results": rows, "count": len(rows)})
        except Exception as e:
            return jsonify({"error": f"SPARQL 실행 오류: {str(e)}"}), 400

@app.route('/api/add-shot', methods=['POST'])
def api_add_shot():
    from decimal import Decimal, InvalidOperation
    import re

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise project_store.ProjectError("장면 요청은 JSON 객체여야 합니다.")
    if data.get('project') not in (None, '') or request.args.get('project') not in (None, ''):
        raise project_store.ProjectError("등록 프로젝트의 장면 편집은 아직 지원하지 않습니다. 가상 예제에서만 장면을 추가할 수 있습니다.")
    domain = data.get('ont', request.args.get('ont', 'mv'))
    if domain != 'mv':
        raise project_store.ProjectError("장면 추가는 mv 가상 예제에서만 지원합니다.")
    shot_id = data.get('shot_id', 'shot03')
    if not isinstance(shot_id, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', shot_id):
        raise project_store.ProjectError("장면 ID는 영문, 숫자, 하이픈, 밑줄로 1~100자여야 합니다.")
    try:
        order_value = Decimal(str(data.get('order_index', 3)))
        start_sec = Decimal(str(data.get('start_sec', '60')))
        end_sec = Decimal(str(data.get('end_sec', '90')))
    except (InvalidOperation, ValueError, TypeError):
        raise project_store.ProjectError("장면 순서와 시간은 유효한 숫자여야 합니다.") from None
    if not order_value.is_finite() or order_value <= 0 or order_value != order_value.to_integral_value():
        raise project_store.ProjectError("장면 순서는 양의 정수여야 합니다.")
    if not start_sec.is_finite() or not end_sec.is_finite() or not 0 <= start_sec < end_sec:
        raise project_store.ProjectError("장면 시간은 유한한 숫자로 0 ≤ 시작 < 종료여야 합니다.")
    order_index = int(order_value)
    namespace = rdflib.Namespace(ONTOLOGIES['mv']['prefix'])
    image_uri = data.get('image_uri', str(namespace.image02))
    label = data.get('label', '세 번째 장면 (60~90초)')
    if not isinstance(image_uri, str) or not isinstance(label, str):
        raise project_store.ProjectError("이미지 URI와 장면 이름은 문자열이어야 합니다.")
    path = selected_data_path('mv')
    with graph_file_lock(path):
        graph = _load_data_graph('mv')
        shot = namespace[shot_id]
        if any(graph.triples((shot, None, None))):
            raise project_store.ProjectError("이미 존재하는 장면 ID입니다.", 409)
        for existing in graph.subjects(rdflib.RDF.type, namespace.Shot):
            if any(value.toPython() == order_index for value in graph.objects(existing, namespace.orderIndex)):
                raise project_store.ProjectError("이미 사용 중인 장면 순서입니다.", 409)
        image = rdflib.URIRef(image_uri)
        if (image, rdflib.RDF.type, namespace.ImageAsset) not in graph:
            raise project_store.ProjectError("이미지 URI는 예제에 등록된 ImageAsset이어야 합니다.")
        if (namespace.timeline01, rdflib.RDF.type, namespace.Timeline) not in graph:
            raise project_store.ProjectError("예제의 timeline01 타임라인을 찾을 수 없습니다.", 409)
        for triple in [
            (shot, rdflib.RDF.type, namespace.Shot),
            (shot, rdflib.RDFS.label, rdflib.Literal(label, lang='ko')),
            (shot, namespace.orderIndex, rdflib.Literal(order_index, datatype=rdflib.XSD.integer)),
            (shot, namespace.startSecond, rdflib.Literal(start_sec, datatype=rdflib.XSD.decimal)),
            (shot, namespace.endSecond, rdflib.Literal(end_sec, datatype=rdflib.XSD.decimal)),
            (shot, namespace.usesImage, image),
            (namespace.timeline01, namespace.hasShot, shot),
        ]:
            graph.add(triple)
        validation = _validate_candidate(graph, 'mv')
        write_graph_atomic(graph, path, format='turtle')
    return jsonify({"success": True, "message": f"장면 {shot_id}가 성공적으로 추가되었습니다.",
                    "validation": validation})

RDFS_PREFIX = "PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>\nPREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>\n"

MV_TEMPLATES = [
    {
        "key": "list_shots",
        "title": "장면(Shot) 순서와 시간 구간",
        "query": RDFS_PREFIX + "PREFIX mv: <https://example.org/mv#>\nSELECT ?shotName ?order ?startSec ?endSec WHERE {\n  ?shot a mv:Shot ;\n        rdfs:label ?shotName ;\n        mv:orderIndex ?order ;\n        mv:startSecond ?startSec ;\n        mv:endSecond ?endSec .\n} ORDER BY ?order",
    },
    {
        "key": "list_media_assets",
        "title": "미디어 자산과 기술 정보",
        "query": RDFS_PREFIX + "PREFIX mv: <https://example.org/mv#>\nSELECT ?asset ?file ?duration ?width ?height WHERE {\n  ?asset mv:fileUri ?file .\n  OPTIONAL { ?asset mv:durationSeconds ?duration }\n  OPTIONAL { ?asset mv:width ?width }\n  OPTIONAL { ?asset mv:height ?height }\n} ORDER BY ?asset",
    },
]

SPARQL_TEMPLATES = {
    "mv": MV_TEMPLATES,
    "e2e": MV_TEMPLATES + [
        {
            "key": "list_pipeline_tasks",
            "title": "가사·자막·번역 작업과 담당 에이전트",
            "query": RDFS_PREFIX + "PREFIX mv: <https://example.org/mv#>\nPREFIX prov: <http://www.w3.org/ns/prov#>\nSELECT ?task ?taskLabel ?status ?agentLabel WHERE {\n  ?task mv:status ?status ;\n        prov:wasAssociatedWith ?agent .\n  ?agent rdfs:label ?agentLabel .\n  OPTIONAL { ?task rdfs:label ?taskLabel }\n} ORDER BY ?task",
        },
        {
            "key": "list_dependencies_and_inputs",
            "title": "선행 작업과 사용 입력 자료",
            "query": RDFS_PREFIX + "PREFIX mv: <https://example.org/mv#>\nSELECT ?task ?relation ?target WHERE {\n  { ?task mv:dependsOn ?target . BIND(\"task-dependency\" AS ?relation) }\n  UNION\n  { ?task mv:usesInput ?target . BIND(\"input\" AS ?relation) }\n} ORDER BY ?task ?relation",
        },
    ],
    "devops": [
        {
            "key": "list_pipelines",
            "title": "파이프라인 실행 상태와 하위 태스크",
            "query": RDFS_PREFIX + "PREFIX devops: <http://example.org/ontology/devops#>\nSELECT ?pipeId ?status ?task ?taskLabel WHERE {\n  ?pipe a devops:DevOpsPipeline ;\n        devops:pipelineId ?pipeId ;\n        devops:executionStatus ?status ;\n        devops:hasTask ?task .\n  OPTIONAL { ?task rdfs:label ?taskLabel }\n} ORDER BY ?task",
        },
        {
            "key": "list_security",
            "title": "보안 스캔 결과 (취약점 수)",
            "query": RDFS_PREFIX + "PREFIX devops: <http://example.org/ontology/devops#>\nSELECT ?task ?label ?vulnerabilities WHERE {\n  ?task a devops:SecurityScanTask ;\n        devops:vulnerabilityCount ?vulnerabilities .\n  OPTIONAL { ?task rdfs:label ?label }\n}",
        },
        {
            "key": "list_deployments",
            "title": "배포 대상 환경",
            "query": RDFS_PREFIX + "PREFIX devops: <http://example.org/ontology/devops#>\nSELECT ?task ?env ?envName WHERE {\n  ?task a devops:DeploymentTask ;\n        devops:deployedTo ?env .\n  OPTIONAL { ?env devops:environmentName ?envName }\n}",
        },
    ],
    "agent": [
        {
            "key": "list_tasks",
            "title": "계획한 작업과 담당 에이전트",
            "query": RDFS_PREFIX + "PREFIX ag: <https://example.org/agent#>\nSELECT ?task ?objective ?agent ?dependsOn WHERE {\n  ?task a ag:Task ;\n        ag:taskObjective ?objective ;\n        ag:assignedTo ?agent .\n  OPTIONAL { ?task ag:dependsOn ?dependsOn }\n} ORDER BY ?task",
        },
        {
            "key": "reviewed_final_artifacts",
            "title": "최종 결과물과 승인 검수 판정",
            "query": RDFS_PREFIX + "PREFIX ag: <https://example.org/agent#>\nSELECT ?project ?artifact ?decision WHERE {\n  ?project a ag:Project ; ag:hasFinalArtifact ?artifact .\n  OPTIONAL { ?review a ag:ReviewDecision ;\n                    ag:decisionAbout ?artifact ;\n                    ag:decision ?decision }\n} ORDER BY ?project ?artifact",
        },
    ],
    "ecommerce": [
        {
            "key": "list_products",
            "title": "상품 카탈로그와 가격",
            "query": RDFS_PREFIX + "PREFIX ecom: <http://example.org/ontology/ecommerce#>\nSELECT ?product ?label ?productId ?price ?currency WHERE {\n  ?product a ecom:Product ;\n           ecom:productId ?productId ;\n           ecom:price ?price .\n  OPTIONAL { ?product rdfs:label ?label }\n  OPTIONAL { ?product ecom:priceCurrency ?currency }\n} ORDER BY ?productId",
        },
        {
            "key": "list_orders",
            "title": "주문 이행 상태와 담당 에이전트",
            "query": RDFS_PREFIX + "PREFIX ecom: <http://example.org/ontology/ecommerce#>\nSELECT ?order ?status ?agent ?product WHERE {\n  ?order a ecom:OrderTask ;\n         ecom:orderStatus ?status ;\n         ecom:handledBy ?agent .\n  OPTIONAL { ?order ecom:includesProduct ?product }\n}",
        },
        {
            "key": "list_recommendations",
            "title": "세션별 추천 상품",
            "query": RDFS_PREFIX + "PREFIX ecom: <http://example.org/ontology/ecommerce#>\nSELECT ?session ?product WHERE {\n  ?session a ecom:CustomerSession ;\n           ecom:recommends ?product .\n}",
        },
    ],
    "healthcare": [
        {
            "key": "count_patient_records",
            "title": "환자 기록 수 (식별정보 제외)",
            "query": RDFS_PREFIX + "PREFIX health: <http://example.org/ontology/healthcare#>\nSELECT (COUNT(DISTINCT ?record) AS ?recordCount) WHERE {\n  ?record a health:PatientRecord .\n}",
        },
        {
            "key": "diagnostic_status_counts",
            "title": "진단 실행 상태별 건수 (환자·소견 제외)",
            "query": RDFS_PREFIX + "PREFIX health: <http://example.org/ontology/healthcare#>\nSELECT ?status (COUNT(?task) AS ?taskCount) WHERE {\n  ?task a health:DiagnosticTask ;\n        health:diagnosticStatus ?status .\n} GROUP BY ?status ORDER BY ?status",
        },
    ],
    "academic": [
        {
            "key": "courses_and_students",
            "title": "과목과 확인된 수강생",
            "query": RDFS_PREFIX + "PREFIX academic: <https://example.org/ontology/academic#>\nSELECT ?course ?courseLabel ?student ?studentLabel WHERE {\n  ?course a academic:Course ; rdfs:label ?courseLabel .\n  OPTIONAL { ?course academic:hasStudent ?student .\n             OPTIONAL { ?student rdfs:label ?studentLabel } }\n} ORDER BY ?courseLabel",
        },
        {
            "key": "professor_courses",
            "title": "교수별 담당 과목",
            "query": RDFS_PREFIX + "PREFIX academic: <https://example.org/ontology/academic#>\nSELECT ?professor ?professorLabel ?course ?courseLabel WHERE {\n  ?professor a academic:Professor ; academic:teaches ?course .\n  OPTIONAL { ?professor rdfs:label ?professorLabel }\n  OPTIONAL { ?course rdfs:label ?courseLabel }\n} ORDER BY ?professorLabel ?courseLabel",
        },
    ],
    "stock": [
        {
            "key": "portfolio_positions",
            "title": "포트폴리오 보유 종목 및 평가",
            "query": RDFS_PREFIX + "PREFIX stock: <http://example.org/ontology/stock#>\nSELECT ?pos ?asset ?ticker ?qty ?cost WHERE {\n  ?pos a stock:PortfolioPosition ;\n       stock:positionAsset ?asset ;\n       stock:positionQuantity ?qty ;\n       stock:averageCost ?cost .\n  OPTIONAL { ?asset stock:tickerSymbol ?ticker }\n} ORDER BY DESC(?qty)",
        },
        {
            "key": "fundamental_and_technical",
            "title": "종목별 펀더멘털 및 기술적 분석 지표",
            "query": RDFS_PREFIX + "PREFIX stock: <http://example.org/ontology/stock#>\nSELECT ?stock ?name ?per ?pbr ?roe ?rsi WHERE {\n  ?stock a stock:Stock ; rdfs:label ?name .\n  OPTIONAL { ?stock stock:hasFinancialMetric ?m . ?m stock:per ?per ; stock:pbr ?pbr ; stock:roe ?roe }\n  OPTIONAL { ?stock stock:hasTechnicalIndicator ?t . ?t stock:rsi ?rsi }\n} ORDER BY ?per",
        },
        {
            "key": "trading_orders",
            "title": "AI 에이전트 매매 주문 현황",
            "query": RDFS_PREFIX + "PREFIX stock: <http://example.org/ontology/stock#>\nSELECT ?order ?type ?status ?asset ?qty ?price ?agent WHERE {\n  ?order a stock:TradingOrder ;\n         stock:orderType ?type ;\n         stock:orderStatus ?status ;\n         stock:orderAsset ?asset ;\n         stock:orderQuantity ?qty ;\n         stock:orderPrice ?price ;\n         stock:executedByAgent ?agent .\n} ORDER BY ?status",
        },
    ],
    "diet": [
        {
            "key": "profiles_and_goals",
            "title": "감량 프로필 및 목표 설정 현황",
            "query": RDFS_PREFIX + "PREFIX diet: <http://example.org/ontology/diet#>\nSELECT ?profile ?name ?height ?targetWeight ?targetFat ?targetDeficit ?agent WHERE {\n  ?profile a diet:WeightLossProfile ;\n           diet:profileName ?name ;\n           diet:heightCm ?height ;\n           diet:hasTargetGoal ?goal .\n  ?goal diet:targetWeightKg ?targetWeight .\n  OPTIONAL { ?goal diet:targetBodyFatPercent ?targetFat }\n  OPTIONAL { ?goal diet:targetDailyCalorieDeficit ?targetDeficit }\n  OPTIONAL { ?profile diet:assignedAgent ?agent }\n} ORDER BY ?name",
        },
        {
            "key": "meal_and_macronutrients",
            "title": "식단 섭취 칼로리 및 3대 영양소 분석",
            "query": RDFS_PREFIX + "PREFIX diet: <http://example.org/ontology/diet#>\nSELECT ?profile ?name ?meal ?mealType ?calories ?carbs ?protein ?fat WHERE {\n  ?profile a diet:WeightLossProfile ;\n           diet:profileName ?name ;\n           diet:logsMeal ?meal .\n  ?meal diet:mealType ?mealType ;\n        diet:mealCaloriesKcal ?calories .\n  OPTIONAL { ?meal diet:carbohydrateGrams ?carbs }\n  OPTIONAL { ?meal diet:proteinGrams ?protein }\n  OPTIONAL { ?meal diet:fatGrams ?fat }\n} ORDER BY ?name ?mealType",
        },
        {
            "key": "coaching_interventions",
            "title": "AI 코칭 에이전트 개입 및 정체기 처방 지침",
            "query": RDFS_PREFIX + "PREFIX diet: <http://example.org/ontology/diet#>\nSELECT ?task ?action ?status ?profile ?coach ?alert WHERE {\n  ?task a diet:CoachingInterventionTask ;\n        diet:interventionAction ?action ;\n        diet:taskStatus ?status ;\n        diet:targetProfile ?profile ;\n        diet:executedByCoach ?coach .\n  OPTIONAL { ?task diet:triggeredByAlert ?alert }\n} ORDER BY ?status",
        },
    ],
    "korean-war": [
        {
            "key": "list_operations",
            "title": "주요 군사 작전, 전장 및 지휘관",
            "query": RDFS_PREFIX + "PREFIX kwar: <http://example.org/ontology/korean-war#>\nSELECT ?op ?name ?start ?end ?outcome ?locName ?commander WHERE {\n  ?op a kwar:MilitaryOperation ;\n      kwar:operationName ?name ;\n      kwar:startDate ?start .\n  OPTIONAL { ?op kwar:endDate ?end }\n  OPTIONAL { ?op kwar:strategicOutcome ?outcome }\n  OPTIONAL { ?op kwar:occurredAt ?loc . ?loc kwar:locationName ?locName }\n  OPTIONAL { ?op kwar:ledByCommander ?cmd . ?cmd kwar:commanderName ?commander }\n} ORDER BY ?start",
        },
        {
            "key": "list_casualties",
            "title": "작전별 전사상자 피해 통계",
            "query": RDFS_PREFIX + "PREFIX kwar: <http://example.org/ontology/korean-war#>\nSELECT ?opName ?kia ?wia ?mia WHERE {\n  ?cas a kwar:WarCasualtyRecord ;\n       kwar:associatedOperation ?op ;\n       kwar:killedInAction ?kia ;\n       kwar:woundedInAction ?wia .\n  ?op kwar:operationName ?opName .\n  OPTIONAL { ?cas kwar:missingInAction ?mia }\n} ORDER BY DESC(?kia)",
        },
        {
            "key": "list_ai_analyses",
            "title": "AI 전사 고증 및 사료 분석 결과",
            "query": RDFS_PREFIX + "PREFIX kwar: <http://example.org/ontology/korean-war#>\nSELECT ?task ?findings ?status ?opName ?agent WHERE {\n  ?task a kwar:AnalysisTask ;\n        kwar:taskFindings ?findings ;\n        kwar:taskStatus ?status ;\n        kwar:targetOperation ?op ;\n        kwar:assignedAnalyst ?agent .\n  ?op kwar:operationName ?opName .\n} ORDER BY ?status",
        },
    ],
    "theme-park": [
        {
            "key": "list_attractions_and_waits",
            "title": "어트랙션별 실시간 대기 시간 및 운영 상태",
            "query": RDFS_PREFIX + "PREFIX tpark: <http://example.org/ontology/theme-park#>\nSELECT ?ride ?name ?zoneName ?waitMin ?queueLen ?status WHERE {\n  ?ride a tpark:Attraction ;\n        rdfs:label ?name ;\n        tpark:operationalStatus ?status ;\n        tpark:locatedInZone ?zone .\n  ?zone rdfs:label ?zoneName .\n  OPTIONAL { ?ride tpark:hasWaitTime ?w . ?w tpark:currentWaitMinutes ?waitMin ; tpark:queueLengthPersons ?queueLen }\n} ORDER BY DESC(?waitMin)",
        },
        {
            "key": "list_inspections",
            "title": "어트랙션 안전 점검 및 합격 내역",
            "query": RDFS_PREFIX + "PREFIX tpark: <http://example.org/ontology/theme-park#>\nSELECT ?rideName ?inspDate ?passed ?inspector WHERE {\n  ?ride a tpark:Attraction ;\n        rdfs:label ?rideName ;\n        tpark:hasInspection ?insp .\n  ?insp tpark:inspectionDate ?inspDate ;\n        tpark:inspectionPassed ?passed .\n  OPTIONAL { ?insp tpark:safetyInspector ?inspector }\n} ORDER BY DESC(?inspDate)",
        },
        {
            "key": "list_ai_crowd_operations",
            "title": "AI 에이전트 군중 혼잡도 및 분산 권고",
            "query": RDFS_PREFIX + "PREFIX tpark: <http://example.org/ontology/theme-park#>\nSELECT ?agent ?agentName ?congestion ?recommendation WHERE {\n  ?agent a tpark:CrowdControlAgent ;\n         rdfs:label ?agentName ;\n         tpark:congestionLevel ?congestion .\n  OPTIONAL { ?agent tpark:aiRecommendationNote ?recommendation }\n}",
        },
    ],
}

# In-memory validation history shared by /api/v1/validate-all and /api/v1/metrics.
VALIDATION_HISTORY = []
MAX_HISTORY = 50


def _validate_domain(key, with_phases=False):
    """Validate a domain's bundled example data; returns (conforms, seconds)."""
    cfg = ONTOLOGIES[key]
    if not cfg["shapes"]:
        return (None, 0.0, None) if with_phases else (None, 0.0)
    started = time.perf_counter()
    data_path = selected_data_path(key)
    data_g = rdflib.Graph().parse(data_path, format="turtle" if data_path.endswith(".ttl") else "xml")
    shapes_g = load_shape_graph(key)
    ont_g = load_schema_graph(key)
    from validation_pipeline import validate_phases
    phases = validate_phases(data_g, ont_g, shapes_g)
    if with_phases:
        from validation_pipeline import public_summary
        return phases['conforms'], time.perf_counter() - started, public_summary(phases)
    return phases['conforms'], time.perf_counter() - started


@app.route('/api/sparql-templates', methods=['GET'])
def api_sparql_templates():
    templates = dict(SPARQL_TEMPLATES)
    for key, cfg in list(ONTOLOGIES.items()):
        if key in templates:
            continue
        from pathlib import Path
        from ontology_quality import QUESTION_PATTERN
        questions = Path(BASE_DIR) / cfg.get('questions', '')
        templates[key] = [{'key': match.group('title').split('.', 1)[0], 'title': match.group('title'),
                           'query': match.group('query')} for match in QUESTION_PATTERN.finditer(
                               questions.read_text(encoding='utf-8') if questions.is_file() else '')]
    ont_key = request.args.get('ont')
    if ont_key:
        ontology_config(ont_key)
        return jsonify({ont_key: templates.get(ont_key, [])})
    return jsonify(templates)


@app.route('/api/v1/domains', methods=['GET'])
def api_v1_domains():
    refresh_ontology_catalog()
    return jsonify({"domains": list(ONTOLOGIES.keys()), "details": ONTOLOGIES})


@app.route('/api/v1/validate-all', methods=['GET'])
def api_v1_validate_all():
    results = {}
    for key in list(ONTOLOGIES):
        conforms, seconds, phases = _validate_domain(key, with_phases=True)
        status = "SKIPPED" if conforms is None else ("PASS" if conforms else "FAIL")
        results[key] = {"conforms": conforms, "status": status, "seconds": round(seconds, 3), "validation_phases": phases}
    overall = all(r["conforms"] for r in results.values() if r["conforms"] is not None)
    VALIDATION_HISTORY.append({
        "at": datetime.datetime.now().isoformat(timespec='seconds'),
        "overall": overall,
        "passed": sum(1 for r in results.values() if r["status"] == "PASS"),
        "failed": sum(1 for r in results.values() if r["status"] == "FAIL"),
        "results": {k: v["status"] for k, v in results.items()},
    })
    del VALIDATION_HISTORY[:-MAX_HISTORY]
    return jsonify({"overall_conforms": overall, "results": results})


@app.route('/api/v1/metrics', methods=['GET'])
def api_v1_metrics():
    """Fast dashboard data: triple/class/instance counts and SPARQL latency per domain.

    SHACL status is taken from the last /api/v1/validate-all run so this endpoint stays cheap.
    """
    last = VALIDATION_HISTORY[-1] if VALIDATION_HISTORY else None
    domains = []
    for key, cfg in list(ONTOLOGIES.items()):
        g = _load_response_graph(key)
        data_path = selected_data_path(key)
        data_g = rdflib.Graph().parse(data_path, format="turtle" if data_path.endswith(".ttl") else "xml")
        data_g, _ = _apply_read_policy(data_g, key)
        query = "SELECT ?s ?p ?o WHERE { ?s ?p ?o } LIMIT 200"
        started = time.perf_counter()
        list(g.query(query))
        latency_ms = (time.perf_counter() - started) * 1000
        classes = {s for s in g.subjects(rdflib.RDF.type, rdflib.OWL.Class)} | {s for s in g.subjects(rdflib.RDF.type, rdflib.RDFS.Class)}
        properties = {s for t in (rdflib.OWL.ObjectProperty, rdflib.OWL.DatatypeProperty) for s in g.subjects(rdflib.RDF.type, t)}
        instances = {s for s in data_g.subjects(rdflib.RDF.type, None) if isinstance(s, rdflib.URIRef) and str(s).startswith(cfg["prefix"])}
        domains.append({
            "key": key,
            "name": cfg["name"],
            "triples": len(g),
            "data_triples": len(data_g),
            "classes": len(classes),
            "properties": len(properties),
            "instances": len(instances),
            "sparql_ms": round(latency_ms, 2),
            "shacl": (last["results"].get(key) if last else None) or "UNKNOWN",
        })
    return jsonify({
        "domains": domains,
        "totals": {
            "triples": sum(d["triples"] for d in domains),
            "classes": sum(d["classes"] for d in domains),
            "instances": sum(d["instances"] for d in domains),
        },
        "history": VALIDATION_HISTORY,
    })


@app.route('/api/graph-data', methods=['GET'])
def api_graph_data():
    import instance_graph
    ont_key, project_id = request.args.get('ont', 'mv'), request.args.get('project') or None
    cfg = ontology_config(ont_key)
    inference = request.args.get('inference', 'none')
    if inference not in ('none', 'rdfs', 'owlrl'):
        raise project_store.ProjectError('inference는 none, rdfs, owlrl 중 하나여야 합니다.')
    external = request.args.get('include_external', '0')
    if external not in ('0', '1', 'false', 'true'):
        raise project_store.ProjectError('include_external은 0 또는 1이어야 합니다.')
    try:
        limit = int(request.args.get('limit', 500))
    except (TypeError, ValueError):
        raise project_store.ProjectError('limit은 정수여야 합니다.')
    if not 1 <= limit <= 1000:
        raise project_store.ProjectError('limit은 1~1000이어야 합니다.')
    path = selected_data_path(ont_key, project_id)
    with graph_file_lock(path):
        data_graph = _load_data_graph(ont_key, project_id)
    data_graph, _ = _apply_read_policy(data_graph, ont_key, _sensitive_read_requested())
    schema = load_schema_graph(ont_key)
    result = instance_graph.build_instance_graph(data_graph, schema, cfg['prefix'],
                                               include_external=external in ('1', 'true'),
                                               inference=inference, limit=limit, project_id=project_id)
    result['scope'] = {'ont': ont_key, 'project': project_id}
    return jsonify(result)


@app.route('/api/v1/relations', methods=['POST', 'DELETE'])
def api_v1_relations():
    import instance_relations, event_stream
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise project_store.ProjectError('관계 요청은 JSON 객체여야 합니다.')
    project_id = data.get('project')
    if project_id is not None and not isinstance(project_id, str):
        raise project_store.ProjectError('project는 프로젝트 ID 문자열이어야 합니다.')
    ont_key, project_id = data.get('ont', 'mv'), project_id or None
    selected_data_path(ont_key, project_id)
    result = instance_relations.mutate_relation(ont_key, project_id, data.get('subject'),
                                               data.get('predicate'), data.get('object'),
                                               action='add' if request.method == 'POST' else 'delete')
    if result.get('changed'):
        event_stream.publish_event('RELATION_UPDATED', {'ont': ont_key, 'project': project_id,
                                  'subject': data['subject'], 'predicate': data['predicate'],
                                  'object': data['object'], 'action': request.method.lower(),
                                  'snapshot_id': result.get('snapshot_id')})
    return jsonify(result)


@app.route('/api/v1/export', methods=['GET'])
def api_v1_export():
    ont_key = request.args.get('ont', 'mv')
    fmt = request.args.get('format', 'turtle').lower()
    format_map = {
        'turtle': ('turtle', 'text/turtle', 'ttl'),
        'ttl': ('turtle', 'text/turtle', 'ttl'),
        'jsonld': ('json-ld', 'application/ld+json', 'jsonld'),
        'json-ld': ('json-ld', 'application/ld+json', 'jsonld'),
        'xml': ('pretty-xml', 'application/rdf+xml', 'rdf'),
        'rdf': ('pretty-xml', 'application/rdf+xml', 'rdf'),
        'nt': ('nt', 'application/n-triples', 'nt'),
        'ntriples': ('nt', 'application/n-triples', 'nt')
    }
    if fmt not in format_map:
        return jsonify({"error": f"지원하지 않는 포맷입니다. 지원 포맷: {list(format_map.keys())}"}), 400
    
    rdflib_fmt, mime_type, ext = format_map[fmt]
    g = _load_response_graph(ont_key, request.args.get('project'), _sensitive_read_requested())
    serialized = g.serialize(format=rdflib_fmt)
    
    if request.args.get('download') == '1':
        from io import BytesIO
        mem = BytesIO(serialized.encode('utf-8') if isinstance(serialized, str) else serialized)
        response = send_file(mem, mimetype=mime_type, as_attachment=True, download_name=f"{ont_key}_export.{ext}")
        if ont_key == "healthcare" and not _sensitive_read_requested():
            response.headers['X-Privacy-Redaction'] = 'unverified-and-protected-records'
        return response
    headers = {'Content-Type': f"{mime_type}; charset=utf-8"}
    if ont_key == "healthcare" and not _sensitive_read_requested():
        headers['X-Privacy-Redaction'] = 'unverified-and-protected-records'
    return serialized, 200, headers


@app.route('/api/v1/healthcare/fhir-bundle', methods=['GET'])
def api_v1_healthcare_fhir_bundle():
    """Export only the explicitly synthetic healthcare subset as FHIR R5 JSON."""
    import json
    import fhir_export

    graph = _load_response_graph("healthcare", request.args.get("project"), False)
    bundle = fhir_export.export_healthcare_bundle(graph)
    checked = fhir_export.validate_collection_bundle(bundle)
    if not checked["valid"]:
        return jsonify({"error": "FHIR collection generation failed local structural validation."}), 500
    response = Response(json.dumps(bundle, ensure_ascii=False, separators=(",", ":")),
                        mimetype="application/fhir+json")
    response.headers["X-Privacy-Redaction"] = "synthetic-only-no-patient-key"
    response.headers["X-FHIR-Version"] = "5.0.0"
    return response


@app.route('/api/docs')
def api_docs():
    return render_template('docs.html')


@app.route('/api/openapi.json')
def api_openapi_json():
    import openapi_spec
    return jsonify(openapi_spec.OPENAPI_SPEC)


@app.route('/api/v1/nl-query', methods=['POST'])
def api_v1_nl_query():
    # Support both JSON and multipart/form-data for multimodal inputs
    if request.content_type and request.content_type.startswith('multipart/form-data'):
        question = request.form.get('question', '').strip()
        if not question:
            return jsonify({"error": "질문(question)을 입력해주세요."}), 400
        image = request.files.get('image')
        audio = request.files.get('audio')
        image_bytes = image.read() if image else None
        audio_bytes = audio.read() if audio else None
        try:
            from multimodal_rag import process_multimodal_query
            node_uris, prompt = process_multimodal_query(question, image_bytes, audio_bytes)
            return jsonify({"question": question, "node_uris": node_uris, "prompt": prompt})
        except Exception as e:
            return jsonify({"error": f"멀티모달 질의 처리 실패: {str(e)}"}), 500
    else:
        data = request.get_json() or {}
        ont_key = data.get('ont', 'mv')
        question = data.get('question', '').strip()
        if not question:
            return jsonify({"error": "질문(question)을 입력해주세요."}), 400
        try:
            import nl_query
            g = _load_response_graph(ont_key, data.get('project'), _sensitive_read_requested(data))
            res = nl_query.answer_natural_query(g, question, ont_key)
            return jsonify(res)
        except Exception as e:
            return jsonify({"error": f"자연어 질의 처리 실패: {str(e)}"}), 500
@app.route('/api/v1/instances', methods=['POST', 'DELETE'])
def api_v1_instances():
    import instance_editor
    import event_stream
    if request.method == 'POST':
        data = request.get_json() or {}
        ont_key = data.get('ont', 'mv')
        class_uri = data.get('class_uri')
        label = data.get('label')
        properties = data.get('properties', {})
        project_id = data.get('project')
        if not class_uri or not label:
            return jsonify({"error": "class_uri와 label은 필수 입력값입니다."}), 400
        try:
            res = instance_editor.create_instance(ont_key, class_uri, label, properties, project_id)
            if res.get("success"):
                event_stream.publish_event("INSTANCE_CREATED", {
                    "ont": ont_key,
                    "uri": res.get("instance_uri"),
                    "label": label,
                    "class_uri": class_uri
                })
            return jsonify(res)
        except project_store.ProjectError:
            raise
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    else:
        import urllib.parse
        data = request.get_json(silent=True) or {}
        ont_key = request.args.get('ont') or data.get('ont', 'mv')
        uri = request.args.get('uri') or data.get('uri')
        project_id = request.args.get('project') or data.get('project')
        if not uri:
            return jsonify({"error": "uri 파라미터가 필요합니다."}), 400
        uri = urllib.parse.unquote(uri)
        try:
            res = instance_editor.delete_instance(ont_key, uri, project_id)
            if res.get("success"):
                event_stream.publish_event("INSTANCE_DELETED", {
                    "ont": ont_key,
                    "uri": uri,
                    "triples_removed": res.get("triples_removed", 0)
                })
            return jsonify(res)
        except project_store.ProjectError:
            raise
        except Exception as e:
            return jsonify({"error": str(e)}), 400


@app.route('/api/v1/simulate', methods=['POST'])
def api_v1_simulate():
    data = request.get_json() or {}
    step = int(data.get('step', 1))
    session_id = data.get('session_id')
    try:
        import simulation
        res = simulation.run_pipeline_step(step, session_id)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route('/api/v1/fuseki/status', methods=['GET'])
def api_v1_fuseki_status():
    import fuseki_sync
    endpoint = request.args.get('endpoint')
    connected, msg, ping_ms = fuseki_sync.check_fuseki_connection(endpoint)
    return jsonify({"connected": connected, "message": msg, "ping_ms": ping_ms, "endpoint": fuseki_sync.get_endpoint_url(endpoint)})


@app.route('/api/v1/fuseki/sync', methods=['POST'])
def api_v1_fuseki_sync():
    import fuseki_sync
    data = request.get_json(silent=True) or {}
    ont_key = data.get('ont') or request.args.get('ont')
    endpoint = data.get('endpoint') or request.args.get('endpoint')
    project_id = data.get('project') or request.args.get('project')
    if ont_key in (None, 'all', 'healthcare'):
        if not _sensitive_read_requested(data):
            raise project_store.ProjectError(
                "의료 그래프를 외부 Fuseki에 전송하려면 ONTOLOGY_ALLOW_SENSITIVE_HEALTHCARE=1과 include_sensitive=true가 모두 필요합니다.",
                403,
            )
        _apply_read_policy(rdflib.Graph(), 'healthcare', True)
    if ont_key and ont_key != 'all':
        res = fuseki_sync.sync_domain(
            ont_key, project_id=project_id, endpoint=endpoint,
            allow_sensitive_healthcare=(ont_key == "healthcare"),
        )
        return jsonify(res)
    res = fuseki_sync.sync_all_domains(
        endpoint=endpoint,
        allow_sensitive_healthcare=_sensitive_read_requested(data),
    )
    return jsonify(res)


@app.route('/api/v1/recommend-similar', methods=['GET'])
def api_v1_recommend_similar():
    import graph_embedding
    ont_key = request.args.get('ont', 'mv')
    uri = request.args.get('uri')
    if not uri:
        return jsonify({"error": "uri 파라미터가 필요합니다."}), 400
    g = _load_response_graph(ont_key, request.args.get('project'), _sensitive_read_requested())
    recommendations = graph_embedding.find_similar_nodes(g, uri, top_k=3)
    return jsonify({"target_uri": uri, "count": len(recommendations), "recommendations": recommendations})


@app.route('/api/v1/audit-data', methods=['GET'])
def api_v1_audit_data():
    import audit_report
    ont_key = request.args.get('ont', 'mv')
    project_id = request.args.get('project')
    g = _load_response_graph(ont_key, project_id, _sensitive_read_requested())
    data = audit_report.extract_audit_trail(g, ont_key, project_id)
    return jsonify(data)


@app.route('/api/v1/audit-report', methods=['GET'])
def api_v1_audit_report():
    import audit_report
    ont_key = request.args.get('ont', 'mv')
    project_id = request.args.get('project')
    g = _load_response_graph(ont_key, project_id, _sensitive_read_requested())
    data = audit_report.extract_audit_trail(g, ont_key, project_id)
    html = audit_report.render_html_certificate(data)
    return html, 200, {'Content-Type': 'text/html; charset=utf-8'}


@app.route('/api/v1/cross-domain/align', methods=['GET'])
def api_v1_cross_domain_align():
    import cross_domain_bridge
    res = cross_domain_bridge.align_cross_domains()
    return jsonify(res)


@app.route('/api/v1/stream/events', methods=['GET'])
def api_v1_stream_events():
    import event_stream
    return Response(event_stream.sse_event_stream(), mimetype='text/event-stream', headers={
        'Cache-Control': 'no-cache',
        'X-Accel-Buffering': 'no',
        'Connection': 'keep-alive'
    })


@app.route('/api/v1/stream/broadcast', methods=['POST'])
def api_v1_stream_broadcast():
    import event_stream
    data = request.get_json(silent=True) or {}
    ev_type = data.get('event', 'CUSTOM_ALERT')
    payload = data.get('payload', {})
    ev = event_stream.publish_event(ev_type, payload)
    return jsonify({"success": True, "event": ev})


@app.route('/api/v1/stream/history', methods=['GET'])
def api_v1_stream_history():
    import event_stream
    limit = int(request.args.get('limit', 20))
    return jsonify({"history": event_stream.bus.get_history(limit), "active_clients": event_stream.bus.active_subscribers_count()})


@app.route('/api/v1/llm/status', methods=['GET'])
@app.route('/api/v1/codex/status', methods=['GET'])
def api_v1_codex_status():
    return jsonify(codex_jobs.check_codex_status())


@app.route('/api/v1/llm/generate', methods=['POST'])
@app.route('/api/v1/codex/jobs', methods=['POST'])
def api_v1_codex_submit():
    return jsonify(codex_jobs.submit_job(request.get_json(silent=True) or {})), 202


@app.route('/api/v1/codex/jobs', methods=['GET'])
def api_v1_codex_list():
    domain = request.args.get('ont')
    project = request.args.get('project')
    if domain:
        selected_data_path(domain, project)
    return jsonify({'jobs': codex_jobs.list_jobs(domain, project)})


@app.route('/api/v1/codex/jobs/<job_id>', methods=['GET'])
def api_v1_codex_job(job_id):
    return jsonify(codex_jobs.public_job(codex_jobs.load_job(job_id)))


@app.route('/api/v1/codex/jobs/<job_id>/run', methods=['POST'])
def api_v1_codex_run(job_id):
    started = codex_jobs.launch_job(job_id)
    return jsonify({'started': started, 'job': codex_jobs.public_job(codex_jobs.load_job(job_id))}), 202


@app.route('/api/v1/analytics/centrality', methods=['GET'])
def api_v1_analytics_centrality():
    import graph_analytics
    ont_key = request.args.get('ont', 'mv')
    project_id = request.args.get('project')
    top_k = int(request.args.get('top_k', 5))
    g = _load_response_graph(ont_key, project_id, _sensitive_read_requested())
    report = graph_analytics.analyze_graph_topology(g, top_k=top_k)
    return jsonify(report)


# ---- Auth & Audit Endpoints (v3.1) ----
@app.route('/api/v1/auth/identity', methods=['GET'])
def api_v1_auth_identity():
    import auth
    auth_ok, role, identity = auth.get_client_identity()
    return jsonify({"authenticated": auth_ok, "role": role, "identity": identity})


@app.route('/api/v1/auth/audit-logs', methods=['GET'])
def api_v1_auth_audit_logs():
    import auth
    limit = int(request.args.get('limit', 50))
    return jsonify({"audit_logs": auth.get_audit_logs(limit)})


@app.route('/api/v1/auth/audit-integrity', methods=['GET'])
def api_v1_auth_audit_integrity():
    return jsonify(auth.verify_audit_integrity())


# ---- Graph Versioning & Snapshot Endpoints (v3.1) ----
def _snapshot_error(exc):
    return jsonify({'error': str(exc)}), 404 if isinstance(exc, FileNotFoundError) else 400


@app.route('/api/v1/snapshots', methods=['GET'])
def api_v1_snapshots_list():
    import graph_versioning
    domain = request.args.get('ont', 'mv')
    project = request.args.get('project') or None
    selected_data_path(domain, project)
    return jsonify({'snapshots': graph_versioning.list_snapshots(domain, project_id=project)})


@app.route('/api/v1/snapshots/create', methods=['POST'])
def api_v1_snapshots_create():
    import graph_versioning, event_stream
    data = request.get_json(silent=True) or {}
    domain, project = data.get('ont', 'mv'), data.get('project') or None
    path = selected_data_path(domain, project)
    try:
        with graph_file_lock(path):
            g = _load_data_graph(domain, project)
            _validate_candidate(g, domain, project)
            meta = graph_versioning.create_snapshot(domain, g, description=str(data.get('description', '사용자 생성 스냅샷'))[:2000], project_id=project)
    except (ValueError, FileNotFoundError) as exc:
        if isinstance(exc, project_store.ProjectError):
            raise
        return _snapshot_error(exc)
    event_stream.publish_event('GRAPH_SNAPSHOT_CREATED', meta)
    return jsonify({'success': True, 'snapshot': meta})


@app.route('/api/v1/snapshots/rollback', methods=['POST'])
def api_v1_snapshots_rollback():
    import graph_versioning, event_stream
    data = request.get_json(silent=True) or {}
    domain, project = data.get('ont', 'mv'), data.get('project') or None
    path = selected_data_path(domain, project)
    try:
        snapshot_id = data.get('snapshot_id')
        with graph_file_lock(path):
            graph_versioning.validate_metadata_scope(snapshot_id, domain, project)
            candidate = graph_versioning.load_snapshot_graph(snapshot_id)
            _validate_candidate(candidate, domain, project)
            current = _load_data_graph(domain, project)
            res = graph_versioning.rollback_to_snapshot(domain, snapshot_id, current, destination_path=path, project_id=project)
    except (ValueError, FileNotFoundError) as exc:
        if isinstance(exc, project_store.ProjectError):
            raise
        return _snapshot_error(exc)
    event_stream.publish_event('GRAPH_ROLLBACK_EXECUTED', res)
    return jsonify(res)


@app.route('/api/v1/snapshots/diff', methods=['GET'])
def api_v1_snapshots_diff():
    import graph_versioning
    domain, project = request.args.get('ont', 'mv'), request.args.get('project') or None
    selected_data_path(domain, project)
    snap_a, snap_b = request.args.get('snapshot_a'), request.args.get('snapshot_b')
    try:
        graph_versioning.validate_metadata_scope(snap_a, domain, project)
        g_a = graph_versioning.load_snapshot_graph(snap_a)
        if snap_b:
            graph_versioning.validate_metadata_scope(snap_b, domain, project)
            g_b = graph_versioning.load_snapshot_graph(snap_b)
        else:
            g_b = _load_data_graph(domain, project)
        g_a, _ = _apply_read_policy(g_a, domain, _sensitive_read_requested())
        g_b, _ = _apply_read_policy(g_b, domain, _sensitive_read_requested())
        diff = graph_versioning.compute_graph_diff(g_a, g_b)
    except (ValueError, FileNotFoundError) as exc:
        return _snapshot_error(exc)
    return jsonify({'snapshot_a': snap_a, 'snapshot_b': snap_b or 'current', 'diff': diff})


# ---- OWL 2 RL Semantic Deductive Reasoning (v3.1) ----
@app.route('/api/v1/reasoning/expand', methods=['POST'])
def api_v1_reasoning_expand():
    import owl_reasoner
    import event_stream
    data = request.get_json(silent=True) or {}
    domain = data.get('ont', 'mv')
    semantics = data.get('semantics', 'owlrl')
    if semantics not in ('owlrl', 'rdfs'):
        return jsonify({'error': 'semantics는 owlrl 또는 rdfs여야 합니다.'}), 400
    base_g = _load_response_graph(domain, data.get('project'), _sensitive_read_requested(data))
    work_g = rdflib.Graph()
    for tr in base_g:
        work_g.add(tr)
    res = owl_reasoner.run_owl_deductive_closure(work_g, semantics=semantics)
    event_stream.publish_event("OWL_REASONING_EXPANDED", {
        "domain": domain,
        "inferred_count": res["inferred_count"],
        "semantics": semantics
    })
    return jsonify(res)


# =====================================================================
# Cognitive Breakthrough Engines (v2 Next-Gen Semantic APIs)
# =====================================================================

@app.route('/api/v2/causal/what-if', methods=['POST'])
def api_v2_causal_what_if():
    """인과 추론 그래프(SCM) 기반 What-If 반사실 시뮬레이션 엔드포인트"""
    data = request.get_json(silent=True) or {}
    interventions = data.get('interventions', {})
    if not interventions:
        return jsonify({"error": "interventions 딕셔너리(예: {'BGM_Tempo_BPM': 160})를 전달해주세요."}), 400
    try:
        from causal_engine import CausalKnowledgeGraph
        ckg = CausalKnowledgeGraph()
        result = ckg.simulate_what_if(interventions)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"인과 시뮬레이션 실패: {str(e)}"}), 500


@app.route('/api/v2/evolver/mine-and-verify', methods=['POST'])
def api_v2_evolver_mine_and_verify():
    """자가 진화형 온톨로지 루프: 신규 개념 발굴 및 가상 샌드박스 SHACL/OWL 사전 심사"""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '').strip()
    domain = data.get('ont', 'mv')
    if not text:
        return jsonify({"error": "text 파라미터를 입력해주세요."}), 400
    try:
        from ontology_evolver import OntologyEvolver
        evolver = OntologyEvolver()
        candidates = evolver.mine_candidate_concepts(text, domain=domain)
        ttl = evolver.generate_candidate_ttl(candidates, domain=domain)
        base_g = load_graph(domain, data.get('project'))
        verdict = evolver.sandbox_verify_evolution(base_g, ttl, domain=domain)
        return jsonify({
            "candidates": candidates,
            "generated_ttl": ttl,
            "verdict": verdict
        })
    except Exception as e:
        return jsonify({"error": f"온톨로지 자가 진화 분석 실패: {str(e)}"}), 500


@app.route('/api/v2/kge/verify-axiom', methods=['POST'])
def api_v2_kge_verify_axiom():
    """기하학적 지식 임베딩(Box Embeddings) 기반 0% 환각 공리 검증"""
    data = request.get_json(silent=True) or {}
    axiom_type = data.get('axiom', 'subclass').lower()  # subclass | disjoint
    class_a = data.get('class_a', '')
    class_b = data.get('class_b', '')
    if not class_a or not class_b:
        return jsonify({"error": "class_a와 class_b를 명시해주세요."}), 400
    try:
        from geometric_kge import GeometricKGEmbedding
        kge = GeometricKGEmbedding(dim=8)
        if axiom_type == 'subclass':
            ok, msg = kge.verify_subclass_axiom(class_a, class_b)
        elif axiom_type == 'disjoint':
            ok, msg = kge.verify_disjointness_axiom(class_a, class_b)
        else:
            return jsonify({"error": "지원되지 않는 axiom 타입입니다 (subclass 또는 disjoint)."}), 400
        return jsonify({"verified": ok, "message": msg, "geometry": "HyperBox Polytope"})
    except Exception as e:
        return jsonify({"error": f"기하학적 공리 검증 실패: {str(e)}"}), 500


@app.route('/api/v2/arbiter/arbitrate', methods=['POST'])
def api_v2_arbiter_arbitrate():
    """멀티 에이전트 온톨로지 법정: 에이전트 갈등에 대한 파레토 최적 중재 판결문 발부"""
    data = request.get_json(silent=True) or {}
    title = data.get('title', 'General Multi-Agent Conflict Session')
    proposals = data.get('proposals', [])
    if not proposals:
        return jsonify({"error": "proposals 리스트를 전달해주세요."}), 400
    try:
        from semantic_arbiter import SemanticArbiter
        arbiter = SemanticArbiter()
        verdict = arbiter.arbitrate_dispute(title, proposals)
        return jsonify(verdict)
    except Exception as e:
        return jsonify({"error": f"온톨로지 법정 중재 실패: {str(e)}"}), 500


@app.route('/api/v2/temporal/snapshot', methods=['GET', 'POST'])
def api_v2_temporal_snapshot():
    """4D Fluents 타임머신 그래프: 특정 시점(t) 지식 그래프 스냅샷 복원"""
    if request.method == 'GET':
        t_val = float(request.args.get('timestamp', 0.0))
    else:
        data = request.get_json(silent=True) or {}
        t_val = float(data.get('timestamp', 0.0))
    try:
        from temporal_graph import TemporalKnowledgeGraph
        tkg = TemporalKnowledgeGraph()
        snapshot = tkg.query_point_in_time(t_val)
        return jsonify(snapshot)
    except Exception as e:
        return jsonify({"error": f"타임머신 스냅샷 복원 실패: {str(e)}"}), 500


# =====================================================================
# Frontier Cognitive Engines & Generative Digital Twin (v3 APIs)
# =====================================================================

@app.route('/digital-twin')
def view_digital_twin():
    """실시간 인터랙티브 비주얼 디지털 트윈 UI 렌더링"""
    return render_template('digital_twin.html')


@app.route('/api/v3/distill/dataset', methods=['GET', 'POST'])
def api_v3_distill_dataset():
    """온톨로지 공리 기반 LLM LoRA 미세조정용 합성 QA 데이터셋 증류"""
    data = request.get_json(silent=True) or {}
    domain = data.get('ont') or request.args.get('ont', 'mv')
    limit = int(data.get('limit') or request.args.get('limit', 30))
    try:
        from knowledge_distiller import KnowledgeDistiller
        g = load_graph(domain, data.get('project'))
        distiller = KnowledgeDistiller(g)
        samples = distiller.synthesize_lora_dataset(domain=domain, max_samples=limit)
        lora_cfg = distiller.export_lora_config(len(samples))
        return jsonify({
            "domain": domain,
            "samples_count": len(samples),
            "lora_hyperparameters": lora_cfg,
            "training_dataset": samples
        })
    except Exception as e:
        return jsonify({"error": f"지식 증류 데이터셋 생성 실패: {str(e)}"}), 500


@app.route('/api/v3/aesthetic/tension-curve', methods=['GET', 'POST'])
def api_v3_aesthetic_tension_curve():
    """인간 감성 및 미학적 텐션 곡선 T(t) 계산 및 카타르시스 피크 검출"""
    if request.method == 'GET':
        bpm = float(request.args.get('bpm', 128.0))
        dur = float(request.args.get('duration', 20.0))
        drop = float(request.args.get('drop', 8.0))
    else:
        data = request.get_json(silent=True) or {}
        bpm = float(data.get('bpm', 128.0))
        dur = float(data.get('duration', 20.0))
        drop = float(data.get('drop', 8.0))
    try:
        from aesthetic_tension import AestheticTensionEngine
        engine = AestheticTensionEngine()
        res = engine.compute_tension_curve(duration_sec=dur, bpm=bpm, drop_timestamp=drop)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"미학 텐션 곡선 계산 실패: {str(e)}"}), 500


@app.route('/api/v3/probabilistic/infer', methods=['POST'])
def api_v3_probabilistic_infer():
    """확률적 소프트 로직 (PSL) 기반 연속 진리값 불확실성 추론"""
    data = request.get_json(silent=True) or {}
    facts = data.get('facts', {})
    if not facts:
        # 기본 관측 사실 예시 주입
        facts = {"HighAudioEnergy": 0.88, "FastCutCadence": 0.75, "DarkLighting": 0.20}
    try:
        from probabilistic_logic import ProbabilisticLogicEngine
        engine = ProbabilisticLogicEngine()
        result = engine.infer(facts)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"확률적 소프트 로직 추론 실패: {str(e)}"}), 500


# =====================================================================
# Ultra-Tier Frontier Engines (v4 Ultra Cognitive APIs)
# =====================================================================

@app.route('/api/v4/wormhole/teleport', methods=['POST'])
def api_v4_wormhole_teleport():
    """범주론 기반 시맨틱 웜홀: 도메인 간 대수적 동형사상(Isomorphism) 해법 순간이동"""
    data = request.get_json(silent=True) or {}
    src = data.get('source_domain', 'devops')
    tgt = data.get('target_domain', 'mv')
    prob = data.get('problem', 'StepFail')
    try:
        from semantic_wormhole import SemanticWormholeEngine
        engine = SemanticWormholeEngine()
        result = engine.teleport_solution(src, tgt, prob)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"시맨틱 웜홀 전이 실패: {str(e)}"}), 500


@app.route('/api/v4/zk/prove-and-verify', methods=['POST'])
def api_v4_zk_prove_and_verify():
    """영지식 시맨틱 증명 (ZK-KG): 민감 정보 0% 노출 암호학적 SHACL 규칙 증명 및 검증"""
    data = request.get_json(silent=True) or {}
    private_facts = data.get('private_facts', {"patient_age": 34, "risk_score": 42})
    rules = data.get('rules', {"patient_age": {"type": "minInclusive", "value": 18}})
    try:
        from zk_knowledge_graph import ZKKnowledgeEngine
        zk = ZKKnowledgeEngine()
        proof_res = zk.generate_zk_proof(private_facts, rules)
        verify_res = zk.verify_zk_proof(proof_res["zk_proof"], rules)
        return jsonify({
            "zk_proof_generation": proof_res,
            "zero_knowledge_verification": verify_res
        })
    except Exception as e:
        return jsonify({"error": f"영지식 증명 처리 실패: {str(e)}"}), 500


@app.route('/api/v4/quantum/superposition', methods=['GET', 'POST'])
def api_v4_quantum_superposition():
    """양자 인지 중첩 그래프: 개념 노드의 힐베르트 복소수 상태 벡터 및 중첩 확률 조회"""
    node_name = request.args.get('node', 'NeonMoodyDark') if request.method == 'GET' else (request.get_json(silent=True) or {}).get('node', 'NeonMoodyDark')
    try:
        from quantum_cognitive import QuantumCognitiveEngine
        engine = QuantumCognitiveEngine()
        superposition = engine.get_node_superposition(node_name)
        return jsonify({"node": node_name, "superposition": superposition})
    except Exception as e:
        return jsonify({"error": f"양자 상태 조회 실패: {str(e)}"}), 500


@app.route('/api/v4/quantum/collapse', methods=['POST'])
def api_v4_quantum_collapse():
    """양자 인지 중첩 그래프: 질의 관측 맥락(Observer Context)에 의한 파동함수 붕괴 및 고유상태 확정"""
    data = request.get_json(silent=True) or {}
    node_name = data.get('node', 'NeonMoodyDark')
    context = data.get('context', '슬픈 이별의 비극적 야경 씬')
    try:
        from quantum_cognitive import QuantumCognitiveEngine
        engine = QuantumCognitiveEngine()
        res = engine.observe_and_collapse(node_name, context)
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"양자 상태 붕괴 실패: {str(e)}"}), 500


@app.route('/api/v4/immune/scan-and-heal', methods=['POST'])
def api_v4_immune_scan_and_heal():
    """자가 치유 시맨틱 면역 체계: 적대적 인젝션·지식 오염 탐식 및 항체 생성 격리 롤백"""
    data = request.get_json(silent=True) or {}
    payload = data.get('payload', '')
    if not payload:
        return jsonify({"error": "스캔할 payload 문자열을 전달해주세요."}), 400
    try:
        from semantic_immune_system import SemanticImmuneSystem
        immune = SemanticImmuneSystem()
        defense_report = immune.scan_and_neutralize(payload, domain=data.get('domain', 'mv'))
        return jsonify(defense_report)
    except Exception as e:
        return jsonify({"error": f"시맨틱 면역 검사 실패: {str(e)}"}), 500


# =====================================================================
# Singular & Embodied Frontier Engines (v5 Singular APIs)
# =====================================================================

@app.route('/api/v5/spatial/simulate', methods=['POST'])
def api_v5_spatial_simulate():
    """3D 공간 및 물리 시뮬레이션 월드 모델: 드론 비행, 충돌 여유 공간, 광학 플레어 연산"""
    data = request.get_json(silent=True) or {}
    speed = float(data.get('speed_ms', 4.0))
    wind = data.get('wind_vector', {"x": 0.5, "y": 0.0, "z": 0.0})
    duration = float(data.get('duration_sec', 2.0))
    try:
        from spatial_world_model import SpatialWorldModelEngine
        engine = SpatialWorldModelEngine()
        result = engine.simulate_drone_flight(drone_speed_ms=speed, wind_vector=wind, duration_sec=duration)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"3D 물리 공간 시뮬레이션 실패: {str(e)}"}), 500


@app.route('/api/v5/multiverse/mcts-search', methods=['POST'])
def api_v5_multiverse_mcts_search():
    """평행 우주 분기 및 몬테카를로 트리 탐색 (MCTS): 최적 미래 황금 궤적(Golden Path) 도출"""
    data = request.get_json(silent=True) or {}
    iterations = int(data.get('iterations', 250))
    try:
        from multiverse_mcts import MultiverseMCTSEngine
        engine = MultiverseMCTSEngine()
        result = engine.search_golden_path(iterations=iterations)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"멀티버스 MCTS 탐색 실패: {str(e)}"}), 500


@app.route('/api/v5/darwin/evolve', methods=['POST'])
def api_v5_darwin_evolve():
    """다윈주의적 스키마 유전 진화기: 자연선택 교배/돌연변이를 통한 슈퍼 스키마 진화"""
    data = request.get_json(silent=True) or {}
    generations = int(data.get('generations', 10))
    pop_size = int(data.get('population_size', 10))
    try:
        from darwinian_evolver import DarwinianSchemaEvolver
        evolver = DarwinianSchemaEvolver()
        result = evolver.evolve_schemas(generations=generations, population_size=pop_size)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"다윈주의적 스키마 진화 실패: {str(e)}"}), 500


@app.route('/api/v5/neurobio/resonate', methods=['POST'])
def api_v5_neurobio_resonate():
    """뉴로-바이오 실시간 생체 공명 온톨로지: EEG/HRV 기반 인지 부하 산출 및 서브그래프 동적 적응"""
    data = request.get_json(silent=True) or {}
    eeg = data.get('eeg_bands', {"alpha": 0.35, "beta": 0.65, "gamma": 0.40})
    hrv = float(data.get('hrv_rmssd', 38.0))
    domain = data.get('domain', 'mv')
    try:
        from neuro_bio_resonance import NeuroBioResonanceEngine
        engine = NeuroBioResonanceEngine()
        bio_state = engine.evaluate_biometric_state(eeg, hrv_rmssd=hrv)
        resonance = engine.resonate_subgraph(domain, bio_state)
        return jsonify(resonance)
    except Exception as e:
        return jsonify({"error": f"뉴로-바이오 공명 처리 실패: {str(e)}"}), 500


# =====================================================================
# Transcendent Frontier Engines (v6 Transcendent APIs)
# =====================================================================

@app.route('/api/v6/hdc/query', methods=['POST'])
def api_v6_hdc_query():
    """초고차원 벡터 기호 연상 기억 (HDC / VSA): O(1) 홀로그래픽 언바인딩 연상 질의"""
    data = request.get_json(silent=True) or {}
    triples = data.get('triples', [
        ["MV_Cyberpunk", "hasDirector", "Alice"],
        ["MV_Cyberpunk", "hasBPM", "140"]
    ])
    s = data.get('query_subject', 'MV_Cyberpunk')
    p = data.get('query_predicate', 'hasDirector')
    candidates = data.get('candidates', None)
    try:
        from hyperdimensional_vsa import HyperdimensionalVSA
        hdc = HyperdimensionalVSA(dim=2048)
        graph_vec = hdc.encode_graph(triples)
        ranked = hdc.query_object(graph_vec, s, p, candidates=candidates)
        top_match = ranked[0][0] if ranked else None
        top_sim = ranked[0][1] if ranked else 0.0
        return jsonify({
            "status": "success",
            "query": {"subject": s, "predicate": p},
            "top_match": top_match,
            "top_similarity": top_sim,
            "ranked_matches": ranked[:5],
            "dimension": hdc.dim
        })
    except Exception as e:
        return jsonify({"error": f"HDC VSA 연상 질의 실패: {str(e)}"}), 500


@app.route('/api/v6/active-inference/evaluate', methods=['POST'])
def api_v6_active_inference_evaluate():
    """프리스턴 능동 추론 & 변분 자유 에너지 (FEP) 최소화: 인식론적 호기심 프로브 및 섀넌 놀라움 산출"""
    data = request.get_json(silent=True) or {}
    observations = data.get('observations', {
        "mv": {"sample_count": 8, "verified_triples_ratio": 0.92, "unresolved_anomalies_count": 0},
        "devops": {"sample_count": 3, "verified_triples_ratio": 0.65, "unresolved_anomalies_count": 2}
    })
    try:
        from active_inference_fep import ActiveInferenceEngine
        engine = ActiveInferenceEngine()
        result = engine.evaluate_free_energy(observations)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"능동 추론 FEP 산출 실패: {str(e)}"}), 500


@app.route('/api/v6/autopoiesis/repair', methods=['POST'])
def api_v6_autopoiesis_repair():
    """오토포이에시스 자기 컴파일 콰인: 내부 유전체(Genome) 기반 스키마 병변 자가 탐지 및 무결점 재합성"""
    data = request.get_json(silent=True) or {}
    active_classes = data.get('active_classes', ["PatientRecord"])
    active_props = data.get('active_properties', ["hasPatientId"])
    try:
        from autopoietic_quine import AutopoieticQuine
        quine = AutopoieticQuine()
        integrity = quine.inspect_graph_integrity(active_classes, active_props)
        repair_res = quine.synthesize_self_repair(integrity["lesions"])
        return jsonify({
            "status": repair_res["status"],
            "structural_health_pre_repair": integrity["structural_health_score"],
            "lesion_count": integrity["lesion_count"],
            "repaired_count": repair_res["repaired_components_count"],
            "synthesized_triples": repair_res["generated_rdf_triples"],
            "genome_dna": quine.genome_dna
        })
    except Exception as e:
        return jsonify({"error": f"오토포이에시스 자가 치유 실패: {str(e)}"}), 500


@app.route('/api/v6/crdt-swarm/sync', methods=['POST'])
def api_v6_crdt_swarm_sync():
    """비잔틴 내결함성 시맨틱 CRDT 스웜: 가십 프로토콜 전파 및 반격자(Semilattice) 무모순 합의 도출"""
    data = request.get_json(silent=True) or {}
    node_count = int(data.get('node_count', 4))
    simulate_byzantine = bool(data.get('simulate_byzantine', True))
    try:
        from semantic_crdt_swarm import SemanticSwarmOrchestrator
        swarm = SemanticSwarmOrchestrator(node_count=node_count)
        swarm.nodes["agent-node-01"].add_triple("Song_Master", "mv:hasTempo", "128")
        swarm.nodes["agent-node-02"].add_triple("Scene_Climax", "mv:hasLighting", "NeonDark")
        if simulate_byzantine:
            bad = swarm.introduce_byzantine_node("agent-byzantine-99")
            bad.add_triple("MaliciousExploit", "rdf:type", "Attack")
            bad.add_triple("PatientRecord_X", "rdf:type", "MusicVideo")
        # Run epidemic gossip rounds until convergence
        last_round = None
        for _ in range(3):
            last_round = swarm.execute_epidemic_gossip_round()
        return jsonify(last_round)
    except Exception as e:
        return jsonify({"error": f"시맨틱 CRDT 스웜 동기화 실패: {str(e)}"}), 500


# =====================================================================
# Dynamic Singularity Engines (v7 Dynamic APIs)
# =====================================================================

@app.route('/api/v7/tda/persistent-homology', methods=['POST'])
def api_v7_tda_persistent_homology():
    """위상수학적 데이터 분석 (TDA) & 지속성 호몰로지: 비에토리-립스 여과, 베티수, 위상 바코드 산출"""
    data = request.get_json(silent=True) or {}
    distances = data.get('distances', [
        ["ArtisticConcept", "TechnicalSpec", 0.3],
        ["TechnicalSpec", "CommercialCampaign", 0.4],
        ["CommercialCampaign", "ArtisticConcept", 0.5]
    ])
    max_eps = float(data.get('max_epsilon', 1.0))
    try:
        from topological_tda import VietorisRipsTDA
        tda = VietorisRipsTDA()
        for item in distances:
            tda.add_distance(str(item[0]), str(item[1]), float(item[2]))
        result = tda.compute_persistent_homology(max_epsilon=max_eps)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"위상수학적 TDA 분석 실패: {str(e)}"}), 500


@app.route('/api/v7/neuromorphic/simulate-spikes', methods=['POST'])
def api_v7_neuromorphic_simulate_spikes():
    """신경형 스파이킹 신경망 & STDP 가소성: LIF 활동전위 발화 및 시간차 의존 시냅스 가소성 강화/약화"""
    data = request.get_json(silent=True) or {}
    synapses = data.get('synapses', [["DirectorAgent", "ShotAgent", 0.4]])
    stimuli = data.get('external_stimuli', {"DirectorAgent": [10.0]})
    duration = float(data.get('duration_ms', 80.0))
    try:
        from neuromorphic_spiking import NeuromorphicSpikingKG
        nkg = NeuromorphicSpikingKG()
        for syn in synapses:
            nkg.add_relation_synapse(str(syn[0]), str(syn[1]), float(syn[2]))
        result = nkg.simulate(duration_ms=duration, external_stimuli=stimuli)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"신경형 스파이킹 시뮬레이션 실패: {str(e)}"}), 500


@app.route('/api/v7/neural-ode/integrate', methods=['POST'])
def api_v7_neural_ode_integrate():
    """연속 시간 신경 상미분 방정식 (Neural ODE): 룬게-쿠타 4차(RK4) 수치적분 및 연속 위상 궤적 추적"""
    data = request.get_json(silent=True) or {}
    z0 = data.get('initial_state', [1.0, 1.0, 1.0])
    duration = float(data.get('duration', 2.0))
    dt = float(data.get('dt', 0.05))
    control = float(data.get('control_input', 0.0))
    try:
        from continuous_neural_ode import ContinuousNeuralODE
        ode = ContinuousNeuralODE()
        result = ode.integrate_trajectory(z0, t_span=(0.0, duration), dt=dt, control_input=control)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"연속 Neural ODE 수치적분 실패: {str(e)}"}), 500


@app.route('/api/v7/gauge/holonomy', methods=['POST'])
def api_v7_gauge_holonomy():
    """게이지 장론적 파이버 번들 & 홀로노미: 폐곡선 맥락 순환 곡률 플럭스 측정 및 게이지 정렬"""
    data = request.get_json(silent=True) or {}
    connections = data.get('connections', [
        ["DevOps", "MV", 0.785],
        ["MV", "Healthcare", 1.047],
        ["Healthcare", "DevOps", -1.571]
    ])
    cycle = data.get('loop_cycle', ["DevOps", "MV", "Healthcare", "DevOps"])
    ref = data.get('reference_domain', 'DevOps')
    try:
        from gauge_holonomy import SemanticGaugeBundle
        bundle = SemanticGaugeBundle()
        for conn in connections:
            bundle.add_connection(str(conn[0]), str(conn[1]), float(conn[2]))
        hol_res = bundle.calculate_loop_holonomy(cycle)
        align_res = bundle.align_gauge_symmetry(ref)
        hol_res["gauge_alignment"] = align_res
        return jsonify(hol_res)
    except Exception as e:
        return jsonify({"error": f"게이지 홀로노미 연산 실패: {str(e)}"}), 500


# =====================================================================
# Metacognitive Transfinite Singularity Engines (v8 APIs)
# =====================================================================

@app.route('/api/v8/poincare/embed-and-distance', methods=['POST'])
def api_v8_poincare_embed_and_distance():
    """푸앵카레 볼 쌍곡 기하 임베딩: 음의 곡률(K=-1) 공간 측지선 거리 및 호로스피어 계층 분해"""
    data = request.get_json(silent=True) or {}
    pairs = data.get('pairs', [
        ["CreativeWork", "MusicVideo"],
        ["MusicVideo", "IndieMV"],
        ["CreativeWork", "Movie"]
    ])
    root = data.get('root', None)
    dim = int(data.get('dim', 3))
    try:
        from poincare_hyperbolic import PoincareBall
        pb = PoincareBall(dim=dim)
        result = pb.embed_tree_hierarchy(pairs, root=root)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"푸앵카레 쌍곡 임베딩 연산 실패: {str(e)}"}), 500


@app.route('/api/v8/sgwt/wavelet-transform', methods=['POST'])
def api_v8_sgwt_wavelet_transform():
    """스펙트럴 그래프 웨이블릿 변환 (SGWT): 라플라시안 체비쇼프 고속 필터링 및 다중해상도 이상징후 탐지"""
    data = request.get_json(silent=True) or {}
    edges = data.get('edges', [
        ["DevOps_CI", "Pipeline_01", 1.0],
        ["Pipeline_01", "TestRunner", 1.0],
        ["TestRunner", "DeployProd", 1.0],
        ["AnomalyNode", "TestRunner", 0.3]
    ])
    scales = data.get('scales', [0.5, 1.5, 3.0])
    try:
        from spectral_graph_wavelet import SpectralGraphWavelet
        sgwt = SpectralGraphWavelet()
        result = sgwt.compute_multiresolution_spectrum(edges, scales=scales)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"스펙트럴 그래프 웨이블릿 변환 실패: {str(e)}"}), 500


@app.route('/api/v8/free-monad/compose-and-execute', methods=['POST'])
def api_v8_free_monad_compose_and_execute():
    """범주론적 자유 모나드(Free Monad) 엔진: 대수적 효과 분리, 모나드 법칙 검증, 가역 트랜잭션 실행"""
    data = request.get_json(silent=True) or {}
    operations = data.get('operations', [
        {"op": "ASSERT_TRIPLE", "s": "MV_Master", "p": "hasDirector", "o": "Alice"}
    ])
    try:
        from free_monad_engine import FreeMonad, FreeMonadInterpreter
        laws_verification = FreeMonad.pure(42).verify_monad_laws()

        # Build monadic program pipeline
        current_program = FreeMonad.pure("PipelineSuccess")
        for op in reversed(operations):
            op_type = op.get("op", "ASSERT_TRIPLE")
            params = {k: v for k, v in op.items() if k != "op"}
            current_program = FreeMonad.suspend(op_type, params, lambda res, nxt=current_program: nxt)

        # Prepend checkpoint
        full_program = FreeMonad.suspend("CREATE_CHECKPOINT", {"checkpoint_id": "tx_root"}, lambda r: current_program)

        interpreter = FreeMonadInterpreter()
        res = interpreter.interpret(full_program)
        res["monad_laws"] = laws_verification
        return jsonify(res)
    except Exception as e:
        return jsonify({"error": f"자유 모나드 파이프라인 실행 실패: {str(e)}"}), 500


@app.route('/api/v8/transfinite/dissolve-paradox', methods=['POST'])
def api_v8_transfinite_dissolve_paradox():
    """초한 서수(Transfinite Ordinal) 메타-인지 재귀기: Tarski 진리 계층 상승 및 괴델 자기참조 역설 용해"""
    data = request.get_json(silent=True) or {}
    statements = data.get('statements', [
        {"id": "ParadoxStmt", "text": "Statement ParadoxStmt is invalid", "negates": []},
        {"id": "PolicyFast", "text": "Enforce fast release", "negates": ["PolicyStrict"]},
        {"id": "PolicyStrict", "text": "Enforce strict security", "negates": ["PolicyFast"]}
    ])
    try:
        from transfinite_metacognition import TransfiniteMetacognition
        meta = TransfiniteMetacognition()
        detected = meta.detect_self_referential_paradox(statements)
        dissolved_results = [meta.dissolve_paradox_via_transfinite_ascension(p) for p in detected]
        consistency = meta.verify_godelian_consistency()
        return jsonify({
            "status": "paradox_resolution_completed",
            "detected_paradoxes_count": len(detected),
            "resolved_paradoxes_count": len(dissolved_results),
            "dissolved_paradoxes": dissolved_results,
            "transfinite_consistency": consistency
        })
    except Exception as e:
        return jsonify({"error": f"초한 서수 역설 용해 실패: {str(e)}"}), 500


if __name__ == '__main__':
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', '5000'))
    print("==========================================================")
    print(f"  온톨로지 웹 브라우저 관리 서버 실행 중: http://{host}:{port}  ")
    print("==========================================================")
    auth.validate_bind_host(host)
    app.run(host=host, port=port, debug=False)
