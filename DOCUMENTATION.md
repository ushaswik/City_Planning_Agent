# Municipal Multi-Agent System: Complete Technical Documentation

## Overview

```
SYSTEM: Municipal Corporation Multi-Agent Pipeline
PURPOSE: Automate city infrastructure project management
ARCHITECTURE: 3-Agent Pipeline with SQLite shared state
FRAMEWORK: OpenAI Agents SDK (openai-agents)
```

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                 MUNICIPAL MULTI-AGENT SYSTEM                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐              │
│  │  AGENT 1  │ ─▶ │  AGENT 2  │ ─▶ │  AGENT 3  │              │
│  │ Formation │    │ Governance│    │ Scheduling│              │
│  └───────────┘    └───────────┘    └───────────┘              │
│       │                │                │                      │
│       ▼                ▼                ▼                      │
│  ┌───────────┐    ┌───────────┐    ┌───────────┐              │
│  │  Creates  │    │ Approves/ │    │  Assigns  │              │
│  │  Project  │    │  Rejects  │    │ Start/End │              │
│  │ Candidates│    │ Projects  │    │   Weeks   │              │
│  └───────────┘    └───────────┘    └───────────┘              │
│       │                │                │                      │
│       └────────────────┴────────────────┘                      │
│                        │                                       │
│                        ▼                                       │
│               ┌─────────────────┐                              │
│               │   SQLite DB     │                              │
│               │  (Shared State) │                              │
│               └─────────────────┘                              │
└─────────────────────────────────────────────────────────────────┘
```

## File Structure

```
city_gov/
├── municipal_agents/           # Main package
│   ├── __init__.py            # Exports
│   ├── database.py            # SQLite schema + seed data
│   ├── models.py              # Pydantic models
│   ├── context.py             # Shared context with DB helpers
│   ├── formation_agent.py     # Agent 1: Issue → Project
│   ├── governance_agent.py    # Agent 2: Budget allocation
│   ├── scheduling_agent.py    # Agent 3: Time scheduling
│   └── pipeline.py            # Orchestrates all 3 agents
├── run_pipeline.py            # Entry point
├── requirements.txt           # Dependencies
└── .gitignore                 # Excludes .env, venv, database
```

## Database Schema (7 Tables)

### Table 1: issues
```sql
CREATE TABLE issues (
    issue_id        INTEGER PRIMARY KEY,
    title           TEXT,
    category        TEXT,
    description     TEXT,
    source          TEXT,
    status          TEXT,
    created_at      TIMESTAMP
);
```

### Table 2: issue_signals
```sql
CREATE TABLE issue_signals (
    issue_id            INTEGER,
    population_affected INTEGER,
    complaint_count     INTEGER,
    safety_risk         INTEGER,
    legal_mandate       INTEGER,
    estimated_cost      REAL,
    urgency_days        INTEGER
);
```

### Table 3: project_candidates (Agent 1 output)
```sql
CREATE TABLE project_candidates (
    project_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    issue_id            INTEGER,
    title               TEXT,
    scope               TEXT,
    estimated_cost      REAL,
    estimated_weeks     INTEGER,
    required_crew_type  TEXT,
    crew_size           INTEGER,
    risk_score          REAL,
    feasibility_score   REAL,
    created_by          TEXT
);
```

### Table 4: portfolio_decisions (Agent 2 output)
```sql
CREATE TABLE portfolio_decisions (
    decision_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER,
    decision            TEXT,
    allocated_budget    REAL,
    priority_rank       INTEGER,
    rationale           TEXT,
    decided_by          TEXT
);
```

### Table 5: resource_calendar
```sql
CREATE TABLE resource_calendar (
    calendar_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    resource_type       TEXT,
    week_number         INTEGER,
    year                INTEGER,
    capacity            INTEGER,
    allocated           INTEGER DEFAULT 0
);
```

### Table 6: schedule_tasks (Agent 3 output)
```sql
CREATE TABLE schedule_tasks (
    task_id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id          INTEGER,
    start_week          INTEGER,
    end_week            INTEGER,
    resource_type       TEXT,
    crew_assigned       INTEGER,
    created_by          TEXT
);
```

### Table 7: audit_log
```sql
CREATE TABLE audit_log (
    log_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type          TEXT,
    agent_name          TEXT,
    payload             TEXT,
    timestamp           TIMESTAMP
);
```

---

## Agent 1: Formation Agent

**Purpose:** Convert raw issues into structured project candidates

**Input:** Raw issues from citizen complaints, sensors, inspections

**Output:** Structured project candidates with cost/time/resource estimates

### Tools

| Tool | Purpose |
|------|---------|
| get_open_issues | Fetch all OPEN issues with signals |
| calculate_risk_score | Compute priority score (0-8) |
| estimate_project_resources | Map category to crew type |
| create_project_candidate | Insert new candidate into DB |
| get_risk_thresholds | Return threshold configuration |

### Risk Score Calculation

```python
def compute_risk_score(signal: dict) -> float:
    score = 0.0
    if signal.get("safety_risk"):
        score += 3  # safety weight
    if signal.get("legal_mandate"):
        score += 3  # legal weight
    if signal.get("population_affected", 0) >= 100_000:
        score += 1  # population impact
    if signal.get("complaint_count", 0) >= 75:
        score += 1  # complaint volume
    return score  # Range: 0-8
```

**Threshold:** If score >= 3, issue becomes a project candidate

---

## Agent 2: Governance Agent

**Purpose:** Allocate limited budget across competing projects

**Input:** Project candidates + Budget constraint ($75M quarterly)

**Output:** Approved/Rejected decisions with allocated budgets

### Tools

| Tool | Purpose |
|------|---------|
| get_project_candidates | Fetch all candidates |
| get_budget_status | Check remaining budget |
| run_knapsack_optimization | Greedy selection algorithm |
| approve_project | Mark as APPROVED |
| reject_project | Mark as REJECTED |
| get_portfolio_summary | Summary of decisions |

### Decision Logic (Greedy Knapsack)

```python
candidates.sort(by=risk_score, descending=True)
remaining_budget = quarterly_budget

for project in candidates:
    if project.cost <= remaining_budget:
        approve_project(project)
        remaining_budget -= project.cost
    else:
        reject_project(project, "Insufficient budget")
```

---

## Agent 3: Scheduling Agent

**Purpose:** Assign start/end weeks respecting resource capacity

**Input:** Approved projects + Resource calendar

**Output:** Week-by-week schedule with crew assignments

### Tools

| Tool | Purpose |
|------|---------|
| get_approved_projects | Fetch APPROVED projects |
| get_resource_availability | Check crew capacity |
| run_greedy_scheduler | Sequential scheduling |
| check_schedule_feasibility | Validate constraints |
| save_schedule_to_db | Persist tasks |
| get_final_schedule | Return schedule |

### Decision Logic

```python
approved_projects.sort(by=priority_rank)

for project in approved_projects:
    for week in range(1, horizon + 1):
        if has_capacity(project.crew_type, week):
            schedule_project(project, start=week)
            break
```

---

## Pipeline Flow

```python
async def run_municipal_pipeline():
    context = MunicipalContext()
    
    # Agent 1: Formation
    await Runner.run(formation_agent, 
        input="Analyze issues and create candidates",
        context=context)
    
    # Agent 2: Governance  
    await Runner.run(governance_agent,
        input="Allocate budget",
        context=context)
    
    # Agent 3: Scheduling
    await Runner.run(scheduling_agent,
        input="Schedule approved projects",
        context=context)
```

---

## Example Execution

```
AGENT 1: FORMATION
├─ Input: 7 open issues
└─ Output: 5 project candidates

AGENT 2: GOVERNANCE
├─ Budget: $75,000,000
├─ Approved: 4 projects ($58.3M)
└─ Rejected: 1 project (exceeded budget)

AGENT 3: SCHEDULING
├─ Horizon: 12 weeks
└─ All 4 projects scheduled
```

---

## Configuration

```python
CITY_PROFILE = {
    "city_name": "Metroville",
    "population": 2_500_000,
    "quarterly_budget": 75_000_000
}

RISK_THRESHOLDS = {
    "high_population": 100_000,
    "high_complaints": 75,
    "high_risk_score": 3
}

RISK_WEIGHTS = {
    "safety_risk": 3,
    "legal_mandate": 3,
    "population_impact": 1,
    "complaint_volume": 1
}
```

---

## How to Run

```bash
cd city_gov
source venv/bin/activate
python run_pipeline.py
```

---

## LLM-Friendly Summary

```yaml
system_name: "Municipal Multi-Agent Pipeline"
framework: "OpenAI Agents SDK"
database: "SQLite"

agents:
  - name: "FormationAgent"
    role: "Convert issues into project candidates"
    
  - name: "GovernanceAgent"  
    role: "Budget allocation via greedy knapsack"
    
  - name: "SchedulingAgent"
    role: "Resource-constrained scheduling"

data_flow:
  1: "issues → FormationAgent → project_candidates"
  2: "project_candidates → GovernanceAgent → portfolio_decisions"  
  3: "portfolio_decisions → SchedulingAgent → schedule_tasks"
```
