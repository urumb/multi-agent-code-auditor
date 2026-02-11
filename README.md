# Decentralized Multi-Agent Code Auditor

**Author:** [urumb](https://github.com/urumb)  
**Status:** Active Development

## Overview

The **Decentralized Multi-Agent Code Auditor** is a sophisticated, privacy-first static analysis tool designed to autonomously audit codebases for security vulnerabilities, performance bottlenecks, and code quality issues. 

Built on a **Modular Multi-Agent Architecture using LangGraph**, the system orchestrates a team of specialized AI agents that collaborate to decompose, analyze, and synthesize feedback on provided source code. Unlike traditional linters, it utilizes local Large Language Models (LLMs) via **Ollama** to provide semantic understanding and context-aware recommendations, while ensuring all data remains on the local machine.

## Key Features

- 🧠 **Contextual Memory**: Integrates ChromaDB to recall historical vulnerabilities and optimizations, ensuring the system "learns" from previous audits.
- ⚡ **Asynchronous Parallelism**: Leverages LangGraph to run Security and Performance scans concurrently, minimizing total audit latency.
- 🔒 **Zero-Trust Privacy**: Executes all inference locally via Ollama; no source code or audit data is ever transmitted to a third-party API.
- 📄 **Synthesis Reporting**: A dedicated Reviewer Agent aggregates multi-agent outputs into a cohesive, prioritized Markdown report.

## System Architecture

The core logic relies on a state graph where code flows through a pipeline of specialized agents.

```mermaid
graph TD
    Start([Start]) --> Manager[Manager Agent\n(Decomposition)]
    Manager --> Retrieve[Memory Retrieval\n(ChromaDB)]
    
    subgraph Analysis Layer [Parallel Execution]
        Retrieve --> Security[Security Agent\n(OWASP / CWE Scanning)]
        Retrieve --> Performance[Performance Agent\n(Big-O / Memory)]
    end
    
    Security --> Reviewer[Reviewer Agent\n(Synthesis & Reporting)]
    Performance --> Reviewer
    
    Reviewer --> Save[Persist Findings]
    Save --> End([End])
    
    style Start fill:#f9f,stroke:#333
    style End fill:#f9f,stroke:#333
    style Manager fill:#bbf,stroke:#333
    style Security fill:#f96,stroke:#333
    style Performance fill:#9f6,stroke:#333
    style Reviewer fill:#ff9,stroke:#333
```

### Technical Components

- **LangGraph**: Orchestrates the state machine and agent workflow.
- **Ollama**: Provides local inference for agents (default: `llama3`).
- **ChromaDB**: Implements RAG (Retrieval-Augmented Generation) memory to recall past audit findings and ensure consistency across analysis sessions.
- **Python 3.12+**: Core runtime environment.

## Getting Started

### Prerequisites

- **Python 3.10+**
- **Ollama** running locally (`http://localhost:11434`)
- Recommended Model: `llama3` or `deepseek-coder`

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/urumb/multi-agent-auditor.git
   cd multi-agent-auditor
   ```

2. **Set up virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment:**
   ```bash
   cp .env.example .env
   # Edit .env if your Ollama instance uses a different port
   ```

## Usage

Execute the auditor by pointing it to a target file. The system will decompose the code, run parallel analysis, and generate a Markdown report alongside the source file.

```bash
python main.py path/to/your/code.py
```

### Example
```bash
python main.py vulnerable_code.py
```

## Project Standards

Development follows strict engineering guidelines detailed in [DEVELOPMENT_STANDARDS.md](./DEVELOPMENT_STANDARDS.md).
