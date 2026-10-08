"""
Natural Language to SPARQL & GraphRAG Query Engine
Translates Korean/English natural language inquiries into standard SPARQL queries,
executes them against the active domain knowledge graph, and formats natural answers.
Works offline via deterministic pattern matching. No LLM or model API is called.
"""

import os
import re
import rdflib

RDFS = rdflib.RDFS
RDF = rdflib.RDF

# Standard Domain Prefixes
PREFIXES = {
    "mv": """PREFIX mv: <https://example.org/mv#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
""",
    "e2e": """PREFIX mv: <https://example.org/mv#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
""",
    "devops": """PREFIX devops: <https://example.org/devops#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
""",
    "agent": """PREFIX ag: <https://example.org/agent#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
""",
    "ecommerce": """PREFIX ecom: <http://example.org/ontology/ecommerce#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
""",
    "healthcare": """PREFIX health: <http://example.org/ontology/healthcare#>
PREFIX prov: <http://www.w3.org/ns/prov#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
""",
    "academic": """PREFIX ex: <https://example.org/ontology/academic#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
"""
}

# Domain Intent Patterns
INTENT_PATTERNS = [
    # 1. Tasks / Runs / Status
    {
        "keys": ["작업", "태스크", "task", "상태", "status", "진행", "완료", "실행", "run"],
        "domains": ["mv", "e2e"],
        "sparql": """SELECT DISTINCT ?taskName ?status ?agentName ?model WHERE {
  ?task rdf:type/rdfs:subClassOf* mv:GenerationTask ;
        rdfs:label ?taskName ;
        mv:status ?status ;
        prov:wasAssociatedWith ?agent .
  ?agent rdfs:label ?agentName .
  OPTIONAL { ?task mv:modelVersion ?model }
} ORDER BY ?taskName""",
        "template": "총 {count}건의 작업이 조회되었습니다.\n{items}"
    },
    {
        "keys": ["작업", "태스크", "task", "목표", "objective"],
        "domains": ["agent"],
        "sparql": """SELECT ?taskName ?objective ?agentName WHERE {
  ?task a ag:Task ;
        rdfs:label ?taskName ;
        ag:taskObjective ?objective ;
        ag:assignedTo ?agent .
  ?agent rdfs:label ?agentName .
} ORDER BY ?taskName""",
        "template": "등록된 에이전트 작업 {count}건입니다.\n{items}"
    },
    {
        "keys": ["실행", "이력", "run", "로그"],
        "domains": ["agent"],
        "sparql": """SELECT ?run ?task ?status ?agentName WHERE {
  ?run rdf:type/rdfs:subClassOf* ag:TaskRun ;
       ag:implementsTask ?task ;
       ag:status ?status ;
       prov:wasAssociatedWith ?agent .
  ?agent rdfs:label ?agentName .
} ORDER BY ?run""",
        "template": "에이전트 작업 실행 이력 {count}건입니다.\n{items}"
    },
    # 2. Assets / Files / Lyrics
    {
        "keys": ["에셋", "파일", "asset", "file", "음원", "이미지", "영상", "media"],
        "domains": ["mv", "e2e"],
        "sparql": """SELECT DISTINCT ?assetName ?fileUri ?taskName WHERE {
  ?asset rdf:type/rdfs:subClassOf* mv:MediaAsset ;
         mv:fileUri ?fileUri .
  OPTIONAL { ?asset rdfs:label ?assetName }
  OPTIONAL { ?asset prov:wasGeneratedBy [ rdfs:label ?taskName ] }
} ORDER BY ?assetName""",
        "template": "등록된 미디어 에셋 {count}건입니다.\n{items}"
    },
    {
        "keys": ["가사", "자막", "lyrics", "subtitle", "번역", "translation"],
        "domains": ["mv", "e2e"],
        "sparql": """SELECT DISTINCT ?asset ?label ?fileUri WHERE {
  ?asset a ?type ;
         mv:fileUri ?fileUri .
  OPTIONAL { ?asset rdfs:label ?label }
  FILTER(CONTAINS(STR(?type), "Lyrics") || CONTAINS(STR(?type), "Subtitle") || CONTAINS(LCASE(STR(?fileUri)), "lyrics") || CONTAINS(LCASE(STR(?fileUri)), "vtt") || CONTAINS(LCASE(STR(?fileUri)), "srt"))
}""",
        "template": "가사 및 자막 관련 에셋 {count}건을 찾았습니다.\n{items}"
    },
    # 3. Timeline / Shots
    {
        "keys": ["장면", "씬", "shot", "순서", "타임라인", "timeline", "시간", "초"],
        "domains": ["mv", "e2e"],
        "sparql": """SELECT ?shotName ?order ?startSec ?endSec ?imageName WHERE {
  ?shot a mv:Shot ;
        rdfs:label ?shotName ;
        mv:orderIndex ?order ;
        mv:startSecond ?startSec ;
        mv:endSecond ?endSec .
  OPTIONAL { ?shot mv:usesImage [ rdfs:label ?imageName ] }
} ORDER BY ?order""",
        "template": "타임라인 장면 구성 {count}건입니다.\n{items}"
    },
    # 4. Agents / Roles
    {
        "keys": ["에이전트", "agent", "누가", "담당자", "역할", "역량", "capability"],
        "domains": ["agent"],
        "sparql": """SELECT ?agent ?name ?role ?capName WHERE {
  ?agent a ag:AutonomousAgent ;
         rdfs:label ?name .
  OPTIONAL { ?agent ag:role ?role }
  OPTIONAL { ?agent ag:hasCapability [ rdfs:label ?capName ] }
} ORDER BY ?name""",
        "template": "등록된 자율 에이전트 {count}명입니다.\n{items}"
    },
    {
        "keys": ["에이전트", "agent", "누가", "담당자"],
        "domains": ["mv", "e2e"],
        "sparql": """SELECT DISTINCT ?agentName ?taskName WHERE {
  ?agent a mv:Agent ;
         rdfs:label ?agentName .
  OPTIONAL { ?task prov:wasAssociatedWith ?agent ; rdfs:label ?taskName }
} ORDER BY ?agentName""",
        "template": "파이프라인 참여 에이전트 {count}명입니다.\n{items}"
    },
    # 5. DevOps / CI/CD
    {
        "keys": ["빌드", "배포", "build", "deploy", "파이프라인", "pipeline", "커밋", "commit", "실패"],
        "domains": ["devops"],
        "sparql": """SELECT ?run ?commit ?status ?agentName WHERE {
  ?run a devops:PipelineRun ;
       devops:commitId ?commit ;
       devops:runStatus ?status ;
       devops:triggeredBy ?agent .
  ?agent rdfs:label ?agentName .
} ORDER BY ?run""",
        "template": "CI/CD 파이프라인 실행 {count}건입니다.\n{items}"
    },
    # 6. E-Commerce
    {
        "keys": ["상품", "product", "추천", "recommend", "가격", "세션", "장바구니"],
        "domains": ["ecommerce"],
        "sparql": """SELECT ?session ?product WHERE {
  ?session a ecom:CustomerSession ;
           ecom:recommends ?product .
} ORDER BY ?session""",
        "template": "고객 세션별 추천 상품 내역 {count}건입니다.\n{items}"
    },
    # 7. Healthcare
    {
        "keys": ["환자", "patient", "진단", "diagnostic", "소견", "finding", "보고서"],
        "domains": ["healthcare"],
        "sparql": """SELECT ?task ?status ?agentName ?confidence ?finding WHERE {
  ?task a health:DiagnosticTask ;
        health:diagnosticStatus ?status ;
        health:analyzedBy [ rdfs:label ?agentName ] ;
        health:generatesReport [
            health:confidenceScore ?confidence ;
            health:findingText ?finding
        ] .
} ORDER BY ?task""",
        "template": "의료 진단 태스크 분석 및 소견 {count}건입니다.\n{items}"
    },
    # 8. Academic
    {
        "keys": ["학생", "교수", "student", "professor", "사람"],
        "domains": ["academic"],
        "sparql": """SELECT ?person ?label ?type WHERE {
  VALUES ?type { ex:Student ex:Professor }
  ?person a ?type .
  OPTIONAL { ?person rdfs:label ?label }
} ORDER BY ?person""",
        "template": "학사 인원 목록 {count}명입니다.\n{items}"
    },
    {
        "keys": ["과목", "수업", "강의", "course", "학점"],
        "domains": ["academic"],
        "sparql": """SELECT ?course ?label ?code ?credits WHERE {
  ?course a ex:Course .
  OPTIONAL { ?course rdfs:label ?label }
  OPTIONAL { ?course ex:courseCode ?code }
  OPTIONAL { ?course ex:credits ?credits }
} ORDER BY ?course""",
        "template": "개설 과목 목록 {count}개입니다.\n{items}"
    }
]


def resolve_sparql(question, domain_key):
    """
    Analyzes natural language question and domain_key to match the best SPARQL query.
    Returns (sparql_query, template_msg).
    """
    clean_q = question.strip().lower()
    best_pattern = None
    best_score = 0

    for item in INTENT_PATTERNS:
        if domain_key in item["domains"]:
            score = 0
            for k in item["keys"]:
                if k in clean_q:
                    score += 1
            if score > best_score:
                best_score = score
                best_pattern = item

    prefix = PREFIXES.get(domain_key, "")

    if best_pattern and best_score > 0:
        query = prefix + best_pattern["sparql"]
        return query, best_pattern["template"]

    # Fallback Generic Keyword Search Query
    # Extracts keywords from the question to search across literal and URI values
    words = [w for w in re.split(r'[\s,\.\?!]+', clean_q) if len(w) > 1 and w not in ["알려줘", "보여줘", "있는", "어떤", "어디", "무엇", "목록", "리스트", "조회"]]
    filter_expr = ""
    if words:
        clauses = []
        for word in words[:3]:
            escaped = word.replace('"', '\\"')
            clauses.append(f'CONTAINS(LCASE(STR(?s)), "{escaped}") || CONTAINS(LCASE(STR(?p)), "{escaped}") || CONTAINS(LCASE(STR(?o)), "{escaped}")')
        filter_expr = "FILTER(" + " || ".join(clauses) + ")\n"

    fallback_query = f"""{prefix}SELECT ?s ?p ?o WHERE {{
  ?s ?p ?o .
  {filter_expr}}} LIMIT 30"""

    return fallback_query, "질문과 관련된 온톨로지 개체 {count}건을 탐색했습니다.\n{items}"


def format_answer(rows, vars_, template):
    """Formats SPARQL query result rows into natural Korean conversational text."""
    count = len(rows)
    if count == 0:
        return "질문하신 조건에 일치하는 온톨로지 데이터를 찾지 못했습니다. 다른 질문을 입력해 보세요."

    items = []
    for idx, r in enumerate(rows[:10], 1):
        line_parts = []
        for v in vars_:
            val = r.get(v, "")
            if val:
                # simplify URI to short name if possible
                short_val = str(val).split("#")[-1].split("/")[-1]
                line_parts.append(f"{v}: {short_val}")
        items.append(f"{idx}. " + " | ".join(line_parts))

    if count > 10:
        items.append(f"... 외 {count - 10}건 추가 검색됨")

    return template.format(count=count, items="\n".join(items))


def answer_natural_query(graph, question, domain_key):
    """
    Executes an end-to-end natural query on an RDF Graph:
      1. Generates SPARQL query.
      2. Executes against graph.
      3. Builds structured and conversational answers.
    """
    sparql_query, template = resolve_sparql(question, domain_key)
    res = graph.query(sparql_query)
    vars_ = [str(v) for v in res.vars]
    rows = []
    for row in res:
        item = {}
        for v in vars_:
            val = getattr(row, v, None)
            item[v] = str(val) if val is not None else ""
        rows.append(item)

    summary_text = format_answer(rows, vars_, template)

    return {
        "question": question,
        "domain": domain_key,
        "sparql": sparql_query,
        "count": len(rows),
        "vars": vars_,
        "rows": rows,
        "answer": summary_text
    }
