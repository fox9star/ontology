"""
PySHACL verification for every configured domain profile.
"""

import os
import sys
import pyshacl
import rdflib
from rdflib import Graph
from ontology_loader import load_schema_graph, load_shape_graph
from validation_pipeline import validate_phases

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DOMAINS = [
    {
        "name": "1. 뮤직비디오 생성 AI 에이전트 온톨로지 (mv)",
        "schema": "mv-schema.ttl",
        "shapes": "mv-shapes.ttl",
        "data": "mv-example.ttl"
    },
    {
        "name": "2. 엔드투엔드 파이프라인 가사/자막/번역 확장 (e2e)",
        "schema": "mv-schema.ttl",
        "shapes": "mv-shapes.ttl",
        "data": "e2e_pipeline_output.ttl"
    },
    {
        "name": "3. 소프트웨어 빌드·배포 CI/CD AI 에이전트 온톨로지 (devops)",
        "schema": "devops-schema.ttl",
        "shapes": "devops-shapes.ttl",
        "data": "devops-example.ttl"
    },
    {
        "name": "4. 일반 AI 에이전트 협업 온톨로지 (agent)",
        "schema": "agent-schema.ttl",
        "shapes": "agent-shapes.ttl",
        "data": "agent-example.ttl"
    },
    {
        "name": "5. 전자상거래 AI 에이전트 온톨로지 (ecommerce)",
        "schema": "ecommerce-schema.ttl",
        "shapes": "ecommerce-shapes.ttl",
        "data": "ecommerce-example.ttl"
    },
    {
        "name": "6. 헬스케어 AI 에이전트 온톨로지 (healthcare)",
        "schema": "healthcare-schema.ttl",
        "shapes": "healthcare-shapes.ttl",
        "data": "healthcare-example.ttl"
    },
    {
        "name": "7. 대학 수강 온톨로지 (academic)",
        "schema": "academic-schema.ttl",
        "shapes": "academic-shapes.ttl",
        "data": "academic-example.ttl"
    },
    {
        "name": "8. 주식투자 AI 에이전트 온톨로지 (stock)",
        "schema": "stock-schema.ttl",
        "shapes": "stock-shapes.ttl",
        "data": "stock-example.ttl"
    },
    {
        "name": "9. 체중감량 및 식이·운동 AI 에이전트 온톨로지 (diet)",
        "schema": "diet-schema.ttl",
        "shapes": "diet-shapes.ttl",
        "data": "diet-example.ttl"
    },
    {
        "name": "10. 캠핑 계획 및 야영장 관리 온톨로지 (camping)",
        "schema": "camping-schema.ttl",
        "shapes": "camping-shapes.ttl",
        "data": "camping-example.ttl"
    },
    {
        "name": "11. 한국전쟁 역사 및 군사작전 온톨로지 (korean-war)",
        "schema": "korean-war-schema.ttl",
        "shapes": "korean-war-shapes.ttl",
        "data": "korean-war-example.ttl"
    },
    {
        "name": "12. 정치·선거 정보 온톨로지 (politics)",
        "schema": "politics-schema.ttl",
        "shapes": "politics-shapes.ttl",
        "data": "politics-example.ttl"
    },
    {
        "name": "13. 놀이공원 운영 및 스마트 대기 온톨로지 (theme-park)",
        "schema": "theme-park-schema.ttl",
        "shapes": "theme-park-shapes.ttl",
        "data": "theme-park-example.ttl"
    },
]

from ontology_catalog import load_custom_profiles
for key, config in load_custom_profiles(BASE_DIR).items():
    DOMAINS.append({'name': config['name'], 'schema': config['schema'], 'shapes': config['shapes'], 'data': config['example']})

def run_suite():
    print("=" * 65)
    print(f"  전체 {len(DOMAINS)}개 온톨로지 프로파일 PySHACL 검증")
    print("=" * 65)
    
    all_passed = True
    for item in DOMAINS:
        data_path = os.path.join(BASE_DIR, item["data"])
        shapes_path = os.path.join(BASE_DIR, item["shapes"])
        
        data_g = Graph().parse(data_path, format="turtle" if data_path.endswith(".ttl") else "xml")
        shapes_g = load_shape_graph(BASE_DIR, item["shapes"])
        ont_g = load_schema_graph(BASE_DIR, item["schema"])
        
        phases = validate_phases(data_g, ont_g, shapes_g)
        conforms, report_text = phases["conforms"], phases["report_text"]
        
        status_str = "[PASS] Conforms: True" if conforms else "[FAIL] Conforms: False"
        print(f"\n{item['name']}: {status_str}")
        print(f"  explicit={phases['raw_conforms']}; rdfs={phases['inferred_conforms']}; inferred_types={phases['inferred_type_count']}")
        if not conforms:
            all_passed = False
            print(report_text)
            
    print("\n" + "=" * 65)
    if all_passed:
        print("[SUMMARY] 모든 온톨로지 프로파일의 PySHACL 검증이 통과하였습니다.")
    else:
        print("[SUMMARY] 검증 실패 항목이 존재합니다.")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
