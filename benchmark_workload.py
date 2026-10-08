"""Deterministic canonical MV workload and independently calculated answers."""

from decimal import Decimal
import re
from pathlib import Path

from rdflib import Graph, Literal, Namespace, RDF, RDFS, XSD

ROOT = Path(__file__).resolve().parent
MV = Namespace("https://example.org/mv#")
PROV = Namespace("http://www.w3.org/ns/prov#")
EX = Namespace("https://example.test/benchmark/")
PROJECT_COUNT = 8
QUESTION_PATTERN = re.compile(r"^###\s+(?P<title>.+?)\n\s*\n~~~sparql\n(?P<query>.*?)\n~~~", re.MULTILINE | re.DOTALL)


def catalog_queries():
    source = (ROOT / "COMPETENCY_QUESTIONS.md").read_text(encoding="utf-8")
    return {m.group("title").split(".", 1)[0]: m.group("query")
            for m in QUESTION_PATTERN.finditer(source) if m.group("title").startswith("BMV-")}


def generate_workload(target_triples):
    """Eight complete productions plus scalable, variably documented images.

    Asset IDs and modulo groups are fixed; there is no random input. Each
    timeline has four shots so increasing archive size does not silently
    increase quadratic interval-validation costs.
    """
    if target_triples < 1000:
        raise ValueError("Workload target must be at least 1000 triples")
    graph = Graph()
    graph.bind("mv", MV)
    graph.bind("ex", EX)
    agent = EX.agent
    graph.add((agent, RDF.type, MV.AIAgent))
    graph.add((agent, RDFS.label, Literal("Synthetic archive agent", lang="en")))
    for i in range(PROJECT_COUNT):
        project, brief, audio, video, timeline = [EX[f"{name}{i:02d}"] for name in ("project", "brief", "audio", "video", "timeline")]
        for node, cls in ((project, MV.MusicVideoProject), (brief, MV.CreativeBrief),
                          (audio, MV.AudioAsset), (video, MV.MusicVideo), (timeline, MV.Timeline)):
            graph.add((node, RDF.type, cls))
        for predicate, value in ((MV.hasBrief, brief), (MV.hasAudio, audio),
                                 (MV.hasTimeline, timeline), (MV.hasFinalVideo, video)):
            graph.add((project, predicate, value))
        graph.add((brief, MV.targetDurationSeconds, Literal(Decimal("20"), datatype=XSD.decimal)))
        for node, suffix in ((audio, "wav"), (video, "mp4")):
            graph.add((node, MV.fileUri, EX[f"files/{i:02d}.{suffix}"]))
            graph.add((node, MV.durationSeconds, Literal(Decimal("20"), datatype=XSD.decimal)))
        graph.add((video, MV.usesAudio, audio))
        graph.add((video, MV.hasTimeline, timeline))
    image_count = 0
    while len(graph) < target_triples:
        i = image_count
        image, project = EX[f"image{i:06d}"], EX[f"project{i % PROJECT_COUNT:02d}"]
        graph.add((image, RDF.type, MV.ImageAsset))
        graph.add((image, MV.fileUri, EX[f"files/image{i:06d}.png"]))
        graph.add((image, MV.width, Literal(1920)))
        graph.add((image, MV.height, Literal(1080)))
        graph.add((project, MV.hasImage, image))
        if i % 4 != 0:
            graph.add((image, MV.checksum, Literal(f"{i:064x}")))
        if i % 3 != 0:
            source = EX[f"source{i:06d}"]
            graph.add((image, PROV.wasDerivedFrom, source))
            graph.add((source, RDF.type, PROV.Entity))
            graph.add((source, PROV.wasDerivedFrom, EX[f"raw{i % 16:02d}"]))
        if i < 32:
            project_index, order = i % PROJECT_COUNT, i // PROJECT_COUNT + 1
            shot, timeline = EX[f"shot{i:02d}"], EX[f"timeline{project_index:02d}"]
            graph.add((shot, RDF.type, MV.Shot))
            graph.add((timeline, MV.hasShot, shot))
            graph.add((shot, MV.usesImage, image))
            graph.add((shot, MV.orderIndex, Literal(order)))
            graph.add((shot, MV.startSecond, Literal(Decimal((order - 1) * 5), datatype=XSD.decimal)))
            graph.add((shot, MV.endSecond, Literal(Decimal(order * 5), datatype=XSD.decimal)))
        image_count += 1
    return graph, {"image_count": image_count, "project_count": PROJECT_COUNT,
                   "requested_triples": target_triples, "actual_data_triples": len(graph)}


def expected_answers(metadata):
    """Calculate answers from the documented modulo design, without querying RDF."""
    n = metadata["image_count"]
    uri = lambda local: str(EX[local])
    return {
        "BMV-01": {"variables": ["project", "video", "audio", "timeline"], "rows": [
            [uri(f"project{i:02d}"), uri(f"video{i:02d}"), uri(f"audio{i:02d}"), uri(f"timeline{i:02d}")]
            for i in range(PROJECT_COUNT)]},
        "BMV-02": {"variables": ["project", "imageCount"], "rows": [
            [uri(f"project{i:02d}"), str(len(range(i, n, PROJECT_COUNT)))] for i in range(PROJECT_COUNT)]},
        "BMV-03": {"variables": ["project", "shotCount", "scheduledSeconds"], "rows": [
            [uri(f"project{i:02d}"), "4", "20"] for i in range(PROJECT_COUNT)]},
        "BMV-04": {"variables": ["ancestor"], "rows": sorted([[uri("raw01")], [uri("source000001")]])},
        "BMV-05": {"variables": ["project", "missingChecksumCount"], "rows": [
            [uri(f"project{i:02d}"), str(sum(j % 4 == 0 for j in range(i, n, PROJECT_COUNT)))]
            for i in (0, 4)]},
        "BMV-06": {"variables": ["project", "unknownSourceCount"], "rows": [
            [uri(f"project{i:02d}"), str(sum(j % 3 == 0 for j in range(i, n, PROJECT_COUNT)))]
            for i in range(PROJECT_COUNT)]},
    }


def query_answer(graph, query):
    result = graph.query(query)
    variables = [str(v) for v in result.vars]
    return {"variables": variables, "rows": [[None if row[v] is None else str(row[v]) for v in variables]
                                              for row in result]}
