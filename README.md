# Municipal Corporation Multi-Agent System

A 3-agent pipeline for municipal project management using the OpenAI Agents SDK.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    MUNICIPAL MULTI-AGENT PIPELINE                   │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐             │
│  │   AGENT 1   │    │   AGENT 2   │    │   AGENT 3   │             │
│  │  Formation  │───▶│ Governance  │───▶│ Scheduling  │             │
│  └─────────────┘    └─────────────┘    └─────────────┘             │
│        │                  │                  │                      │
│        ▼                  ▼                  ▼                      │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │                    SQLite Database                         │     │
│  │  issues │ signals │ candidates │ decisions │ schedule     │     │
│  └───────────────────────────────────────────────────────────┘     │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Agent Responsibilities

| Agent | Role | Input | Output |
|-------|------|-------|--------|
| **Formation** | Project scoping | Open issues | Project candidates with cost/time estimates |
| **Governance** | Budget allocation | Candidates + Budget | Approved/rejected decisions |
| **Scheduling** | Resource planning | Approved projects | Execution schedule |

## Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set OpenAI API key
export OPENAI_API_KEY='your-api-key-here'
```

## Quick Start

```bash
# Initialize database with sample data
python run_pipeline.py --init

# Run the complete pipeline
python run_pipeline.py
```

## Frontend

A simple React + Vite single-page app lives in `frontend/` and provides a dashboard, agents list, and pipeline views.

Quick start (development):

```bash
# Start backend
uvicorn backend.app.main:app --reload --port 8000

# In another terminal, start frontend
cd frontend
npm install
npm run dev
```

---

## Project Structure

```
city_gov/
├── municipal_agents/
│   ├── __init__.py          # Package exports
│   ├── database.py          # Schema & data seeding
│   ├── models.py            # Pydantic models for agent outputs
│   ├── context.py           # Shared MunicipalContext
│   ├── formation_agent.py   # Agent 1: Issue → Project
│   ├── governance_agent.py  # Agent 2: Budget allocation
│   ├── scheduling_agent.py  # Agent 3: Resource scheduling
│   └── pipeline.py          # Orchestration
├── database/
│   └── city_risk.db         # SQLite database (auto-created)
├── run_pipeline.py          # Main entry point
├── requirements.txt
└── README.md
```

## Database Schema

| Table | Purpose |
|-------|---------|
| `issues` | Raw citizen complaints/demands |
| `issue_signals` | Risk metrics (population, safety, legal) |
| `project_candidates` | Formation Agent output |
| `portfolio_decisions` | Governance Agent output |
| `resource_calendar` | Weekly resource capacity |
| `schedule_tasks` | Scheduling Agent output |
| `audit_log` | Governance trail |

## Usage Examples

### Run Full Pipeline
```python
from municipal_agents import MunicipalContext, run_municipal_pipeline
import asyncio

context = MunicipalContext(quarterly_budget=50_000_000)
results = asyncio.run(run_municipal_pipeline(context))
```

### Run Single Stage
```python
from municipal_agents.pipeline import run_interactive_stage

# Just run Formation Agent
await run_interactive_stage("formation")

# Run Governance with custom prompt
await run_interactive_stage(
    "governance",
    custom_prompt="Approve only legal mandate projects"
)
```

### Custom Context
```python
context = MunicipalContext(
    db_path="my_city.db",
    city_name="Springfield",
    quarterly_budget=25_000_000,
    planning_horizon_weeks=8
)
```

## Configuration

Edit `municipal_agents/database.py` to customize:

```python
CITY_PROFILE = {
    "city_name": "Metroville",
    "population": 2_500_000,
    "quarterly_budget": 75_000_000,
}

RISK_THRESHOLDS = {
    "high_population": 100_000,
    "high_complaints": 75,
    "high_risk_score": 3,
}

RISK_WEIGHTS = {
    "safety_risk": 3,
    "legal_mandate": 3,
    "population_impact": 1,
    "complaint_volume": 1,
}
```

## Optimization Algorithms

### Governance Agent (Budget Allocation)
Currently uses a **greedy knapsack** algorithm:
1. Include legal mandate projects first
2. Sort by risk-per-dollar (value density)
3. Greedily add until budget exhausted

To upgrade to MILP: uncomment `pulp` in requirements.txt and modify `run_knapsack_optimization()`.

### Scheduling Agent (Resource Scheduling)
Currently uses a **greedy scheduler**:
1. Sort projects by priority
2. Find earliest feasible start for each
3. Allocate resources

To upgrade to CP-SAT: uncomment `ortools` in requirements.txt and implement with `cp_model.CpModel()`.

## Sample Data

The system includes 7 sample issues:

| Issue | Category | Risk | Urgency |
|-------|----------|------|---------|
| Water Pipeline Rupture | Water | HIGH | 7 days |
| Hospital Power Backup | Health | HIGH | 14 days |
| Urban Flooding | Disaster Mgmt | HIGH | 30 days |
| Pothole Complaints | Infrastructure | MEDIUM | 60 days |
| Park Renovation | Recreation | LOW | 180 days |
| Street Light Outages | Infrastructure | MEDIUM | 45 days |
| School Zone Safety | Education | MEDIUM | 30 days |

## Extending the System

### Add New Agent Tools

```python
from agents import function_tool, RunContextWrapper

@function_tool
def my_custom_tool(
    ctx: RunContextWrapper["MunicipalContext"],
    param1: str
) -> str:
    """Tool description for the LLM."""
    # Access database via ctx.context.query()
    return "Result"
```

### Add New Issue Categories

1. Update `CREW_MAPPING` in `database.py`
2. Add resource capacity in `seed_sample_data()`

## License

MIT License - For educational use.

## Team

- Your team members here
