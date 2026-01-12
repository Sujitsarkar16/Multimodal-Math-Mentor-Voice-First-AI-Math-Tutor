# 🧮 Multimodal Math Mentor - Voice-First AI Math Tutor

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![React](https://img.shields.io/badge/React-19.2+-61DAFB.svg)
![LangChain](https://img.shields.io/badge/LangChain-0.3+-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**An intelligent, multimodal math tutoring system powered by LangChain ReAct agents with voice, image, and text input support.**

[Demo](#demo) • [Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [API](#-api-endpoints)

</div>

---

## 📖 Overview

Multimodal Math Mentor is a sophisticated AI-powered math tutoring application that accepts problems through multiple input modes (voice, image, text) and provides step-by-step solutions with explanations. Built with a multi-agent architecture using LangChain, it features:

- **Voice-First Design**: Speak your math problems naturally
- **Image Recognition**: Upload handwritten or printed math problems
- **Human-in-the-Loop (HITL)**: Low-confidence results trigger human review
- **Self-Learning**: Learns from user feedback to improve over time
- **RAG-Enhanced**: Retrieval-Augmented Generation for accurate solutions

---

## ✨ Features

### 🎤 Multimodal Input
- **Text Input**: Type math problems directly
- **Voice Input**: Record audio using AssemblyAI transcription
- **Image Input**: Upload images with OCR powered by Gemini Vision

### 🤖 Multi-Agent Architecture
| Agent | Role |
|-------|------|
| **Parser** | Extracts mathematical expressions from natural language |
| **Input Verifier** | Validates and normalizes problem statements |
| **Router** | Classifies problem type (algebra, calculus, geometry, etc.) |
| **Solver** | LangChain ReAct agent with computational tools |
| **Verifier** | Validates solution correctness |
| **Explainer** | Generates step-by-step explanations |
| **Guardrail** | Ensures math-only content, blocks harmful inputs |

### 📚 Knowledge & Learning
- **RAG System**: Vector-based retrieval of mathematical concepts
- **Self-Learning**: Correct/incorrect feedback improves future responses
- **Knowledge Base**: Curated mathematical examples and formulas

### 🔄 Human-in-the-Loop
- Automatic flagging when confidence < 75%
- Review interface for OCR results
- Feedback loop for continuous improvement

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **npm** or **yarn**
- **API Keys**:
  - [Google AI (Gemini)](https://makersuite.google.com/app/apikey) - Required
  - [AssemblyAI](https://www.assemblyai.com/) - For voice input

### 📁 Project Structure

```
app/
├── frontend/                 # React + Vite frontend
│   ├── src/
│   │   ├── components/      # React components
│   │   ├── services/        # API service layer
│   │   └── context/         # React context providers
│   ├── package.json
│   └── vite.config.js
│
├── server/                   # FastAPI backend
│   ├── app/
│   │   ├── agents/          # Multi-agent system
│   │   ├── api/             # API endpoints
│   │   ├── llm/             # LLM clients (Gemini)
│   │   ├── multimodal/      # OCR & ASR processors
│   │   ├── rag/             # RAG knowledge retrieval
│   │   ├── memory/          # Self-learning memory
│   │   └── main.py          # FastAPI application
│   ├── requirements.txt
│   └── Dockerfile
│
└── README.md
```

---

## 🔧 Local Development Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/Sujitsarkar16/Multimodal-Math-Mentor-Voice-First-AI-Math-Tutor.git
cd Multimodal-Math-Mentor-Voice-First-AI-Math-Tutor/app
```

### Step 2: Backend Setup

```bash
# Navigate to server directory
cd server

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Create `.env` file in `server/` directory:

```env
# Required - Get from https://makersuite.google.com/app/apikey
GEMINI_API_KEY=your_gemini_api_key_here

# Optional - For voice input (https://www.assemblyai.com/)
ASSEMBLYAI_API_KEY=your_assemblyai_api_key_here

# Optional - OpenAI fallback
OPENAI_API_KEY=your_openai_api_key_here

# Application Settings
ENVIRONMENT=development
LOG_LEVEL=INFO
```

#### Start the Backend Server:

```bash
# From the server/ directory
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### Step 3: Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install dependencies
npm install
```

#### Create `.env` file in `frontend/` directory (for local development):

```env
# For local development - point to local backend
VITE_API_URL=http://localhost:8000
```

> ⚠️ **Important**: For local development, make sure `VITE_API_URL` points to `http://localhost:8000` (without `/api/v1` - it's added automatically by the API service).

#### Start the Frontend Dev Server:

```bash
npm run dev
```

The frontend will be available at: `http://localhost:5173`

---

## 🔀 Configuration Reference

### Backend Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GEMINI_API_KEY` | ✅ Yes | - | Google AI Gemini API key |
| `ASSEMBLYAI_API_KEY` | For voice | - | AssemblyAI API key for speech-to-text |
| `OPENAI_API_KEY` | No | - | OpenAI API key (fallback) |
| `ENVIRONMENT` | No | `development` | `development` or `production` |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `DEFAULT_LLM_MODEL` | No | `gemini-2.0-flash-exp` | LLM model to use |
| `DEFAULT_TEMPERATURE` | No | `0.2` | LLM temperature |
| `ENABLE_GUARDRAILS` | No | `true` | Enable content guardrails |

### Frontend Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `VITE_API_URL` | Yes | Backend API URL (without `/api/v1`) |

### Switching Between Local and Production

**For Local Development:**
```env
# frontend/.env
VITE_API_URL=http://localhost:8000
```

**For Production (Vercel + Railway):**
```env
# Set in Vercel dashboard
VITE_API_URL=https://your-railway-backend.up.railway.app
```

---

## 🌐 API Endpoints

### Base URL: `/api/v1`

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/ingest` | Process text/image/audio input |
| `POST` | `/solve/stream` | Solve problem with streaming SSE |
| `POST` | `/solve/async` | Solve problem asynchronously |
| `GET` | `/solve/health` | Pipeline health check |
| `GET` | `/solve/stats` | Pipeline statistics |
| `POST` | `/feedback/correct` | Mark solution as correct |
| `POST` | `/feedback/incorrect` | Mark solution as incorrect |
| `GET` | `/feedback/history` | Get solution history |
| `GET` | `/knowledge` | Get knowledge base entries |
| `POST` | `/knowledge` | Create knowledge entry |

### Example: Solve a Problem

```bash
curl -X POST "http://localhost:8000/api/v1/solve/async" \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the derivative of x^2 + 3x?", "enable_guardrails": true}'
```

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        FRONTEND (React + Vite)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐│
│  │  Voice   │  │  Image   │  │   Text   │  │   Workspace      ││
│  │  Input   │  │  Upload  │  │  Input   │  │   (Solutions)    ││
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘│
│       └─────────────┴─────────────┴─────────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │ API Calls
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     BACKEND (FastAPI)                           │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    INGEST LAYER                          │  │
│  │   ┌─────────┐   ┌─────────┐   ┌─────────────────────┐   │  │
│  │   │   OCR   │   │   ASR   │   │   Text Processing   │   │  │
│  │   │ (Gemini)│   │(Assembly│   │                     │   │  │
│  │   │         │   │   AI)   │   │                     │   │  │
│  │   └────┬────┘   └────┬────┘   └──────────┬──────────┘   │  │
│  └────────┴─────────────┴───────────────────┴──────────────┘  │
│                              │                                  │
│  ┌──────────────────────────▼───────────────────────────────┐  │
│  │                  MULTI-AGENT PIPELINE                     │  │
│  │                                                           │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐              │  │
│  │  │ Guardrail│──▶│  Parser  │──▶│  Router  │              │  │
│  │  └──────────┘   └──────────┘   └────┬─────┘              │  │
│  │                                      │                    │  │
│  │       ┌──────────────────────────────┘                   │  │
│  │       ▼                                                   │  │
│  │  ┌──────────┐   ┌──────────┐   ┌──────────┐              │  │
│  │  │  Solver  │──▶│ Verifier │──▶│ Explainer│              │  │
│  │  │ (LangChain   └──────────┘   └──────────┘              │  │
│  │  │  ReAct)  │                                             │  │
│  │  └──────────┘                                             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                  │
│  ┌───────────────────────────▼───────────────────────────────┐  │
│  │                   SUPPORT SYSTEMS                         │  │
│  │   ┌─────────────┐   ┌─────────────┐   ┌──────────────┐   │  │
│  │   │     RAG     │   │   Memory    │   │    HITL      │   │  │
│  │   │ (Knowledge) │   │(Self-Learn) │   │   (Review)   │   │  │
│  │   └─────────────┘   └─────────────┘   └──────────────┘   │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🚢 Deployment

### Backend on Railway

1. Create a new project on [Railway](https://railway.app)
2. Connect your GitHub repository
3. Set root directory to `server/`
4. Add environment variables:
   - `GEMINI_API_KEY`
   - `ASSEMBLYAI_API_KEY` (optional)
   - `ENVIRONMENT=production`
5. Railway will auto-detect the Dockerfile and deploy

### Frontend on Vercel

1. Import project on [Vercel](https://vercel.com)
2. Set root directory to `frontend/`
3. Add environment variable:
   - `VITE_API_URL` = Your Railway backend URL
4. Deploy

---

## 🧪 Testing

### Backend Tests

```bash
cd server
pytest -v
```

### API Health Check

```bash
curl http://localhost:8000/health
# Response: {"status": "healthy", "version": "2.0.0"}
```

---

## 📊 Key Technologies

| Component | Technology |
|-----------|------------|
| **Frontend** | React 19, Vite 7, TailwindCSS 4 |
| **Backend** | FastAPI, Python 3.11, Uvicorn |
| **AI/ML** | LangChain 0.3, LangGraph, Gemini 2.0 |
| **Vector Store** | FAISS (in-memory) |
| **Speech-to-Text** | AssemblyAI |
| **OCR** | Gemini Vision |

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit changes: `git commit -m 'Add amazing feature'`
4. Push to branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- [LangChain](https://www.langchain.com/) for the agent framework
- [Google AI](https://ai.google.dev/) for Gemini models
- [AssemblyAI](https://www.assemblyai.com/) for speech-to-text
- [FastAPI](https://fastapi.tiangolo.com/) for the backend framework

---

<div align="center">

**Built with ❤️ for the AI Planet Challenge**

[⬆ Back to Top](#-multimodal-math-mentor---voice-first-ai-math-tutor)

</div>
