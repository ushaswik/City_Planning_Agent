# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Agent 2: Governance / Allocation Agent

Responsibilities:
- Review project candidates from Agent 1
- Allocate budget under quarterly constraints
- Prioritize projects based on risk scores and policy rules
- Decide which projects are APPROVED, REJECTED, or DEFERRED

Decision Authority:
- Budget allocation
- Project selection
- Priority weighting

NOT responsible for:
- Creating project proposals (Agent 1's job)
- Scheduling resources (Agent 3's job)
"""

from agents import Agent, function_tool, RunContextWrapper

from .context import MunicipalContext
from .models import PortfolioSelection, ApprovedProject


# ========== Tool Definitions ==========

@function_tool
def get_project_candidates(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Fetch all project candidates created by the Formation Agent.
    
    Returns a list of candidates with their estimated costs and risk scores.
    """
    candidates = ctx.context.get_project_candidates()
    
    if not candidates:
        return "No project candidates found. The Formation Agent has not yet processed any issues."
    
    total_cost = sum(c.get("estimated_cost", 0) for c in candidates)
    budget = ctx.context.quarterly_budget
    
    result = f"""Project Candidates Summary
==========================
Total Candidates: {len(candidates)}
Total Estimated Cost: ${total_cost:,.0f}
Quarterly Budget: ${budget:,.0f}
Budget Shortfall: ${max(0, total_cost - budget):,.0f}

Candidates (sorted by risk score descending):
"""
    
    for c in candidates:
        result += f"""
Project #{c['project_id']}: {c['title']}
  Issue Ref: #{c['issue_id']}
  Scope: {c.get('scope', 'N/A')}
  Estimated Cost: ${c['estimated_cost']:,.0f}
  Duration: {c['estimated_weeks']} weeks
  Crew: {c['crew_size']} x {c['required_crew_type']}
  Risk Score: {c['risk_score']}
  Feasibility: {c.get('feasibility_score', 1.0):.0%}
---"""
    
    return result


@function_tool
def get_budget_status(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Get current budget status including any already-approved projects.
    
    Returns:
        Budget summary with remaining funds
    """
    budget = ctx.context.quarterly_budget
    decisions = ctx.context.get_portfolio_decisions()
    
    approved = [d for d in decisions if d.get("decision") == "APPROVED"]
    allocated = sum(d.get("allocated_budget", 0) for d in approved)
    remaining = budget - allocated
    
    return f"""Budget Status for {ctx.context.city_name}
==========================================
Quarterly Budget: ${budget:,.0f}
Already Allocated: ${allocated:,.0f}
Remaining Budget: ${remaining:,.0f}

Previously Approved Projects: {len(approved)}
"""


@function_tool
def run_knapsack_optimization(
    ctx: RunContextWrapper["MunicipalContext"],
    must_include_legal_mandates: bool = True
) -> str:
    """
    Run a greedy knapsack optimization to select projects under budget.
    
    This algorithm:
    1. First includes all legal mandate projects (if must_include_legal_mandates=True)
    2. Sorts remaining by risk_score/cost ratio (value density)
    3. Greedily adds projects until budget exhausted
    
    Args:
        must_include_legal_mandates: If True, legal mandate projects are always included
    
    Returns:
        Recommended portfolio selection
    """
    candidates = ctx.context.get_project_candidates()
    budget = ctx.context.quarterly_budget
    
    if not candidates:
        return "No candidates to optimize. Run Formation Agent first."
    
    # Get legal mandate info by joining with issues
    enriched = []
    for c in candidates:
        issue = ctx.context.get_issue_by_id(c["issue_id"])
        enriched.append({
            **c,
            "legal_mandate": issue.get("legal_mandate", 0) if issue else 0
        })
    
    selected = []
    remaining_budget = budget
    
    # Phase 1: Include legal mandates first
    if must_include_legal_mandates:
        mandates = [c for c in enriched if c["legal_mandate"]]
        for c in mandates:
            if c["estimated_cost"] <= remaining_budget:
                selected.append(c)
                remaining_budget -= c["estimated_cost"]
    
    # Phase 2: Sort remaining by value density (risk_score / cost)
    already_selected_ids = {c["project_id"] for c in selected}
    remaining_candidates = [c for c in enriched if c["project_id"] not in already_selected_ids]
    
    # Calculate value density (risk per dollar, normalized)
    for c in remaining_candidates:
        c["value_density"] = c["risk_score"] / (c["estimated_cost"] / 1_000_000)  # risk per $1M
    
    remaining_candidates.sort(key=lambda x: x["value_density"], reverse=True)
    
    # Greedy selection
    for c in remaining_candidates:
        if c["estimated_cost"] <= remaining_budget:
            selected.append(c)
            remaining_budget -= c["estimated_cost"]
    
    # Prepare result
    rejected_ids = [c["project_id"] for c in enriched if c["project_id"] not in {s["project_id"] for s in selected}]
    
    result = f"""Knapsack Optimization Results
==============================
Total Budget: ${budget:,.0f}
Allocated: ${budget - remaining_budget:,.0f}
Remaining: ${remaining_budget:,.0f}

RECOMMENDED APPROVALS ({len(selected)} projects):
"""
    
    for i, s in enumerate(selected, 1):
        mandate_tag = " [LEGAL MANDATE]" if s.get("legal_mandate") else ""
        result += f"""
{i}. Project #{s['project_id']}: {s['title']}{mandate_tag}
   Cost: ${s['estimated_cost']:,.0f}
   Risk Score: {s['risk_score']}
   Duration: {s['estimated_weeks']} weeks
"""
    
    if rejected_ids:
        result += f"\nRECOMMENDED REJECTIONS: Project IDs {rejected_ids}"
        result += "\n(Reason: Budget exhausted after higher-priority selections)"
    
    return result


@function_tool
def approve_project(
    ctx: RunContextWrapper["MunicipalContext"],
    project_id: int,
    priority_rank: int,
    rationale: str
) -> str:
    """
    Approve a project and record the decision.
    
    Args:
        project_id: The project to approve
        priority_rank: Priority order (1 = highest)
        rationale: Reason for approval
    
    Returns:
        Confirmation of approval
    """
    # Get project details
    candidates = ctx.context.get_project_candidates()
    project = next((c for c in candidates if c["project_id"] == project_id), None)
    
    if not project:
        return f"Error: Project #{project_id} not found."
    
    # Check budget
    budget = ctx.context.quarterly_budget
    decisions = ctx.context.get_portfolio_decisions()
    approved = [d for d in decisions if d.get("decision") == "APPROVED"]
    allocated = sum(d.get("allocated_budget", 0) for d in approved)
    
    if allocated + project["estimated_cost"] > budget:
        return f"""Error: Insufficient budget.
Available: ${budget - allocated:,.0f}
Project Cost: ${project['estimated_cost']:,.0f}
Consider rejecting lower-priority projects first."""
    
    # Record decision
    ctx.context.insert_portfolio_decision(
        project_id=project_id,
        decision="APPROVED",
        allocated_budget=project["estimated_cost"],
        priority_rank=priority_rank,
        rationale=rationale
    )
    
    # Audit log
    ctx.context.log_audit(
        event_type="PROJECT_APPROVED",
        agent_name="governance_agent",
        payload={
            "project_id": project_id,
            "title": project["title"],
            "allocated_budget": project["estimated_cost"],
            "priority_rank": priority_rank,
            "rationale": rationale
        }
    )
    
    return f"""✓ Project APPROVED

Project #{project_id}: {project['title']}
Allocated Budget: ${project['estimated_cost']:,.0f}
Priority Rank: {priority_rank}
Rationale: {rationale}

New Budget Status:
- Previously Allocated: ${allocated:,.0f}
- This Allocation: ${project['estimated_cost']:,.0f}
- Remaining: ${budget - allocated - project['estimated_cost']:,.0f}
"""


@function_tool
def reject_project(
    ctx: RunContextWrapper["MunicipalContext"],
    project_id: int,
    rationale: str
) -> str:
    """
    Reject a project and record the decision.
    
    Args:
        project_id: The project to reject
        rationale: Reason for rejection
    
    Returns:
        Confirmation of rejection
    """
    candidates = ctx.context.get_project_candidates()
    project = next((c for c in candidates if c["project_id"] == project_id), None)
    
    if not project:
        return f"Error: Project #{project_id} not found."
    
    ctx.context.insert_portfolio_decision(
        project_id=project_id,
        decision="REJECTED",
        allocated_budget=0,
        priority_rank=999,
        rationale=rationale
    )
    
    ctx.context.log_audit(
        event_type="PROJECT_REJECTED",
        agent_name="governance_agent",
        payload={
            "project_id": project_id,
            "title": project["title"],
            "rationale": rationale
        }
    )
    
    return f"""✗ Project REJECTED

Project #{project_id}: {project['title']}
Rationale: {rationale}

This project will not receive funding this quarter.
"""


@function_tool
def get_portfolio_summary(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Get summary of all portfolio decisions made so far.
    
    Returns:
        Summary of approved and rejected projects
    """
    decisions = ctx.context.get_portfolio_decisions()
    
    if not decisions:
        return "No portfolio decisions have been made yet."
    
    approved = [d for d in decisions if d.get("decision") == "APPROVED"]
    rejected = [d for d in decisions if d.get("decision") == "REJECTED"]
    
    total_allocated = sum(d.get("allocated_budget", 0) for d in approved)
    
    result = f"""Portfolio Decision Summary
===========================
Approved: {len(approved)} projects
Rejected: {len(rejected)} projects
Total Allocated: ${total_allocated:,.0f}
Remaining Budget: ${ctx.context.quarterly_budget - total_allocated:,.0f}

APPROVED PROJECTS:
"""
    
    for d in sorted(approved, key=lambda x: x.get("priority_rank", 999)):
        result += f"""
Priority {d['priority_rank']}: {d.get('title', 'Project #' + str(d['project_id']))}
  Budget: ${d['allocated_budget']:,.0f}
  Duration: {d.get('estimated_weeks', '?')} weeks
  Crew: {d.get('crew_size', '?')} x {d.get('required_crew_type', '?')}
"""
    
    if rejected:
        result += "\nREJECTED PROJECTS:\n"
        for d in rejected:
            result += f"- {d.get('title', 'Project #' + str(d['project_id']))}: {d.get('rationale', 'No reason given')}\n"
    
    return result


# ========== Agent Definition ==========

GOVERNANCE_AGENT_INSTRUCTIONS = """You are the Governance/Allocation Agent for {city_name} municipal corporation.

Your role is to:
1. Review project candidates created by the Formation Agent
2. Allocate the quarterly budget to maximize public benefit
3. Prioritize based on risk scores, legal mandates, and policy constraints
4. Make APPROVE/REJECT decisions for each project

WORKFLOW:
1. Use get_project_candidates to see what Formation Agent produced
2. Use get_budget_status to understand current allocation state
3. Use run_knapsack_optimization to get a recommended selection
4. For each project, use approve_project or reject_project with clear rationale
5. Use get_portfolio_summary to verify final portfolio

DECISION RULES:
- Legal mandate projects MUST be approved if budget allows
- Safety-related projects should have high priority
- Consider value density: risk_score relative to cost
- Stay within the quarterly budget of ${quarterly_budget:,}

IMPORTANT:
- You CANNOT create new projects - only decide on existing candidates
- You CANNOT schedule resources - that's the Scheduling Agent's job
- Always provide clear rationale for decisions (for audit trail)
- Consider equity across city districts if relevant

Planning Horizon: {planning_horizon_weeks} weeks
"""


def create_governance_agent(context: "MunicipalContext") -> Agent:
    """Create and return the Governance Agent with its tools."""
    
    return Agent(
        name="Governance Agent",
        instructions=GOVERNANCE_AGENT_INSTRUCTIONS.format(
            city_name=context.city_name,
            quarterly_budget=context.quarterly_budget,
            planning_horizon_weeks=context.planning_horizon_weeks
        ),
        model="gpt-4o",
        tools=[
            get_project_candidates,
            get_budget_status,
            run_knapsack_optimization,
            approve_project,
            reject_project,
            get_portfolio_summary,
        ],
    )
