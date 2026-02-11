# Author: urumb
import ast
from typing import List
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

    def run(self, state: AuditorState) -> AuditorState:
        """
        Orchestrates decomposition.
        """
        print("--- Manager Agent: Decomposing Code ---")
        original_code = state.get("original_code", "")
        snippets = self.split_code(original_code)
        
        # Update state
        return {"code_snippets": snippets}
