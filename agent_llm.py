"""Compatibility facade: model-API generation now queues actual Codex work."""
from codex_jobs import check_codex_status, submit_job


def check_llm_status():
    return check_codex_status()


def generate_agent_execution(domain, agent_name, task_title, prompt, model_version=None):
    return submit_job({'ont': domain, 'agent_name': agent_name,
                       'task_name': task_title, 'prompt': prompt})
