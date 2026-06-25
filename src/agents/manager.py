# Author: urumb
import ast
from typing import Dict, List
from ..state import AuditorState

class ManagerAgent:
    def __init__(self):
        pass

    def split_code(self, code: str) -> List[str]:
        """
        Splits Python code into functions and classes using AST.
        Falls back to simple chunking if AST fails (non-python).
        """
        try:
            tree = ast.parse(code)
            chunks = []
            lines = code.splitlines()
            
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # Extract the segment
                    start = node.lineno - 1
                    end = node.end_lineno
                    chunk = "\n".join(lines[start:end])
                    chunks.append(chunk)
                else:
                    # For top-level code or imports, we might group them or ignore?
                    # Let's simple capture them as "Main Body" if important, 
                    # but for now, let's focus on functions/classes which are usually the unit of audit.
                    pass
            
            # If no functions/classes found, treat whole file as one chunk
            if not chunks:
                return [code]
                
            return chunks

        except SyntaxError:
            # Not valid python or other language
            return [code]

    def build_execution_plan(self, code: str, repository_file_count: int = 1) -> Dict[str, object]:
        """
        Chooses the minimum useful agent set for the submitted input.
        """
        if len(code) < 200:
            return {
                "agents": ["security"],
                "reason": "Small snippet",
            }

        if repository_file_count > 1 or len(code) >= 5000:
            return {
                "agents": ["security", "performance", "quality", "reviewer"],
                "reason": "Large repository input",
            }

        return {
            "agents": ["security", "performance", "quality", "reviewer"],
            "reason": "Medium-sized input",
        }

    def run(self, state: AuditorState) -> AuditorState:
        """
        Orchestrates decomposition.
        """
        print("--- Manager Agent: Decomposing Code ---")
        original_code = state.get("original_code", "")
        repository_file_count = state.get("repository_file_count") or 1
        snippets = self.split_code(original_code)
        execution_plan = self.build_execution_plan(original_code, repository_file_count)
        
        # Update state
        return {
            "code_snippets": snippets,
            "execution_plan": execution_plan,
        }
