"""Create and validate a local demonstration graph without generating media.

Remote graph updates and webhook delivery require explicit command-line options.
Each invocation writes a new run directory so source fixtures are never replaced.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from urllib.parse import urlparse
from uuid import uuid4

from rdflib import Literal, Namespace, RDF

from ontology_pipeline import MusicVideoOntologyBuilder, MV, PROV


BASE_DIR = Path(__file__).resolve().parent
DEMO = Namespace("https://example.org/demo#")


def _endpoint(value):
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise argparse.ArgumentTypeError("Expected an http(s) endpoint URL")
    return value


def _build_demo(project_id):
    builder = MusicVideoOntologyBuilder(project_id=project_id, title="Local demonstration music video")
    builder.add_audio("https://example.invalid/demo/audio.wav", duration_sec=60, bpm=128)
    builder.add_timeline_with_shots([
        {"order": 1, "start": 0, "end": 30,
         "image_uri": "https://example.invalid/demo/image01.png", "label": "Demo city"},
        {"order": 2, "start": 30, "end": 60,
         "image_uri": "https://example.invalid/demo/image02.png", "label": "Demo studio"},
    ])
    builder.finalize_video("https://example.invalid/demo/video.mp4", duration_sec=60)
    builder.g.bind("demo", DEMO)
    builder.g.add((builder.project_uri, DEMO.simulated, Literal(True)))
    builder.g.add((builder.project_uri, DEMO.note,
                   Literal("Metadata demonstration only; no media has been generated or verified.")))
    for asset_class in (MV.AudioAsset, MV.ImageAsset, MV.MusicVideo):
        for asset in builder.g.subjects(RDF.type, asset_class):
            builder.g.add((asset, DEMO.simulated, Literal(True)))
    for asset, task in list(builder.g.subject_objects(PROV.wasGeneratedBy)):
        builder.g.remove((asset, PROV.wasGeneratedBy, task))
        builder.g.add((asset, DEMO.plannedGenerationTask, task))
    # The builder models finished assets. In this demo they remain planned placeholders.
    for task in list(builder.g.subjects(MV.status, None)):
        builder.g.set((task, MV.status, Literal("planned")))
        builder.g.add((task, DEMO.simulated, Literal(True)))
    return builder


def execute_end_to_end_pipeline(output_dir=None, project_id="demo_project",
                                update_endpoint=None, webhook_url=None):
    """Return success after validation and any explicitly requested delivery.

    Endpoint arguments opt in to network writes. Environment credentials and
    endpoint variables are deliberately not read.
    """
    if update_endpoint:
        _endpoint(update_endpoint)
    if webhook_url:
        _endpoint(webhook_url)
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "_" + uuid4().hex[:12]
    run_dir = Path(output_dir or BASE_DIR / "exports" / "demo-pipeline").resolve() / run_id
    run_dir.mkdir(parents=True, exist_ok=False)
    builder = _build_demo(project_id)
    conforms, report_text = builder.validate()
    ttl_path, jsonld_path = builder.export(str(run_dir / "demo_project"))
    report_path = run_dir / "validation.txt"
    report_path.write_text(report_text, encoding="utf-8")
    summary = {
        "project_id": project_id,
        "simulated": True,
        "media_generated": False,
        "conforms": bool(conforms),
        "triples": len(builder.g),
        "outputs": {"turtle": str(ttl_path), "jsonld": str(jsonld_path),
                    "validation": str(report_path)},
        "remote_update": "not_requested",
        "webhook": "not_requested",
    }
    success = bool(conforms)
    # A failed graph is available for diagnosis but is never sent to a remote store.
    if update_endpoint and conforms:
        import requests
        try:
            response = requests.post(
                update_endpoint,
                data="INSERT DATA {\n" + builder.g.serialize(format="nt") + "\n}",
                headers={"Content-Type": "application/sparql-update"}, timeout=10)
            delivered = response.status_code in (200, 201, 202, 204)
        except requests.RequestException:
            delivered = False
        summary["remote_update"] = "delivered" if delivered else "failed"
        success = success and delivered
    elif update_endpoint:
        summary["remote_update"] = "skipped_invalid_graph"
    if webhook_url:
        import requests
        try:
            response = requests.post(webhook_url,
                                     json={"event": "demo_pipeline", "data": summary}, timeout=10)
            delivered = response.status_code in (200, 201, 202, 204)
        except requests.RequestException:
            delivered = False
        summary["webhook"] = "delivered" if delivered else "failed"
        success = success and delivered
    summary["success"] = success
    summary_path = run_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"success": success, "simulated": True, "conforms": bool(conforms),
                      "summary": str(summary_path)}, ensure_ascii=False))
    return success


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Parent directory for new local run folders")
    parser.add_argument("--project-id", default="demo_project")
    parser.add_argument("--update-endpoint", type=_endpoint,
                        help="Opt in to inserting the validated DEMO graph at this SPARQL endpoint")
    parser.add_argument("--notify-webhook", type=_endpoint,
                        help="Opt in to delivering a DEMO status event to this webhook")
    args = parser.parse_args(argv)
    return 0 if execute_end_to_end_pipeline(args.output_dir, args.project_id,
                                           args.update_endpoint, args.notify_webhook) else 1


if __name__ == "__main__":
    sys.exit(main())
