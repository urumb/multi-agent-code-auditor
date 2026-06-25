import unittest
import os
import tempfile

os.makedirs(r"C:\tmp", exist_ok=True)
os.environ["CHROMA_PERSIST_DIRECTORY"] = tempfile.mkdtemp(
    prefix="auditor_test_chroma_",
    dir=r"C:\tmp",
)

from src.agents.manager import ManagerAgent
from src.graph import route_after_manager, route_after_analysis, route_to_planned_agents


class ExecutionPlannerTests(unittest.TestCase):
    def setUp(self):
        self.manager = ManagerAgent()

    def test_small_snippet_runs_security_only(self):
        plan = self.manager.build_execution_plan("print('x')")

        self.assertEqual(plan, {
            "agents": ["security"],
            "reason": "Small snippet",
        })
        self.assertEqual(
            route_after_manager({"execution_plan": plan}),
            "security",
        )
        self.assertEqual(
            route_after_analysis({"execution_plan": plan}),
            "finalize",
        )

    def test_medium_input_runs_security_performance_reviewer(self):
        code = "def example():\n    return 'x'\n" * 20
        plan = self.manager.build_execution_plan(code)

        self.assertEqual(plan, {
            "agents": ["security", "performance", "quality", "reviewer"],
            "reason": "Medium-sized input",
        })
        self.assertEqual(
            route_to_planned_agents({"execution_plan": plan}),
            ["security", "performance", "quality"],
        )
        self.assertEqual(
            route_after_analysis({"execution_plan": plan}),
            "reviewer",
        )

    def test_large_repository_uses_all_enabled_agents(self):
        code = "def example():\n    return 'x'\n" * 20
        plan = self.manager.build_execution_plan(code, repository_file_count=5)

        self.assertEqual(plan, {
            "agents": ["security", "performance", "quality", "reviewer"],
            "reason": "Large repository input",
        })


if __name__ == "__main__":
    unittest.main()
