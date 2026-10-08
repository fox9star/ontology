"""
Multi-format Batch Ontology Exporter
Exports all domain ontologies and instance graphs into multiple Semantic Web formats:
  - Turtle (.ttl)
  - JSON-LD (.jsonld)
  - RDF/XML (.rdf)
  - N-Triples (.nt)
"""

import os
import sys
import argparse
import time
from pathlib import Path
from app import ONTOLOGIES, load_graph, BASE_DIR

FORMAT_SPECS = {
    "ttl": ("turtle", "ttl", "Turtle"),
    "turtle": ("turtle", "ttl", "Turtle"),
    "jsonld": ("json-ld", "jsonld", "JSON-LD"),
    "json-ld": ("json-ld", "jsonld", "JSON-LD"),
    "rdf": ("pretty-xml", "rdf", "RDF/XML"),
    "xml": ("pretty-xml", "rdf", "RDF/XML"),
    "pretty-xml": ("pretty-xml", "rdf", "RDF/XML"),
    "nt": ("nt", "nt", "N-Triples"),
    "ntriples": ("nt", "nt", "N-Triples")
}

DEFAULT_FORMATS = ["ttl", "jsonld", "rdf", "nt"]


def export_domain(domain_key, output_dir, formats=None, project_id=None):
    """
    Exports a single domain to the specified formats.
    Returns a dict with export details.
    """
    if formats is None:
        formats = DEFAULT_FORMATS

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    g = load_graph(domain_key, project_id=project_id)
    triple_count = len(g)
    results = {
        "domain": domain_key,
        "triples": triple_count,
        "files": []
    }

    seen_exts = set()
    for fmt_alias in formats:
        key_norm = fmt_alias.strip().lower()
        if key_norm not in FORMAT_SPECS:
            continue
        rdflib_fmt, ext, label = FORMAT_SPECS[key_norm]
        if ext in seen_exts:
            continue
        seen_exts.add(ext)

        filename = f"{domain_key}.{ext}" if not project_id else f"{domain_key}_{project_id}.{ext}"
        target_file = out_path / filename

        serialized = g.serialize(format=rdflib_fmt)
        if isinstance(serialized, str):
            target_file.write_text(serialized, encoding="utf-8")
        else:
            target_file.write_bytes(serialized)

        size = target_file.stat().st_size
        results["files"].append({
            "format": label,
            "filename": filename,
            "path": str(target_file),
            "size": size
        })

    return results


def export_all(output_dir="exports", formats=None, domains=None, project_id=None):
    """
    Exports all or specified domains into the target output directory.
    Returns list of result dictionaries per domain.
    """
    if formats is None:
        formats = DEFAULT_FORMATS
    if domains is None:
        domains = list(ONTOLOGIES.keys())

    all_results = []
    start_time = time.perf_counter()

    for dom in domains:
        if dom not in ONTOLOGIES:
            print(f"[경고] 알 수 없는 도메인: {dom}", file=sys.stderr)
            continue
        res = export_domain(dom, output_dir, formats=formats, project_id=project_id if dom == 'mv' else None)
        all_results.append(res)

    elapsed = time.perf_counter() - start_time
    return all_results, elapsed


def print_summary(all_results, elapsed):
    print("=" * 70)
    print("         AI 에이전트 온톨로지 에코시스템 일괄 내보내기 (Export) 결과         ")
    print("=" * 70)
    total_files = 0
    total_bytes = 0
    total_triples = 0

    for res in all_results:
        dom = res["domain"]
        triples = res["triples"]
        total_triples += triples
        print(f"\n[도메인] {dom.upper():<12} (트리플: {triples}개)")
        for f in res["files"]:
            total_files += 1
            total_bytes += f["size"]
            size_kb = f["size"] / 1024.0
            print(f"  - {f['format']:<10} -> {f['filename']:<25} ({size_kb:6.2f} KB)")

    print("-" * 70)
    print(f"총계: 도메인 {len(all_results)}개, 파일 {total_files}개 생성, 전체 용량: {total_bytes/1024:.2f} KB")
    print(f"소요 시간: {elapsed:.2f}초")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Multi-format Batch Ontology Exporter")
    parser.add_argument("--output-dir", "-o", default="exports", help="내보낼 대상 디렉토리 (기본값: exports)")
    parser.add_argument("--formats", "-f", default="ttl,jsonld,rdf,nt", help="내보낼 포맷 목록 (기본값: ttl,jsonld,rdf,nt)")
    parser.add_argument("--domains", "-d", default=None, help="내보낼 도메인 (쉼표 구분, 기본값: 전체)")
    parser.add_argument("--project", "-p", default=None, help="MV 도메인 대상 프로젝트 ID (선택)")

    args = parser.parse_args()
    formats = [f.strip() for f in args.formats.split(",") if f.strip()]
    domains = [d.strip() for d in args.domains.split(",") if d.strip()] if args.domains else None

    results, elapsed = export_all(
        output_dir=args.output_dir,
        formats=formats,
        domains=domains,
        project_id=args.project
    )
    print_summary(results, elapsed)


if __name__ == "__main__":
    main()
