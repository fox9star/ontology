"""
Automated Test Runner for AI Agent Ontology Ecosystem.
Discovers and executes all unit tests in the tests/ directory.
"""

from pathlib import Path
import os
import sys
import tempfile
import unittest

def main():
    # Route application mutation records from the test process to a disposable
    # file so a full suite never pollutes the user's durable workspace audit log.
    previous_audit_path = os.environ.get("ONTOLOGY_AUDIT_LOG_PATH")
    try:
        with tempfile.TemporaryDirectory(prefix="ontology-tests-") as temporary_state:
            os.environ["ONTOLOGY_AUDIT_LOG_PATH"] = str(Path(temporary_state) / "audit.jsonl")
            result = _run_suite()
    finally:
        if previous_audit_path is None:
            os.environ.pop("ONTOLOGY_AUDIT_LOG_PATH", None)
        else:
            os.environ["ONTOLOGY_AUDIT_LOG_PATH"] = previous_audit_path
    sys.exit(result)


def _run_suite():
    print("=" * 65)
    print("  AI 에이전트 온톨로지 에코시스템 단위 테스트 스위트 (Unit Tests)  ")
    print("=" * 65)
    
    loader = unittest.TestLoader()
    base_dir = Path(__file__).resolve().parent
    suite = loader.discover(str(base_dir / "tests"), pattern="test_*.py", top_level_dir=str(base_dir / "tests"))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("-" * 65)
    print(f"테스트 실행: {result.testsRun}개")
    print(f"실패: {len(result.failures)}개, 오류: {len(result.errors)}개, 건너뜀: {len(result.skipped)}개")
    print("=" * 65)
    
    return 0 if result.wasSuccessful() else 1

if __name__ == "__main__":
    main()
