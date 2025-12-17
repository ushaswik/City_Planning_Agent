# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Agent 1: Project Formation Agent

Responsibilities:
- Fetch open issues from the database
- Calculate risk scores
- Generate cost/time/resource estimates
- Create project candidates for high-risk issues

NOT responsible for:
- Choosing which projects get funded
- Managing budget constraints
- Scheduling resources
"""

from agents import Agent, function_tool, RunContextWrapper

from .context import MunicipalContext
from .models import ProjectCandidate, ProjectCandidateList


# ========== Tool Definitions ==========

@function_tool
def get_open_issues(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Fetch all open citizen issues from the database with their signals.
    
    Returns a formatted list of issues with:
    - issue_id, title, category
    - population_affected, complaint_count
    - safety_risk (0/1), legal_mandate (0/1)
    - estimated_cost, urgency_days
    """
    issues = ctx.context.get_open_issues()
    
    if not issues:
        return "No open issues found in the database."
    
    result = f"Found {len(issues)} open issues:\n\n"
    for issue in issues:
        result += f"""Issue #{issue['issue_id']}: {issue['title']}
  Category: {issue['category']}
  Description: {issue.get('description', 'N/A')}
  Population Affected: {issue.get('population_affected', 0):,}
  Complaint Count: {issue.get('complaint_count', 0)}
  Safety Risk: {'YES' if issue.get('safety_risk') else 'NO'}
  Legal Mandate: {'YES' if issue.get('legal_mandate') else 'NO'}
  Estimated Cost: ${issue.get('estimated_cost', 0):,}
  Urgency: {issue.get('urgency_days', 90)} days
---
"""
    return result


@function_tool
def calculate_risk_score(
    ctx: RunContextWrapper["MunicipalContext"],
    issue_id: int
) -> str:
    """
    Calculate the risk score for a specific issue.
    
    Args:
        issue_id: The ID of the issue to assess
    
    Returns:
        Risk score and breakdown of factors
    """
    issue = ctx.context.get_issue_by_id(issue_id)
    
    if not issue:
        return f"Issue #{issue_id} not found."
    
    score = ctx.context.compute_risk_score(issue)
    thresholds = ctx.context.risk_thresholds
    
    breakdown = f"""Risk Assessment for Issue #{issue_id}: {issue['title']}

Risk Score: {score} (threshold for high-risk: {thresholds['high_risk_score']})

Factor Breakdown:
- Safety Risk: {'3 points (YES)' if issue.get('safety_risk') else '0 points (NO)'}
- Legal Mandate: {'3 points (YES)' if issue.get('legal_mandate') else '0 points (NO)'}
- Population Impact: {'1 point (>100K affected)' if issue.get('population_affected', 0) >= thresholds['high_population'] else '0 points (<100K)'}
- Complaint Volume: {'1 point (>75 complaints)' if issue.get('complaint_count', 0) >= thresholds['high_complaints'] else '0 points (<75)'}

Classification: {'HIGH RISK - Should create project candidate' if score >= thresholds['high_risk_score'] else 'LOW RISK - May defer'}
"""
    return breakdown


@function_tool
def estimate_project_resources(
    ctx: RunContextWrapper["MunicipalContext"],
    issue_id: int,
    category: str,
    estimated_cost: float
) -> str:
    """
    Generate resource estimates for a project based on category and cost.
    
    Args:
        issue_id: The issue ID this project addresses
        category: Issue category (Water, Health, Infrastructure, etc.)
        estimated_cost: Rough cost estimate from signals
    
    Returns:
        Estimated duration, crew type, and crew size
    """
    # Estimation heuristics (in a real system, this would be more sophisticated)
    crew_type = ctx.context.get_crew_type(category)
    
    # Duration estimation based on cost tiers
    if estimated_cost >= 50_000_000:
        weeks = 8
        crew_size = 3
    elif estimated_cost >= 10_000_000:
        weeks = 4
        crew_size = 2
    elif estimated_cost >= 1_000_000:
        weeks = 2
        crew_size = 2
    else:
        weeks = 1
        crew_size = 1
    
    return f"""Resource Estimates for Issue #{issue_id}:

Category: {category}
Required Crew Type: {crew_type}
Estimated Duration: {weeks} weeks
Crew Size Needed: {crew_size} units
Estimated Cost: ${estimated_cost:,.0f}

Note: These are heuristic estimates. Actual requirements may vary.
"""


@function_tool
def create_project_candidate(
    ctx: RunContextWrapper["MunicipalContext"],
    issue_id: int,
    title: str,
    scope: str,
    estimated_cost: float,
    estimated_weeks: int,
    required_crew_type: str,
    crew_size: int,
    risk_score: float,
    feasibility_score: float = 1.0
) -> str:
    """
    Create a new project candidate in the database.
    
    Args:
        issue_id: Reference to the original issue
        title: Project title
        scope: Brief scope description
        estimated_cost: Estimated cost in USD
        estimated_weeks: Estimated duration in weeks
        required_crew_type: Type of crew needed (water_crew, electrical_crew, etc.)
        crew_size: Number of crew units needed
        risk_score: Computed risk score
        feasibility_score: Feasibility rating 0-1 (default 1.0)
    
    Returns:
        Confirmation with the new project_id
    """
    project_id = ctx.context.insert_project_candidate(
        issue_id=issue_id,
        title=title,
        scope=scope,
        estimated_cost=estimated_cost,
        estimated_weeks=estimated_weeks,
        required_crew_type=required_crew_type,
        crew_size=crew_size,
        risk_score=risk_score,
        feasibility_score=feasibility_score
    )
    
    # Log to audit trail
    ctx.context.log_audit(
        event_type="PROJECT_CANDIDATE_CREATED",
        agent_name="formation_agent",
        payload={
            "project_id": project_id,
            "issue_id": issue_id,
            "title": title,
            "estimated_cost": estimated_cost,
            "risk_score": risk_score
        }
    )
    
    return f"""✓ Project Candidate Created Successfully

Project ID: {project_id}
Title: {title}
Issue Reference: #{issue_id}
Estimated Cost: ${estimated_cost:,.0f}
Duration: {estimated_weeks} weeks
Crew: {crew_size} x {required_crew_type}
Risk Score: {risk_score}
Feasibility: {feasibility_score:.0%}

This project candidate will be reviewed by the Governance Agent for budget allocation.
"""


@function_tool
def get_risk_thresholds(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Get the current risk thresholds and weights used for assessment.
    
    Returns:
        Current risk configuration
    """
    thresholds = ctx.context.risk_thresholds
    weights = ctx.context.risk_weights
    
    return f"""Risk Configuration for {ctx.context.city_name}:

THRESHOLDS:
- High Population Impact: {thresholds['high_population']:,} people
- High Complaint Volume: {thresholds['high_complaints']} complaints
- High Risk Score: {thresholds['high_risk_score']} points

WEIGHTS (points added to risk score):
- Safety Risk: {weights['safety_risk']} points
- Legal Mandate: {weights['legal_mandate']} points
- Population Impact: {weights['population_impact']} point(s)
- Complaint Volume: {weights['complaint_volume']} point(s)

An issue with risk_score >= {thresholds['high_risk_score']} should become a project candidate.
"""


# ========== Agent Definition ==========

FORMATION_AGENT_INSTRUCTIONS = """You are the Project Formation Agent for {city_name} municipal corporation.

Your role is to:
1. Analyze open citizen issues and their impact signals
2. Calculate risk scores based on safety, legal, population, and complaint factors
3. Generate cost/time/resource estimates for high-risk issues
4. Create structured project candidates for issues that warrant action

WORKFLOW:
1. First, use get_open_issues to see all pending citizen demands
2. For each issue, use calculate_risk_score to assess priority
3. For HIGH RISK issues (score >= 3), use estimate_project_resources to get estimates
4. Create project candidates using create_project_candidate

IMPORTANT RULES:
- Only create project candidates for HIGH RISK issues (risk_score >= 3)
- You do NOT decide which projects get funded - that's the Governance Agent's job
- You do NOT schedule resources - that's the Scheduling Agent's job
- Be conservative with feasibility scores if there are concerns
- Always include clear scope descriptions

Available crew types: water_crew, electrical_crew, construction_crew, general_crew

Current quarterly budget for context: ${quarterly_budget:,} (but you don't allocate this)
"""


def create_formation_agent(context: "MunicipalContext") -> Agent:
    """Create and return the Formation Agent with its tools."""
    
    return Agent(
        name="Project Formation Agent",
        instructions=FORMATION_AGENT_INSTRUCTIONS.format(
            city_name=context.city_name,
            quarterly_budget=context.quarterly_budget
        ),
        model="gpt-4o",
        tools=[
            get_open_issues,
            calculate_risk_score,
            estimate_project_resources,
            create_project_candidate,
            get_risk_thresholds,
        ],
        # output_type=ProjectCandidateList,  # Enable for structured output
    )
