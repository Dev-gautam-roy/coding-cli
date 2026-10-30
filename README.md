<div align="center">

# 🩺 RepoMedic CLI

**A Safe, Evidence-Based Terminal Agent for Repository Diagnosis and Verified Repair**

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://python.org)
[![Hackathon](https://img.shields.io/badge/Nebius%20×%20NVIDIA-Global%20AI%20Hackathon-76B900.svg)](https://nebiusglobalaihackathon.devpost.com/)
[![Track](https://img.shields.io/badge/Track-Coding%20%26%20Agentic%20Engineering-purple.svg)](https://nebiusglobalaihackathon.devpost.com/)
[![Model](https://img.shields.io/badge/Model-NVIDIA%20Nemotron%20%7C%20OpenAI%20Compatible-76B900.svg)](https://nebius.com/services/token-factory/nemotron)
[![Platform](https://img.shields.io/badge/Infra-Nebius%20%7C%20NVIDIA%20NIM%20%7C%20Any%20LLM-00D26A.svg)](https://docs.tokenfactory.nebius.com/quickstart)

*RepoMedic bridges the gap between chat-based LLM suggestions and reproducible software engineering repairs.*

</div>

---

## 📌 Executive Summary

When a build fails, an import breaks, or a regression test crashes, developers often copy-paste errors into an AI chat window. While chat models can explain syntax errors, **conversational advice cannot prove that a patch works in an actual repository**. Moreover, granting an autonomous agent unbounded filesystem access or arbitrary shell execution introduces severe security and stability risks.

**RepoMedic CLI** is a human-in-the-loop terminal coding agent designed for safe repository repair:
1. **Bounded Context**: Ingests only relevant project manifests, targeted source files, and truncated error logs—automatically redacting credentials and API keys.
2. **Flexible Model Engine**: Works with **Nebius Token Factory** (NVIDIA Nemotron), **NVIDIA NIM** (free without card), **OpenAI**, **Groq**, **OpenRouter**, or any standard OpenAI-compatible API.
3. **Deterministic Security Boundary**: Validates every patch target before disk operations, strictly rejecting parent traversal (`..`), absolute paths, repository metadata (`.git`), and symlink escapes.
4. **Human Approval Gate**: Interactive preview of unified diffs requiring explicit confirmation before any file modification.
5. **Verified Evidence**: Executes allowlisted test profiles (`pytest`, `unittest`) in disposable copies with strict timeouts, reporting real subprocess exit codes instead of trusting an LLM's claim of success.

---

## ⏱️ Current Status & Hackathon Implementation Timeline

> **Overall Progress: 6 / 7 Milestones Completed (~86%)**  
> `████████████████████████████████████░░░░░░`  
> *Target Submission Deadline: 30 October 2026 (10:00 AM PT / 10:30 PM IST)*

| Phase / Day | Focus & Deliverable | Exit Criterion | Status |
|:---|:---|:---|:---:|
| **Day 1** (Oct 24) | Repo foundation, multi-provider API client, schemas & base fixture | Live inference verified & sample fixture defined | ![Completed](https://img.shields.io/badge/Status-Completed-brightgreen.svg) |
| **Day 2** (Oct 25) | CLI skeleton, project discovery, bounded context & secret redaction | Bounded context collected without secret leaks | ![Completed](https://img.shields.io/badge/Status-Completed-brightgreen.svg) |
| **Day 3** (Oct 26) | Structured Pydantic diagnosis & deterministic patch validator | Traversal and malformed patches strictly blocked | ![Completed](https://img.shields.io/badge/Status-Completed-brightgreen.svg) |
| **Day 4** (Oct 27) | Human approval gate, diff preview & safe test runner | Predefined test passes and exit code is reported | ![Completed](https://img.shields.io/badge/Status-Completed-brightgreen.svg) |
| **Day 5** (Oct 28) | Security regression suite & cross-platform testing (Win/Linux) | 24/24 pytest suite passing cleanly | ![Completed](https://img.shields.io/badge/Status-Completed-brightgreen.svg) |
| **Day 6** (Oct 29) | Public repository, Apache 2.0 license, full docs & automated demo | Clean clone works & demo script succeeds | ![Completed](https://img.shields.io/badge/Status-Completed-brightgreen.svg) |
| **Day 7** (Oct 30) | Under 3-minute video demo, tool feedback & Devpost submission | Devpost submission completed before deadline | ![In Progress](https://img.shields.io/badge/Status-In%20Progress-yellow.svg) |

```mermaid
flowchart LR
    D1["Day 1: Setup & API"] --> D2["Day 2: Context & Scanner"]
    D2 --> D3["Day 3: Nemotron & Validator"]
    D3 --> D4["Day 4: Approval & Runner"]
    D4 --> D5["Day 5: 24x Tests & Polish"]
    D5 --> D6["Day 6: Public Repo & Demo"]
    D6 --> D7["Day 7: Demo Video & Devpost"]

    classDef done fill:#2ea44f,stroke:#22863a,color:#fff;
    classDef active fill:#e3b341,stroke:#d99b1a,color:#000;

    class D1,D2,D3,D4,D5,D6 done;
    class D7 active;
```

---

## 🏗️ Architecture & Data Flow

```mermaid
flowchart TD
    A["User in Terminal"] --> B["CLI Command Parser (repomedic)"]
    B --> C["Discovery & Bounded Context Engine"]
    C -.->|"Apply file caps & secret redaction"| D["Context Bundle"]
    D --> E["AI Inference (Nebius Nemotron / NVIDIA NIM / Any LLM)"]
    E --> F["Structured Pydantic Diagnosis + Patch"]
    F --> G{"Deterministic Patch & Security Validator"}
    G -- "Traversal / Symlink / Malformed" --> H["Rejected & Aborted Safely"]
    G -- "Valid In-Workspace Targets" --> I["Interactive Human Approval Gate"]
    I -- "Declined" --> J["Exit without Modifying Files"]
    I -- "Approved" --> K["Disposable Work Copy / Target Workspace"]
    K --> L["Allowlisted Subprocess Test Runner (pytest/unittest)"]
    L --> M["Evidence Report: Genuine Exit Code & Logs"]
```

---

## 🌟 Core Features

- **Universal Model Compatibility**: Supports **Nebius Token Factory**, **NVIDIA NIM**, **OpenAI**, **Groq**, **OpenRouter**, **DeepSeek**, or local endpoints (Ollama / vLLM).
- **Auto-Provider Detection**: Automatically infers base URLs, recommended models, and auth patterns from your environment variables or key format.
- **OWASP-Compliant Command Execution**: Safe subprocess execution with argument arrays (`shell=False`), eliminating shell-string interpolation risks.
- **Traversal Defense**: Strict path resolution guaranteeing that model-authored patches cannot escape the repository root.
- **Heuristic Secret Redaction**: Masks Bearer tokens, GitHub personal access tokens, and API keys before repository context leaves the local machine.
- **Deterministic Test Fixtures**: Ships with a reproducible failing fixture (`fixtures/broken_sample_project/`) for immediate testing and verification without requiring live API quotas.
- **Terminal UI**: Colored diff rendering, status tables, and diagnostic panels powered by Typer and Rich.

---

## ⚡ Quickstart Guide (Up & Running in 2 Minutes)

Follow these simple steps to install, configure, and run RepoMedic on your machine.

### Prerequisites
- **Python 3.11+** installed (`python --version`)
- **Git** installed and available in PATH
- **Any AI API Key** (Nebius Token Factory, NVIDIA NIM, OpenAI, Groq, OpenRouter, or local LLM)

---

### Step 1: Clone & Setup Environment

#### 🐧 Linux / macOS:
```bash
# 1. Clone the repository
git clone https://github.com/Dev-gautam-roy/coding-cli.git repomedic
cd repomedic

# 2. Create and activate a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install RepoMedic in editable mode
pip install --upgrade pip
pip install -e ".[dev]"
```

#### 🪟 Windows (PowerShell):
```powershell
# 1. Clone the repository
git clone https://github.com/Dev-gautam-roy/coding-cli.git repomedic
cd repomedic

# 2. Create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install RepoMedic in editable mode
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

---

### Step 2: Configure Your API Key

Create your local `.env` configuration file from the template:

**Linux / macOS:**
```bash
cp .env.example .env
```
**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

Open `.env` in any editor and set **ONE** of the following options:

#### Option A: Nebius Token Factory (Official Hackathon Provider)
```env
NEBIUS_API_KEY=your_token_factory_key
NEBIUS_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1/
NEBIUS_MODEL=nvidia/Nemotron-3_5-Lightning
```

#### Option B: NVIDIA NIM (Free instant key, no credit card required at [build.nvidia.com](https://build.nvidia.com))
```env
NVIDIA_API_KEY=nvapi-your_nvidia_key_here
```

#### Option C: OpenAI
```env
OPENAI_API_KEY=sk-your_openai_key_here
OPENAI_MODEL=gpt-4o-mini
```

#### Option D: Groq (Ultra-fast free tier at [console.groq.com](https://console.groq.com))
```env
GROQ_API_KEY=gsk_your_groq_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

#### Option E: Local LLMs (Ollama / vLLM / LM Studio)
```env
LLM_API_KEY=dummy-token
LLM_BASE_URL=http://localhost:11434/v1/
LLM_MODEL=llama3.2
```

> **Note**: `.env` is ignored by Git to ensure your secrets are never committed.

---

### Step 3: Run the Pre-Flight Check (`repomedic doctor`)

Verify your installation, Python environment, Git path, and AI credentials:

```bash
repomedic doctor
```

**Expected output:**
```
+------------------------------+
| RepoMedic Environment Doctor |
+------------------------------+
                       System & Configuration Check                        
+-------------------------------------------------------------------------+
| Component         | Status     | Details                                |
|-------------------+------------+----------------------------------------|
| Python Runtime    | OK         | Python 3.13.2 (Supported)              |
| Git Executable    | OK         | C:\Program Files\Git\cmd\git.EXE       |
| Detected Provider | OK         | Nebius Token Factory (or NVIDIA NIM)   |
| API Key           | CONFIGURED | Key: nvap...7890                       |
| Base URL          | OK         | https://integrate.api.nvidia.com/v1/   |
| Configured Model  | OK         | nvidia/llama-3.1-nemotron-70b-instruct |
+-------------------------------------------------------------------------+
```

---

### Step 4: Run the Automated 5-Step Demo

To witness the entire lifecycle—from baseline test failure, AI-driven diagnosis, security gate validation, diff inspection, and passing verification—simply run:

```bash
python demo/app.py
```

This self-contained script runs on the bundled deterministic fixture and proves the repair cycle end-to-end!

---

### Step 5: Test on Your Own Repository

To diagnose and repair any repository:

```bash
# 1. Inspect repository structure & manifests
repomedic inspect /path/to/repo

# 2. Diagnose an issue (optionally pass test/build error logs)
repomedic diagnose /path/to/repo --log /path/to/test.log --out /path/to/fix.json

# 3. Safely preview and apply an approved unified diff patch
repomedic apply /path/to/repo --patch /path/to/fix.patch

# 4. Verify that the fix passes repository tests
repomedic verify /path/to/repo --profile pytest
```

---

## 💻 CLI Command Reference

| Command | Usage | Description |
|:---|:---|:---|
| **`repomedic doctor`** | `repomedic doctor` | Health check for Python, Git, and active AI model provider configuration. |
| **`repomedic inspect`** | `repomedic inspect [PATH]` | Discovers project manifests (`pyproject.toml`, `requirements.txt`, etc.) and candidate source files. |
| **`repomedic diagnose`** | `repomedic diagnose [PATH] [--log FILE] [--out FILE]` | Collects bounded context, queries LLM, and outputs structured diagnosis + unified diff. |
| **`repomedic apply`** | `repomedic apply [PATH] --patch FILE [-y/--yes]` | Validates security boundary (blocks directory traversal), renders color diff preview, and requests explicit approval. |
| **`repomedic verify`** | `repomedic verify [PATH] [--profile pytest\|unittest]` | Executes allowlisted test runner in isolated environment and captures exit code evidence. |

---

## 🧪 Test Suite & Acceptance Matrix

RepoMedic includes automated unit and regression tests covering all security boundaries, multi-provider configuration, schema validations, and process runners:

```bash
pytest
```

### Verified Acceptance Matrix

| Test ID | Scenario | Verification Status |
|:---:|:---|:---:|
| **AT-01** | Known fixture contains repairable defect | **PASSED** (Diagnosed in `fixtures/broken_sample_project`) |
| **AT-02** | Model returns malformed patch or invalid hunk | **PASSED** (`test_patch_validator.py` rejects invalid hunks) |
| **AT-03** | Patch attempts path traversal (`../outside.txt`) | **PASSED** (`test_security.py` blocks escape) |
| **AT-04** | User declines patch approval | **PASSED** (Workspace remains unmodified on rejection) |
| **AT-05** | Approved patch fixes the fixture | **PASSED** (Verified exit code `0` on test suite rerun) |
| **AT-06** | Test runner process exceeds timeout | **PASSED** (`test_runner.py` reports `timed_out`) |
| **AT-07** | Secret leakage & credential protection | **PASSED** (`test_security.py` redacts API keys and tokens) |
| **AT-08** | Fresh checkout setup | **PASSED** (Clean install from `pyproject.toml`) |
| **AT-09** | Multi-Provider resolution (Nebius, NIM, OpenAI, Groq, Custom) | **PASSED** (`test_config.py` auto-detects providers) |

---

## 🛡️ Security & Threat Model

| Threat | RepoMedic Mitigation |
|:---|:---|
| **Arbitrary Command Execution** | Model is never permitted to emit shell commands for execution; test execution is strictly restricted to allowlisted profiles (`pytest`, `unittest`) using `shell=False`. |
| **Path Traversal / Arbitrary File Overwrite** | Paths are canonicalized with `Path.resolve()` and tested with `relative_to(root)`. Any path containing `..`, absolute drives, or `.git` directories is rejected immediately. |
| **Secret Leakage to Remote LLM** | Known credential formats (GitHub PATs, AWS/GCP secrets, Bearer tokens, API keys) and sensitive file extensions (`.env`, `.pem`, `.key`, `id_rsa`) are stripped prior to inference. |
| **Silent / Hallucinated Fixes** | LLM self-assessments (*"I have fixed this"*) are disregarded; only genuine OS process exit codes (`returncode == 0`) are reported as verification evidence. |

---

## 📋 Hackathon Submission Alignment

- **Event**: Nebius × NVIDIA Global AI Hackathon
- **Track**: Coding and Agentic Engineering
- **Model Integration**: NVIDIA Nemotron (via Nebius Token Factory or NVIDIA NIM) + Any OpenAI-compatible fallback
- **Open Source**: Publicly licensed under Apache 2.0
- **Reproducibility**: Pinned dependencies, reproducible failing fixture, and runnable local demo.

---

## 📄 License

This project is licensed under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for details.
