"""Copy actual local media into an independently validated ontology project."""

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import json
import mimetypes
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import pyshacl
from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef, XSD
from ontology_loader import load_schema_graph, load_shape_graph
from validation_pipeline import validate_phases


ROOT = Path(__file__).resolve().parent
MV = Namespace('https://example.org/mv#')
PROV = Namespace('http://www.w3.org/ns/prov#')
VERSION = 'local-media-importer-1.0'
KST = timezone(timedelta(hours=9))


def positive_decimal(value, name):
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f'{name} must be a positive number') from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f'{name} must be a positive number')
    return result


def file_sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def probe_media(path, kind, executable='ffprobe'):
    result = subprocess.run(
        [str(executable), '-v', 'error', '-show_streams', '-show_format', '-of', 'json', str(path)],
        capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=60,
    )
    if result.returncode:
        raise ValueError(f'Cannot inspect {Path(path).name}: {result.stderr.strip()}')
    try:
        data = json.loads(result.stdout)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'ffprobe returned invalid metadata for {Path(path).name}') from exc
    if not isinstance(data, dict):
        raise ValueError(f'ffprobe returned invalid metadata for {Path(path).name}')
    streams = data.get('streams') or []
    stream_kind = 'audio' if kind == 'audio' else 'video'
    stream = next((s for s in streams if isinstance(s, dict) and s.get('codec_type') == stream_kind), None)
    if stream is None:
        raise ValueError(f'{Path(path).name} has no {stream_kind} stream')
    metadata = {'codec': stream.get('codec_name', 'unknown')}
    if kind in ('audio', 'video'):
        duration = (data.get('format') or {}).get('duration') or stream.get('duration')
        metadata['duration_seconds'] = str(positive_decimal(duration, 'duration'))
    if kind in ('image', 'video'):
        width, height = int(stream.get('width', 0)), int(stream.get('height', 0))
        if width <= 0 or height <= 0:
            raise ValueError(f'{Path(path).name} has invalid dimensions')
        metadata.update(width=width, height=height)
    if kind == 'audio':
        metadata.update(sample_rate=int(stream.get('sample_rate', 0)), channels=int(stream.get('channels', 0)))
    return metadata


def make_graph(project, manifest, finished_at):
    graph = Graph()
    for prefix, namespace in [('mv', MV), ('prov', PROV), ('rdfs', RDFS), ('xsd', XSD)]:
        graph.bind(prefix, namespace)
    graph.add((MV.project01, RDF.type, MV.MusicVideoProject))
    graph.add((MV.project01, RDFS.label, Literal(project['name'], lang='ko')))
    graph.add((MV.project01, MV.hasBrief, MV.brief01))
    graph.add((MV.project01, MV.hasTimeline, MV.timeline01))
    graph.add((MV.brief01, RDF.type, MV.CreativeBrief))
    graph.add((MV.brief01, RDFS.label, Literal('등록한 음원과 이미지의 장면 배치 계획', lang='ko')))
    graph.add((MV.brief01, MV.targetDurationSeconds, Literal(manifest['duration_seconds'], datatype=XSD.decimal)))
    graph.add((MV.timeline01, RDF.type, MV.Timeline))
    graph.add((MV.timeline01, RDFS.label, Literal('음원 전체 길이를 나눈 장면 배치 계획', lang='ko')))
    graph.add((MV.localImportAgent, RDF.type, MV.AIAgent))
    graph.add((MV.localImportAgent, RDFS.label, Literal('로컬 파일 등록 에이전트', lang='ko')))
    graph.add((MV.importRun01, RDF.type, MV.GenerationTask))
    graph.add((MV.importRun01, RDFS.label, Literal('기존 음원·이미지 복사 및 메타데이터 등록', lang='ko')))
    graph.add((MV.importRun01, RDFS.comment, Literal(manifest['import_info']['provenance_note'], lang='ko')))
    graph.add((MV.importRun01, MV.status, Literal('completed')))
    graph.add((MV.importRun01, MV.modelVersion, Literal(manifest['import_info']['tool_version'])))
    graph.add((MV.importRun01, PROV.wasAssociatedWith, MV.localImportAgent))
    graph.add((MV.importRun01, PROV.startedAtTime, Literal(project['created_at'], datatype=XSD.dateTime)))
    graph.add((MV.importRun01, PROV.endedAtTime, Literal(finished_at, datatype=XSD.dateTime)))
    for reference in manifest['import_info'].get('source_references', []):
        graph.add((MV.importRun01, RDFS.seeAlso, URIRef(reference)))
    asset_classes = {'audio': MV.AudioAsset, 'image': MV.ImageAsset, 'video': MV.MusicVideo}
    project_links = {'audio': MV.hasAudio, 'image': MV.hasImage, 'video': MV.hasFinalVideo}
    for asset in manifest['assets']:
        node = MV[asset['id']]
        source_uri = URIRef(Path(asset['source_file']).as_uri())
        graph.add((node, RDF.type, asset_classes[asset['kind']]))
        graph.add((node, RDFS.label, Literal(asset['label'], lang='ko')))
        graph.add((node, MV.fileUri, URIRef(asset['file_uri'])))
        graph.add((node, MV.checksum, Literal(asset['sha256'])))
        graph.add((node, MV.mimeType, Literal(asset['mime_type'])))
        graph.add((node, PROV.wasGeneratedBy, MV.importRun01))
        graph.add((node, PROV.wasDerivedFrom, source_uri))
        graph.add((MV.importRun01, PROV.used, source_uri))
        graph.add((MV.project01, project_links[asset['kind']], node))
        if 'duration_seconds' in asset:
            graph.add((node, MV.durationSeconds, Literal(asset['duration_seconds'], datatype=XSD.decimal)))
        for dimension in ('width', 'height'):
            if dimension in asset:
                graph.add((node, MV[dimension], Literal(asset[dimension], datatype=XSD.integer)))
        if asset['kind'] == 'video':
            graph.add((node, MV.usesAudio, MV.audio01))
            graph.add((node, MV.hasTimeline, MV.timeline01))
    for shot in manifest['timeline']:
        node = MV[shot['id']]
        graph.add((node, RDF.type, MV.Shot))
        graph.add((node, RDFS.label, Literal(f"장면 {shot['order_index']} 배치 계획", lang='ko')))
        graph.add((node, MV.orderIndex, Literal(shot['order_index'], datatype=XSD.integer)))
        graph.add((node, MV.startSecond, Literal(shot['start_second'], datatype=XSD.decimal)))
        graph.add((node, MV.endSecond, Literal(shot['end_second'], datatype=XSD.decimal)))
        graph.add((node, MV.usesImage, MV[shot['image_id']]))
        graph.add((MV.timeline01, MV.hasShot, node))
    return graph


def import_project(plan, projects_root=None, ffprobe_path='ffprobe'):
    project_id = plan.get('id', '')
    if not isinstance(project_id, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}', project_id):
        raise ValueError('Project id must contain only letters, digits, underscores and hyphens')
    project_name = str(plan.get('name') or project_id).strip()
    source_dir = Path(plan['source_directory']).resolve(strict=True)
    if not source_dir.is_dir():
        raise ValueError('source_directory must be a directory')
    image_names = plan.get('images')
    if not isinstance(image_names, list) or not image_names or not plan.get('audio'):
        raise ValueError('A project requires one audio file and at least one image')
    projects_root = Path(projects_root or ROOT / 'projects').resolve()
    projects_root.mkdir(parents=True, exist_ok=True)
    target = projects_root / project_id
    if target.exists():
        raise FileExistsError(f'Project {project_id} already exists; use another id')
    probe_version = subprocess.run(
        [str(ffprobe_path), '-version'], capture_output=True, text=True,
        encoding='utf-8', errors='replace', check=True, timeout=15,
    ).stdout.splitlines()[0]
    started_at = datetime.now(KST).isoformat()
    project = {'id': project_id, 'name': project_name, 'ontology': 'mv',
               'created_at': started_at, 'data': 'data.ttl', 'manifest': 'manifest.json'}
    notes = plan.get('provenance_note') or 'Imported local files. Original generation model and prompt are unknown.'
    references = [Path(value).resolve().as_uri() for value in plan.get('source_references', [])]
    manifest = {'project_id': project_id, 'assets': [], 'timeline': [], 'import_info': {
        'source_directory': str(source_dir), 'imported_at': started_at,
        'tool': 'import_media.py', 'tool_version': f'{VERSION}; {probe_version}',
        'provenance_note': notes, 'source_references': references,
        'timeline_note': 'Image placement plan; no new video was rendered.'}}
    entries = [('audio01', 'audio', plan['audio'], project_name)]
    labels = plan.get('image_labels') or []
    entries.extend((f'image{i:02d}', 'image', value, str(labels[i - 1]) if i <= len(labels) else Path(value).stem)
                   for i, value in enumerate(image_names, 1))
    if plan.get('video'):
        entries.append(('video01', 'video', plan['video'], project_name + ' video'))

    with tempfile.TemporaryDirectory(prefix='import-', dir=projects_root) as scratch:
        staging = Path(scratch) / project_id
        assets_dir = staging / 'assets'
        assets_dir.mkdir(parents=True)
        for asset_id, kind, source_name, label in entries:
            source = (source_dir / source_name).resolve(strict=True)
            if not source.is_relative_to(source_dir) or not source.is_file():
                raise ValueError(f'Media file must stay within source_directory: {source_name}')
            metadata = probe_media(source, kind, ffprobe_path)
            filename = asset_id + source.suffix.lower()
            destination = assets_dir / filename
            shutil.copy2(source, destination)
            source_hash = file_sha256(source)
            if file_sha256(destination) != source_hash:
                raise ValueError(f'Copy checksum mismatch: {source.name}')
            manifest['assets'].append({
                'id': asset_id, 'kind': kind, 'label': label,
                'file_name': filename, 'file_uri': (target / 'assets' / filename).as_uri(),
                'source_file': str(source), 'sha256': source_hash,
                'size_bytes': destination.stat().st_size,
                'mime_type': mimetypes.guess_type(filename)[0] or 'application/octet-stream',
                **metadata,
            })
        audio = manifest['assets'][0]
        duration = positive_decimal(plan.get('target_duration_seconds') or audio['duration_seconds'], 'target duration')
        if duration > Decimal(audio['duration_seconds']):
            raise ValueError('Target duration cannot exceed the audio duration')
        video = next((a for a in manifest['assets'] if a['kind'] == 'video'), None)
        if video and Decimal(video['duration_seconds']) != duration:
            raise ValueError('Existing video duration must equal the planned timeline duration')
        manifest['duration_seconds'] = str(duration)
        images = [a for a in manifest['assets'] if a['kind'] == 'image']
        for i, image in enumerate(images, 1):
            start = (duration * Decimal(i - 1) / Decimal(len(images))).quantize(Decimal('0.000001'))
            end = duration if i == len(images) else (duration * Decimal(i) / Decimal(len(images))).quantize(Decimal('0.000001'))
            if start >= end:
                raise ValueError('The duration is too short to give every image a positive interval')
            manifest['timeline'].append({'id': f'shot{i:02d}', 'order_index': i,
                'start_second': str(start), 'end_second': str(end), 'image_id': image['id']})
        finished_at = datetime.now(KST).isoformat()
        graph = make_graph(project, manifest, finished_at)
        phases = validate_phases(graph, load_schema_graph(ROOT, 'mv-schema.ttl'), load_shape_graph(ROOT, 'mv-shapes.ttl'))
        conforms, report = phases['conforms'], phases['report_text']
        if not conforms:
            raise ValueError('Project failed SHACL validation:\n' + report)
        graph.serialize(destination=str(staging / 'data.ttl'), format='turtle', encoding='utf-8')
        for filename, content in [('project.json', project), ('manifest.json', manifest), ('import-plan.json', plan)]:
            (staging / filename).write_text(json.dumps(content, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        (staging / 'validation.txt').write_text(report, encoding='utf-8')
        staging.rename(target)
    return {'id': project_id, 'name': project_name, 'path': str(target),
            'assets': len(manifest['assets']), 'duration_seconds': manifest['duration_seconds'], 'conforms': True}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan', required=True, type=Path, help='UTF-8 JSON import plan')
    parser.add_argument('--projects-root', type=Path, default=ROOT / 'projects')
    parser.add_argument('--ffprobe', default='ffprobe', help='ffprobe executable name or path')
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan.read_text(encoding='utf-8-sig'))
        if not isinstance(plan, dict):
            raise ValueError('The import plan must be a JSON object')
        result = import_project(plan, args.projects_root, args.ffprobe)
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as exc:
        parser.exit(1, f'Import failed: {exc}\n')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
