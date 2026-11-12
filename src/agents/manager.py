# Author: urumb
import logging
import ast
from typing import Dict, List, Tuple
from ..state import AuditorState

logger = logging.getLogger(__name__)

class ManagerAgent:
    # Each snippet costs one LLM call per analysis agent (security,
    # performance, quality), plus the fixed reviewer call. Uncapped
    # decomposition on a file with many functions turns into dozens of
    # sequential local-LLM calls and can blow past any reasonable per-file
    # timeout. Capping keeps worst-case latency bounded and predictable;
    # the largest snippets (the most substantial functions/classes) are
    # kept since they're the most likely to contain real issues.
    MAX_SNIPPETS = 6

    # Target size of one LLM chunk. ~3000 chars is ~800 tokens: comfortably
    # inside the 4096-token context together with the prompt and the capped
    # response, and big enough that small files / small functions are
    # analyzed together in ONE call per agent instead of one call each.
    CHUNK_CHARS = 3000

    def __init__(self):
        pass

    @staticmethod
    def _pack(pieces: List[str], limit: int) -> List[str]:
        """Greedily merge consecutive pieces into chunks of at most ``limit`` chars.

        A piece larger than ``limit`` is split on line boundaries so no single
        LLM call receives more than the model's context can hold.
        """
        chunks: List[str] = []
        current = ""
        for piece in pieces:
            while len(piece) > limit:
                cut = piece.rfind("\n", 0, limit)
                cut = cut if cut > 0 else limit
                if current:
                    chunks.append(current)
                    current = ""
                chunks.append(piece[:cut])
                piece = piece[cut:].lstrip("\n")
            if current and len(current) + len(piece) + 2 > limit:
                chunks.append(current)
                current = piece
            else:
                current = f"{current}\n\n{piece}" if current else piece
        if current.strip():
            chunks.append(current)
        return chunks

    def split_code(self, code: str) -> List[str]:
        return self.split_code_with_stats(code)[0]

    def split_code_with_stats(self, code: str) -> Tuple[List[str], int]:
        """
        Splits code into LLM-sized chunks.

        Small inputs stay whole (one call per agent). Python is split along
        function/class boundaries; other languages (or unparsable Python) are
        split on line boundaries. Neighbouring small pieces are packed
        together to minimize the number of sequential LLM calls.
        """
        if len(code) <= self.CHUNK_CHARS:
            return [code], 1

        pieces: List[str] = []
        try:
            tree = ast.parse(code)
            lines = code.splitlines()
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    pieces.append("\n".join(lines[node.lineno - 1 : node.end_lineno]))
        except SyntaxError:
            pass

        if not pieces:
            pieces = [code]

        chunks = self._pack(pieces, self.CHUNK_CHARS)
        total = len(chunks)
        if total > self.MAX_SNIPPETS:
            chunks = sorted(chunks, key=len, reverse=True)[: self.MAX_SNIPPETS]
        return chunks, total

    def build_execution_plan(self, code: str, repository_file_count: int = 1, depth: str = "full") -> Dict[str, object]:
        """
        Chooses the minimum useful agent set for the submitted input.
        """
        if depth == "quick":
            return {
                "agents": ["security"],
                "reason": "Quick scan (security only)",
            }

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
        logger.info("Manager Agent: decomposing code")
        original_code = state.get("original_code", "")
        repository_file_count = state.get("repository_file_count") or 1
        snippets, total_chunks = self.split_code_with_stats(original_code)
        execution_plan = self.build_execution_plan(original_code, repository_file_count, state.get("depth") or "full")
        execution_plan["chunks_total"] = total_chunks
        execution_plan["chunks_analyzed"] = len(snippets)
        if total_chunks > len(snippets):
            logger.warning(
                "File split into %d chunks; only the %d largest are analyzed",
                total_chunks, len(snippets),
            )
        
        # Update state
        return {
            "code_snippets": snippets,
            "execution_plan": execution_plan,
        }
