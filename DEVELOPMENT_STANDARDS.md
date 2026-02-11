# Development Standards & Engineering Guidelines

**Project:** Decentralized Multi-Agent Code Auditor  
**Maintainer:** urumb

## 1. Architecture & Logic Patterns
- **Orchestration:** All agent workflows are managed via **LangGraph**. The graph definition serves as the single source of truth for agent interaction logic.
- **State Management:** Agents communicate exclusively through a shared `TypedDict` state object defined in `src/state.py`. Direct agent-to-agent calls are prohibited to maintain loose coupling.
- **Modularity:** 
  - `src/agents/`: strictly contains agent logic and prompt templates.
  - `src/utils/`: contains pure utility functions and database wrappers (e.g., ChromaDB).

## 2. Coding Standards
- **Python Version:** 3.12+ features (type hinting, pattern matching) are encouraged.
- **Typing:** Strong typing is enforced. All function signatures must include type hints.
- **Docstrings:** Google-style docstrings are required for every class and public function.
- **Error Handling:** Use explicit `try-except` blocks. Silent failures are not allowed; errors must be logged or propagated to the final report.

## 3. Repository & Environment
- **Dependency Management:** All dependencies must be pinned in `requirements.txt`.
- **Configuration:** Local environment variables (API keys, model paths) are managed via `.env`. A `.env.example` must be kept in sync.
- **Privacy:** Local LLMs (Ollama) are the default. No code execution or data transmission to external APIs is permitted by default.
