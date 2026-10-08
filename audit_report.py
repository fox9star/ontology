"""Report provenance recorded in a graph without certifying unverified history."""

from datetime import datetime, timezone
from html import escape

from rdflib import Namespace, RDF, RDFS

PROV_NS = Namespace("http://www.w3.org/ns/prov#")
MV_NS = Namespace("https://example.org/mv#")
CODEX_NS = Namespace("https://example.org/codex#")
UNKNOWN = "미확인"


def _local_name(value):
    return str(value).rsplit("#", 1)[-1].rsplit("/", 1)[-1]


def _named_values(graph, subject, names):
    """Read existing domain properties without assuming one domain namespace."""
    return sorted({str(value) for predicate, value in graph.predicate_objects(subject)
                   if _local_name(predicate) in names})


def _labels(graph, subjects):
    labels = []
    for subject in subjects:
        recorded = sorted(str(value) for value in graph.objects(subject, RDFS.label))
        labels.append(recorded[0] if recorded else _local_name(subject))
    return "; ".join(labels) if labels else UNKNOWN


def extract_audit_trail(graph, domain_key="mv", project_id=None):
    """Return recorded entities and activities, keeping absent facts unknown.

    An import activity describes file copying/registration. Its recorded tool
    version is not evidence of the original media's generation model.
    """
    assets = set(graph.subjects(PROV_NS.wasGeneratedBy, None))
    assets.update(graph.subjects(PROV_NS.atLocation, None))
    for subject, predicate, _ in graph:
        if _local_name(predicate) == "fileUri":
            assets.add(subject)
    for subject, kind in graph.subject_objects(RDF.type):
        if kind == PROV_NS.Entity or _local_name(kind).endswith(("Asset", "Artifact")):
            assets.add(subject)

    records = []
    for asset in sorted(assets, key=str):
        sources = sorted({str(value) for value in graph.objects(asset, PROV_NS.wasDerivedFrom)})
        locations = _named_values(graph, asset, {"fileUri"})
        locations += sorted({str(value) for value in graph.objects(asset, PROV_NS.atLocation)})
        checksums = _named_values(graph, asset, {"sha256", "checksum"})
        activities = sorted(set(graph.objects(asset, PROV_NS.wasGeneratedBy)), key=str)
        for activity in activities or [None]:
            agents = sorted(set(graph.objects(activity, PROV_NS.wasAssociatedWith)), key=str) if activity is not None else []
            versions = _named_values(graph, activity, {"modelVersion"}) if activity is not None else []
            importing = MV_NS.localImportAgent in agents or any(version.startswith("local-media-importer-") for version in versions)
            model_provenance = _named_values(graph, activity, {"modelProvenance"}) if activity is not None else []
            notes = sorted(str(value) for value in graph.objects(activity, RDFS.comment)) if activity is not None else []
            recorded_status = _named_values(graph, activity, {"status"}) if activity is not None else []
            records.append({
                "asset_uri": str(asset), "asset_name": _labels(graph, [asset]),
                "file_uri": "; ".join(sorted(set(locations))) if locations else UNKNOWN,
                "task_uri": str(activity) if activity is not None else None,
                "task_name": _labels(graph, [activity]) if activity is not None else UNKNOWN,
                "agent_uris": [str(agent) for agent in agents], "agent_name": _labels(graph, agents),
                "source": "; ".join(sources) if sources else UNKNOWN, "source_uris": sources,
                "model_version": "; ".join(versions) if versions and not importing else UNKNOWN,
                "model_provenance": "; ".join(model_provenance) if model_provenance else UNKNOWN,
                "tool_version": "; ".join(versions) if importing and versions else UNKNOWN,
                "activity_kind": "import_registration" if importing else "recorded_activity" if activity is not None else "unknown",
                "recorded_status": "; ".join(recorded_status) if recorded_status else UNKNOWN,
                "checksum": "; ".join(checksums) if checksums else UNKNOWN,
                "started_at": "; ".join(sorted(str(value) for value in graph.objects(activity, PROV_NS.startedAtTime))) if activity is not None else "",
                "ended_at": "; ".join(sorted(str(value) for value in graph.objects(activity, PROV_NS.endedAtTime))) if activity is not None else "",
                "notes": "; ".join(notes) if notes else "",
                "verification": "graph_record_only",
            })

    records.sort(key=lambda record: (record["asset_name"], record["asset_uri"], record["task_uri"] or ""))
    return {
        "domain": domain_key, "project_id": project_id or "default",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_artifacts": len(assets), "total_records": len(records),
        "verification": "graph_record_only", "records": records,
    }


def render_html_certificate(audit_data):
    """Render the historical API's HTML report; it makes no certification claim."""
    def e(value):
        return escape(str(value if value is not None else UNKNOWN), quote=True)

    rows = []
    for index, record in enumerate(audit_data.get("records", []), 1):
        details = [
            f"<div>모델 확인 정보: {e(record.get('model_provenance', UNKNOWN))}</div>",
            f"<div>작업 도구 버전: {e(record.get('tool_version', UNKNOWN))}</div>",
            f"<div>체크섬(그래프 기록): {e(record.get('checksum', UNKNOWN))}</div>",
        ]
        if record.get("activity_kind") == "import_registration":
            details.insert(0, "<div><strong>기존 파일 복사·등록 이력. 원본 생성 모델과 프롬프트는 미확인입니다.</strong></div>")
        for key, label in (("recorded_status", "기록된 작업 상태"), ("started_at", "시작"), ("ended_at", "종료"), ("notes", "기록 메모")):
            if record.get(key):
                details.append(f"<div>{label}: {e(record[key])}</div>")
        rows.append(f"""<tr>
<td>{index}</td>
<td><strong>{e(record.get('asset_name', UNKNOWN))}</strong><br><small>{e(record.get('file_uri', UNKNOWN))}</small></td>
<td>{e(record.get('task_name', UNKNOWN))}<br><small>{e(record.get('agent_name', UNKNOWN))}</small></td>
<td>{e(record.get('model_version', UNKNOWN))}</td>
<td>{e(record.get('source', UNKNOWN))}<div class="details">{''.join(details)}</div></td>
</tr>""")

    empty = '<tr><td colspan="5">기록된 객체가 없습니다.</td></tr>'
    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<title>등록된 출처 및 작업 이력 보고서</title>
<style>
body {{ font-family: 'Segoe UI', sans-serif; margin: 32px; color: #14213d; }}
main {{ max-width: 1200px; margin: auto; }}
h1 {{ font-size: 24px; }}
.meta, .notice {{ background: #f1f5f9; padding: 16px; margin-bottom: 20px; line-height: 1.6; }}
table {{ width: 100%; border-collapse: collapse; table-layout: fixed; }}
td, th {{ text-align: left; padding: 12px; border-bottom: 1px solid #cbd5e1; vertical-align: top; overflow-wrap: anywhere; }}
th {{ background: #eff6ff; }}
th:first-child {{ width: 35px; }}
small, .details {{ font-size: 12px; color: #475569; }}
.details {{ margin-top: 12px; line-height: 1.6; }}
@media print {{ body {{ margin: 12px; }} tr {{ break-inside: avoid; }} }}
</style></head><body><main>
<h1>등록된 출처 및 작업 이력 보고서</h1>
<div class="meta">도메인: {e(audit_data.get('domain', UNKNOWN))}<br>
프로젝트: {e(audit_data.get('project_id', UNKNOWN))}<br>
보고서 작성(UTC): {e(audit_data.get('generated_at', UNKNOWN))}</div>
<p class="notice">이 보고서는 RDF 그래프에 등록된 출처와 작업 이력을 보여줍니다.
원본 생성 모델, 저작권, 실제 파일 무결성 또는 SHACL 검증 통과를 인증하지 않습니다.
기록되지 않은 정보는 미확인으로 표시하며, 파일 무결성과 SHACL 검증 결과는 별도로 확인해야 합니다.</p>
<table><thead><tr><th>No</th><th>기록된 객체 / 파일</th><th>작업 / 담당 도구</th><th>기록된 모델 버전</th><th>출처 / 확인 정보</th></tr></thead>
<tbody>{''.join(rows) if rows else empty}</tbody></table>
</main></body></html>"""
