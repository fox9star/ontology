"""
Automated Ontology Integration Pipeline Module.
Provides programmatic graph construction, asset lineage tracking, and SHACL validation for AI Agents.
"""

import os
import hashlib
from decimal import Decimal
from pathlib import Path
import rdflib
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD
import pyshacl
from ontology_loader import load_schema_graph, load_shape_graph
from validation_pipeline import validate_phases

MV = Namespace("https://example.org/mv#")
PROV = Namespace("http://www.w3.org/ns/prov#")
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class MusicVideoOntologyBuilder:
    def __init__(self, project_id="project_auto_01", title="AI 뮤직비디오 자동 생성 프로젝트"):
        self.g = Graph()
        self.g.bind("mv", MV)
        self.g.bind("prov", PROV)
        self.project_uri = MV[project_id]
        
        # Add Project & Brief
        self.g.add((self.project_uri, RDF.type, MV.MusicVideoProject))
        self.g.add((self.project_uri, rdflib.RDFS.label, Literal(title, lang="ko")))
        
        self.brief_uri = MV[f"{project_id}_brief"]
        self.g.add((self.brief_uri, RDF.type, MV.CreativeBrief))
        self.g.add((self.brief_uri, MV.targetDurationSeconds, Literal(Decimal("60"), datatype=XSD.decimal)))
        self.g.add((self.project_uri, MV.hasBrief, self.brief_uri))
        
    def add_audio(self, audio_uri, duration_sec, bpm=120, genre="Pop", agent_name="작곡 에이전트"):
        audio_asset = MV.audio_main
        task_uri = MV.task_audio_gen
        agent_uri = MV.agent_music
        
        self.g.add((agent_uri, RDF.type, MV.AIAgent))
        self.g.add((agent_uri, rdflib.RDFS.label, Literal(agent_name, lang="ko")))
        
        self.g.add((task_uri, RDF.type, MV.AudioGenerationTask))
        self.g.add((task_uri, rdflib.RDFS.label, Literal("음원 트랙 자동 생성", lang="ko")))
        self.g.add((task_uri, MV.status, Literal("completed")))
        self.g.add((task_uri, PROV.wasAssociatedWith, agent_uri))
        
        self.g.add((audio_asset, RDF.type, MV.AudioAsset))
        self.g.add((audio_asset, rdflib.RDFS.label, Literal("메인 음원", lang="ko")))
        self.g.add((audio_asset, MV.fileUri, URIRef(audio_uri)))
        self.g.add((audio_asset, MV.durationSeconds, Literal(Decimal(str(duration_sec)), datatype=XSD.decimal)))
        self.g.add((audio_asset, MV.bpm, Literal(int(bpm), datatype=XSD.integer)))
        self.g.add((audio_asset, MV.genre, Literal(genre)))
        self.g.add((audio_asset, PROV.wasGeneratedBy, task_uri))
        
        self.g.add((self.project_uri, MV.hasAudio, audio_asset))
        return audio_asset

    def add_timeline_with_shots(self, shots_data):
        """
        shots_data: list of dicts [{'order': 1, 'start': 0, 'end': 30, 'image_uri': '...', 'label': '...'}]
        """
        timeline_uri = MV.timeline_main
        self.g.add((timeline_uri, RDF.type, MV.Timeline))
        self.g.add((timeline_uri, rdflib.RDFS.label, Literal("메인 타임라인", lang="ko")))
        
        for idx, shot in enumerate(shots_data, 1):
            image_uri = MV[f"image_{idx:02d}"]
            shot_uri = MV[f"shot_{idx:02d}"]
            
            # Image asset
            self.g.add((image_uri, RDF.type, MV.ImageAsset))
            self.g.add((image_uri, MV.fileUri, URIRef(shot['image_uri'])))
            self.g.add((image_uri, MV.width, Literal(1920, datatype=XSD.integer)))
            self.g.add((image_uri, MV.height, Literal(1080, datatype=XSD.integer)))
            self.g.add((self.project_uri, MV.hasImage, image_uri))
            
            # Shot
            self.g.add((shot_uri, RDF.type, MV.Shot))
            self.g.add((shot_uri, rdflib.RDFS.label, Literal(shot.get('label', f"장면 #{idx}"), lang="ko")))
            self.g.add((shot_uri, MV.orderIndex, Literal(int(shot['order']), datatype=XSD.integer)))
            self.g.add((shot_uri, MV.startSecond, Literal(Decimal(str(shot['start'])), datatype=XSD.decimal)))
            self.g.add((shot_uri, MV.endSecond, Literal(Decimal(str(shot['end'])), datatype=XSD.decimal)))
            self.g.add((shot_uri, MV.usesImage, image_uri))
            
            self.g.add((timeline_uri, MV.hasShot, shot_uri))
            
        self.g.add((self.project_uri, MV.hasTimeline, timeline_uri))
        return timeline_uri

    def finalize_video(self, video_uri, duration_sec):
        video_asset = MV.video_main
        render_task = MV.task_render
        editor_agent = MV.agent_editor
        
        self.g.add((editor_agent, RDF.type, MV.AIAgent))
        self.g.add((editor_agent, rdflib.RDFS.label, Literal("영상 편집 에이전트", lang="ko")))
        
        self.g.add((render_task, RDF.type, MV.RenderTask))
        self.g.add((render_task, MV.status, Literal("completed")))
        self.g.add((render_task, PROV.wasAssociatedWith, editor_agent))
        
        self.g.add((video_asset, RDF.type, MV.MusicVideo))
        self.g.add((video_asset, rdflib.RDFS.label, Literal("최종 렌더링 뮤직비디오", lang="ko")))
        self.g.add((video_asset, MV.fileUri, URIRef(video_uri)))
        self.g.add((video_asset, MV.durationSeconds, Literal(Decimal(str(duration_sec)), datatype=XSD.decimal)))
        self.g.add((video_asset, MV.usesAudio, MV.audio_main))
        self.g.add((video_asset, MV.hasTimeline, MV.timeline_main))
        self.g.add((video_asset, PROV.wasGeneratedBy, render_task))
        
        self.g.add((self.project_uri, MV.hasFinalVideo, video_asset))
        return video_asset

    def validate(self):
        shapes_path = os.path.join(BASE_DIR, "mv-shapes.ttl")
        shapes_graph = load_shape_graph(BASE_DIR, 'mv-shapes.ttl')
        ont_graph = load_schema_graph(BASE_DIR, "mv-schema.ttl")
        
        phases = validate_phases(self.g, ont_graph, shapes_graph)
        return phases['conforms'], phases['report_text']

    def export(self, file_prefix="auto_project"):
        ttl_path = os.path.join(BASE_DIR, f"{file_prefix}.ttl")
        jsonld_path = os.path.join(BASE_DIR, f"{file_prefix}.jsonld")
        
        self.g.serialize(destination=ttl_path, format="turtle")
        self.g.serialize(destination=jsonld_path, format="json-ld", indent=2)
        return ttl_path, jsonld_path

if __name__ == "__main__":
    builder = MusicVideoOntologyBuilder(project_id="demo_p01", title="파이프라인 자동화 60초 뮤직비디오")
    builder.add_audio("https://example.org/assets/demo_song.wav", duration_sec=60, bpm=128, genre="CityPop")
    builder.add_timeline_with_shots([
        {"order": 1, "start": 0, "end": 30, "image_uri": "https://example.org/assets/img01.png", "label": "첫 번째 밤거리 샷"},
        {"order": 2, "start": 30, "end": 60, "image_uri": "https://example.org/assets/img02.png", "label": "두 번째 드라이브 샷"}
    ])
    builder.finalize_video("https://example.org/assets/demo_video.mp4", duration_sec=60)
    
    conforms, report = builder.validate()
    print(f"Pipeline Test Validation: {conforms}")
    if conforms:
        ttl, jsonld = builder.export("auto_project_demo")
        print(f"Exported: {ttl}")

