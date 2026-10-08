"""
Multi-Agent Workflow Simulator
Simulates multi-agent pipeline executions and generates standards-compliant
PROV-O / Domain triples step-by-step for real-time visualization.
"""

import time
import uuid
import rdflib
from rdflib import URIRef, Literal, RDF, RDFS

MV_NS = rdflib.Namespace("https://example.org/mv#")
PROV_NS = rdflib.Namespace("http://www.w3.org/ns/prov#")

SIMULATION_STEPS = [
    {
        "step": 1,
        "phase": "기획 및 스토리보드 설계",
        "agent_name": "스토리보드 기획 에이전트 (PlanningAgent)",
        "agent_id": "Agent_Planner_01",
        "task_name": "기획안 및 장면 분할 작업",
        "task_id": "Task_Plan_01",
        "task_type": "PlanningTask",
        "output_asset": "storyboard_spec.json",
        "output_type": "DocumentAsset",
        "details": "전체 음악 구성 분석, 4개 주요 장면(Intro, Verse, Chorus, Outro) 분할 및 연출 키워드 확정."
    },
    {
        "step": 2,
        "phase": "비주얼 & 오디오 프롬프트 생성",
        "agent_name": "프롬프트 엔지니어링 에이전트 (PromptAgent)",
        "agent_id": "Agent_Prompt_02",
        "task_name": "고해상도 비디오/오디오 프롬프트 설계",
        "task_id": "Task_PromptGen_02",
        "task_type": "PromptEngineeringTask",
        "output_asset": "prompt_master.txt",
        "output_type": "PromptAsset",
        "details": "시네마틱 조명, 8K 사이버펑크 네온 색감, 카메라 무빙(Orbit, Pan) 가이드 프롬프트 빌드."
    },
    {
        "step": 3,
        "phase": "AI 배경 음악 및 사운드트랙 생성",
        "agent_name": "음악 생성 AI 에이전트 (SunoAgent)",
        "agent_id": "Agent_Music_03",
        "task_name": "신스웨이브 128BPM 음원 생성 작업",
        "task_id": "Task_MusicGen_03",
        "task_type": "AudioGenerationTask",
        "output_asset": "cyber_synthwave_bgm.mp3",
        "output_type": "AudioAsset",
        "duration": 45.0,
        "details": "Suno v3 기반 44.1kHz 스테레오 신스웨이브 BGM 트랙 생성 완료."
    },
    {
        "step": 4,
        "phase": "보컬 분리 및 다국어 자막 싱크",
        "agent_name": "보컬/자막 처리 에이전트 (DemucsWhisperAgent)",
        "agent_id": "Agent_VocalSync_04",
        "task_name": "AI 보컬 추출 및 타임스탬프 자막 정렬",
        "task_id": "Task_VocalSync_04",
        "task_type": "VocalProcessingTask",
        "output_asset": "lyrics_synced.vtt",
        "output_type": "SubtitleAsset",
        "details": "Demucs 4-stem 보컬 분리 및 Whisper 기반 단어 단위 타임코드 싱크 자막 생성."
    },
    {
        "step": 5,
        "phase": "비디오 프레임 및 모션 비주얼 렌더링",
        "agent_name": "비디오 확산 AI 에이전트 (DiffusionAgent)",
        "agent_id": "Agent_VideoGen_05",
        "task_name": "다중 장면 모션 비디오 렌더링",
        "task_id": "Task_VideoGen_05",
        "task_type": "VideoGenerationTask",
        "output_asset": "final_music_video.mp4",
        "output_type": "VideoAsset",
        "duration": 45.0,
        "details": "Wan2.1 / SVD 기반 고화질 비디오 렌더링 및 음원 합성 완료."
    },
    {
        "step": 6,
        "phase": "품질 검토 및 SHACL 온톨로지 승인",
        "agent_name": "품질 검증 에이전트 (ReviewQualityAgent)",
        "agent_id": "Agent_QA_06",
        "task_name": "최종 아티팩트 무결성 및 적합성 검사",
        "task_id": "Task_QAReview_06",
        "task_type": "ReviewTask",
        "output_asset": "quality_report.json",
        "output_type": "ReportAsset",
        "details": "PySHACL 스펙 검증 통과, 해상도(1920x1080) 및 오디오 비트레이트 정합성 확인 완료 (APPROVED)."
    }
]


def run_pipeline_step(step_number, session_id=None):
    """
    Executes a single step (1 to 6) of the multi-agent pipeline.
    Returns step metadata and RDF triples formatted for the frontend.
    """
    if step_number < 1 or step_number > len(SIMULATION_STEPS):
        raise ValueError(f"Step {step_number} is out of bounds (1-{len(SIMULATION_STEPS)})")

    cfg = SIMULATION_STEPS[step_number - 1]
    sid = session_id or uuid.uuid4().hex[:6]

    agent_uri = MV_NS[f"{cfg['agent_id']}_{sid}"]
    task_uri = MV_NS[f"{cfg['task_id']}_{sid}"]
    asset_uri = MV_NS[f"Asset_{sid}_{cfg['output_asset'].replace('.', '_')}"]

    triples = [
        {"subject": str(agent_uri), "predicate": str(RDF.type), "object": str(MV_NS.Agent)},
        {"subject": str(agent_uri), "predicate": str(RDFS.label), "object": cfg["agent_name"]},
        {"subject": str(task_uri), "predicate": str(RDF.type), "object": str(MV_NS[cfg["task_type"]])},
        {"subject": str(task_uri), "predicate": str(RDFS.label), "object": cfg["task_name"]},
        {"subject": str(task_uri), "predicate": str(MV_NS.status), "object": "COMPLETED"},
        {"subject": str(task_uri), "predicate": str(PROV_NS.wasAssociatedWith), "object": str(agent_uri)},
        {"subject": str(asset_uri), "predicate": str(RDF.type), "object": str(MV_NS[cfg["output_type"]])},
        {"subject": str(asset_uri), "predicate": str(RDFS.label), "object": cfg["output_asset"]},
        {"subject": str(asset_uri), "predicate": str(PROV_NS.wasGeneratedBy), "object": str(task_uri)},
        {"subject": str(asset_uri), "predicate": str(MV_NS.fileUri), "object": f"media/{cfg['output_asset']}"}
    ]

    new_nodes = [
        {"id": str(agent_uri), "label": cfg["agent_id"], "group": "Agent", "color": "#3b82f6", "shape": "box"},
        {"id": str(task_uri), "label": cfg["task_id"], "group": "Task", "color": "#10b981", "shape": "dot"},
        {"id": str(asset_uri), "label": cfg["output_asset"], "group": "Asset", "color": "#f59e0b", "shape": "diamond"}
    ]

    new_edges = [
        {"from": str(task_uri), "to": str(agent_uri), "label": "wasAssociatedWith", "arrows": "to"},
        {"from": str(asset_uri), "to": str(task_uri), "label": "wasGeneratedBy", "arrows": "to"}
    ]

    return {
        "step": step_number,
        "total_steps": len(SIMULATION_STEPS),
        "session_id": sid,
        "phase": cfg["phase"],
        "agent": cfg["agent_name"],
        "task": cfg["task_name"],
        "output_asset": cfg["output_asset"],
        "details": cfg["details"],
        "triples": triples,
        "new_nodes": new_nodes,
        "new_edges": new_edges,
        "is_completed": step_number == len(SIMULATION_STEPS)
    }
