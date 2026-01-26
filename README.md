<p align="center">
  <img src="path/to/your/animated-shark-logo.gif" alt="DweepBot Pro Logo" width="200">
</p>

<h1 align="center">🦈 DweepBot Pro – Autonomous AI Agent Framework</h1>

<p align="center">
  <a href="https://github.com/dweepbot/dweepbot/stargazers"><img src="https://img.shields.io/github/stars/dweepbot/dweepbot?style=social" alt="GitHub Stars"></a>
  <a href="https://github.com/dweepbot/dweepbot/network/members"><img src="https://img.shields.io/github/forks/dweepbot/dweepbot?style=social" alt="GitHub Forks"></a>
  <a href="https://github.com/dweepbot/dweepbot/actions"><img src="https://img.shields.io/github/actions/workflow/status/dweepbot/dweepbot/tests.yml?branch=main" alt="Build Status"></a>
  <a href="https://github.com/dweepbot/dweepbot/blob/main/LICENSE"><img src="https://img.shields.io/github/license/dweepbot/dweepbot" alt="MIT License"></a>
  <a href="https://pypi.org/project/dweepbot/"><img src="https://img.shields.io/pypi/v/dweepbot" alt="PyPI Version"></a>
</p>

<p align="center">
  DweepBot Pro is a production-grade, open-source AI agent framework that gives you Claude/GPT‑4–level autonomy at DeepSeek prices. Batteries included. Extensible. Fun to hack on.
</p>

<p align="center">
  👉 Like this project? <a href="https://github.com/dweepbot/dweepbot">Star the repo</a> to support development!
</p>

## 🎥 Demo

![DweepBot Pro Demo]
🦈 DweepBot Pro working through a multi-step task: PLAN → ACT → OBSERVE → REFLECT. Writing code, running tools, fixing errors, and shipping.

## 💡 What Is DweepBot Pro?

DweepBot Pro is an autonomous AI agent framework built for real workloads, not toy demos.  
It combines:

- 🧭 A PLAN → ACT → OBSERVE → REFLECT loop for autonomous planning
- 💰 DeepSeek‑V3 for 50–60× lower LLM costs than GPT‑4/Claude agents
- 🧩 Batteries-included tools (web search, secure code exec, file ops, notifications)
- 🧠 Multi-level memory + RAG so it doesn’t forget what it just did
- 🎨 A simple, hackable architecture that fits in your head

Target users: agencies, indie hackers, and dev teams that want serious agents without serious cloud bills.

## ⚡ Quick Start

### 1. Requirements
- Python 3.10+
- macOS 10.15+, Linux, or WSL (Windows via WSL recommended)
- DeepSeek API key (free tier available)
- Optional deps: For full features, install `rich` (TUI), `duckduckgo-search` (web), `PyPDF2` & `python-docx` (docs), `chromadb` (RAG)

### 2. Install
```bash
# Clone the repo
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot

# Install with all features (RAG, web, docs)
pip install -e ".[all]"

# Or minimal core
pip install -e .
