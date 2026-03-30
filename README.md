# Decentralized Multi-Agent Code Auditor

A privacy-first static analysis system that autonomously audits codebases for security vulnerabilities, performance bottlenecks, and code quality issues using local LLMs.

## Features
- **Multi-agent architecture:** Specialized agents collaborate to analyze code using LangGraph.
- **GitHub repo support:** Directly clone and analyze repositories.
- **File upload & Paste:** Support for multiple structural inputs via FastAPI.
- **Local LLM (Ollama):** 100% private inference; source code never leaves your machine.

## Setup

1. **Clone & Install Backend**
```bash
git clone https://github.com/urumb/multi-agent-code-auditor.git
cd multi-agent-code-auditor
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Backend Setup

```bash
# Create and activate virtual environment
python -m venv .venv

# Windows (PowerShell)
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
```

### 3. Ollama Setup

```bash
# Pull a recommended model
ollama pull llama3.2
# or
ollama pull deepseek-coder

# Start Ollama (if not running as a service)
ollama serve
```

### 4. Start the Backend

```bash
python main.py
# or
uvicorn main:app --reload
```

### 5. Start the Frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

---

## Usage

Run the auditor against a local source file:

```bash
python main.py vulnerable_code.py
```

The system will:

1. Decompose the file into analyzable chunks
2. Retrieve relevant context from ChromaDB memory
3. Run Security, Performance, and Quality analysis in parallel
4. Synthesize findings via the Reviewer Agent
5. Generate a structured Markdown report

---

## Project Roadmap

- [ ] Repository-level analysis
- [ ] GitHub repository scanning
- [ ] File upload support
- [ ] Streaming agent logs
- [ ] Real-time audit progress visualization
- [ ] Exportable audit reports (PDF / JSON)
- [ ] Multi-language support

---

## Development Standards

Engineering guidelines and coding conventions are documented in [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md).

---

## License

MIT License

---

## Author

**urumb**  
GitHub: [https://github.com/urumb](https://github.com/urumb)