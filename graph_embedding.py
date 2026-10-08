"""
Knowledge Graph Embedding & Semantic Similarity Recommendation Engine
Builds structural and lexical feature vectors for RDF entities and calculates
cosine & Jaccard semantic similarity to find top similar agents, tasks, or assets.
Pure Python implementation with zero heavy external dependencies.
"""

import math
import re
from collections import Counter
import rdflib
from rdflib import URIRef, Literal, RDF, RDFS


def tokenize_text(text):
    """Simple tokenizer for Korean and English text."""
    if not text:
        return []
    return [w.lower() for w in re.split(r'[\s_\-\.:/]+', str(text)) if len(w) > 1]


def extract_entity_features(graph, entity_uri):
    """
    Extracts structural topological and lexical feature tokens for an entity node.
    Features include:
      - Direct rdf:type
      - Outgoing predicates (pred_out:<name>)
      - Incoming predicates (pred_in:<name>)
      - Neighbor object types (neighbor_type:<type>)
      - Text tokens from rdfs:label and literals
    """
    s = URIRef(entity_uri)
    features = []

    # 1. Outgoing predicates and object values/types
    for p, o in graph.predicate_objects(s):
        p_name = str(p).split("#")[-1].split("/")[-1]
        features.append(f"pred_out:{p_name}")

        if p == RDF.type:
            t_name = str(o).split("#")[-1].split("/")[-1]
            features.append(f"type:{t_name}")
            features.append(f"type:{t_name}")  # Double weight for type
        elif isinstance(o, URIRef):
            # Neighbor type
            for _, _, ot in graph.triples((o, RDF.type, None)):
                ot_name = str(ot).split("#")[-1].split("/")[-1]
                features.append(f"neighbor_type:{ot_name}")
        elif isinstance(o, Literal):
            tokens = tokenize_text(str(o))
            for tok in tokens:
                features.append(f"token:{tok}")

    # 2. Incoming predicates
    for sub, p in graph.subject_predicates(s):
        p_name = str(p).split("#")[-1].split("/")[-1]
        features.append(f"pred_in:{p_name}")
        for _, _, st in graph.triples((sub, RDF.type, None)):
            st_name = str(st).split("#")[-1].split("/")[-1]
            features.append(f"in_neighbor_type:{st_name}")

    return Counter(features)


def cosine_similarity(vec1, vec2):
    """Computes cosine similarity between two feature count vectors."""
    intersection = set(vec1.keys()) & set(vec2.keys())
    if not intersection:
        return 0.0, []

    numerator = sum(vec1[x] * vec2[x] for x in intersection)
    sum1 = sum(val ** 2 for val in vec1.values())
    sum2 = sum(val ** 2 for val in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0, []

    score = numerator / denominator
    shared = sorted(list(intersection), key=lambda x: vec1[x] * vec2[x], reverse=True)[:5]
    return round(score, 4), shared


def find_similar_nodes(graph, target_uri, top_k=3, min_similarity=0.1):
    """
    Finds the top K most similar entities in the graph to target_uri.
    Returns a list of dicts with uri, label, score, and shared_features.
    """
    target = URIRef(target_uri)
    target_vec = extract_entity_features(graph, target)
    if not target_vec:
        return []

    # Get target type to prioritize or compare across entities
    target_types = set(str(o) for _, _, o in graph.triples((target, RDF.type, None)))

    # Collect all unique candidate subjects in the graph
    candidates = set()
    for s in graph.subjects():
        if isinstance(s, URIRef) and s != target:
            # Check if candidate has a type
            has_type = any(graph.triples((s, RDF.type, None)))
            if has_type:
                candidates.add(s)

    scored = []
    for cand in candidates:
        cand_vec = extract_entity_features(graph, cand)
        sim, shared = cosine_similarity(target_vec, cand_vec)
        if sim >= min_similarity:
            # Get candidate label
            lbl = graph.value(cand, RDFS.label)
            lbl_str = str(lbl) if lbl else str(cand).split("#")[-1].split("/")[-1]

            cand_types = [str(t).split("#")[-1].split("/")[-1] for _, _, t in graph.triples((cand, RDF.type, None))]

            # Clean shared feature names for human readability
            readable_shared = []
            for feat in shared:
                if feat.startswith("type:"):
                    readable_shared.append(f"동일 유형: {feat.split(':')[1]}")
                elif feat.startswith("pred_out:"):
                    readable_shared.append(f"속성: {feat.split(':')[1]}")
                elif feat.startswith("neighbor_type:"):
                    readable_shared.append(f"연계 대상: {feat.split(':')[1]}")
                elif feat.startswith("token:"):
                    readable_shared.append(f"키워드: {feat.split(':')[1]}")

            scored.append({
                "uri": str(cand),
                "name": str(cand).split("#")[-1].split("/")[-1],
                "label": lbl_str,
                "types": cand_types,
                "similarity": sim,
                "shared_features": readable_shared
            })

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:top_k]
