# Multi-Agent Mathematical Problem Solver

## Overview

This is a production-grade multi-agent system for solving mathematical problems using LangChain and Google Gemini. The system implements a clean, modular architecture following industry best practices.

## Architecture

### Core Components

1. **Agent System** (`app/agents/`)
   - **BaseAgent**: Abstract base class implementing the Strategy pattern
   - **ParserAgent**: Converts raw text into structured problem representation
   - **IntentRouterAgent**: Classifies problem type and routes to appropriate strategy
   - **SolverAgent**: Solves problems using RAG, LLM, and computational tools
   - **VerifierAgent**: Validates solutions and triggers human-in-the-loop when needed
   - **ExplainerAgent**: Generates student-friendly explanations
   - **GuardrailAgent**: Enforces safety and content policies

2. **Orchestration** (`app/domain/`)
   - **AgentOrchestrator**: Coordinates multi-agent workflow
   - **Pipeline**: Clean interface for problem solving

3. **LLM Integration** (`app/llm/`)
   - **LLMClient**: LangChain-based wrapper for Gemini
   - Supports text, JSON, and batch generation

4. **RAG System** (`app/rag/`)
   - **RAGRetriever**: FAISS-based vector store for context retrieval
   - Supports similarity search with scoring

5. **Tools** (`app/agents/tools.py`)
   - **CalculatorTool**: Safe numerical computation
   - **SymbolicSolverTool**: Placeholder for symbolic math
   - **PlotterTool**: Placeholder for visualization

## Installation

### Prerequisites

- Python 3.10+
- Google Gemini API key

### Setup

1. **Install dependencies**:
   ```bash
   cd server
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   ```bash
   cp .env.example .env
   # Edit .env and add your GEMINI_API_KEY
   ```

3. **Run the server**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Usage

### Solve a Problem

```bash
POST /solve
Content-Type: application/json

{
  "text": "Solve for x: 2x + 5 = 15",
  "context": null,
  "enable_guardrails": true
}
```

**Response**:
```json
{
  "final_answer": "x = 5",
  "explanation": "Step-by-step explanation...",
  "confidence": 0.95,
  "requires_human_review": false,
  "agent_trace": [
    {
      "agent": "parser",
      "input": "Text: Solve for x: 2x + 5 = 15",
      "output": "Parsed: algebra",
      "time_ms": 234.5,
      "success": true
    },
    ...
  ],
  "metadata": {
    "problem_type": "linear_equation",
    "difficulty": "easy",
    "topic": "algebra"
  }
}
```

### Get Statistics

```bash
GET /solve/stats
```

### Health Check

```bash
GET /solve/health
```

## Key Features

### 🎯 Clean Code Practices

- **SOLID Principles**: Single Responsibility, Open/Closed, etc.
- **Design Patterns**: Strategy (agents), Singleton (shared resources)
- **Type Safety**: Pydantic models for all data structures
- **Error Handling**: Custom exception hierarchy
- **Logging**: Structured logging instead of print statements

### 🔄 Multi-Agent Workflow

1. **Guardrail Check**: Content safety validation
2. **Parsing**: Extract structured problem components
3. **Routing**: Classify and determine strategy
4. **Solving**: Use RAG + tools to solve
5. **Verification**: Validate correctness
6. **Explanation**: Generate student-friendly output

### 🛡️ Safety & Reliability

- Content policy enforcement
- Human-in-the-loop for uncertain cases
- Comprehensive error handling
- Execution tracing and monitoring

### 🧰 Tool Integration

- Extensible tool registry
- Safe calculator for numeric operations
- Placeholder for symbolic solvers (SymPy)
- Placeholder for plotting (matplotlib)

## Configuration

All configuration is centralized in `app/settings.py` using pydantic-settings:

- **LLM Settings**: Model, temperature, tokens
- **Agent Settings**: Guardrails, confidence thresholds
- **RAG Settings**: Embedding model, similarity thresholds
- **Logging**: Log level, trace logging

## Development

### Code Structure

```
app/
├── agents/          # Agent implementations
│   ├── base.py     # Base agent class
│   ├── models.py   # Pydantic models
│   ├── parser.py
│   ├── router.py
│   ├── solver.py
│   ├── verifier.py
│   ├── explainer.py
│   ├── guardrail.py
│   └── tools.py    # Tool implementations
├── api/            # FastAPI routers
│   └── solve.py
├── core/           # Core utilities
│   ├── logger.py
│   └── exceptions.py
├── domain/         # Business logic
│   ├── orchestrator.py
│   └── pipeline.py
├── llm/            # LLM integration
│   └── client.py
├── rag/            # RAG system
│   └── retriever.py
└── settings.py     # Configuration
```

### Adding New Agents

1. Extend `BaseAgent`
2. Define input/output models in `agents/models.py`
3. Implement `execute()` method
4. Register in orchestrator
5. Update pipeline flow

### Adding New Tools

1. Create tool class in `agents/tools.py`
2. Register in `ToolRegistry`
3. Update solver to use tool
4. Document in prompts

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app
```

## Performance

- **Singleton Pattern**: Shared LLM client and RAG retriever
- **Batch Operations**: Support for batch inference
- **Lazy Loading**: Components initialized on demand
- **Execution Tracing**: Monitor agent performance

## Future Enhancements

- [ ] Full SymPy integration for symbolic math
- [ ] Matplotlib integration for plotting
- [ ] Memory system for conversation context
- [ ] Advanced RAG with document chunking
- [ ] Multi-modal support (images, equations)
- [ ] Caching for repeated queries
- [ ] Async agent execution
- [ ] Enhanced tool calling with LangChain tools

## License

MIT License

## Support

For issues or questions, contact the development team.
