# -*- coding: utf-8 -*-
"""
Validation and safety checks for the multi-agent system.
Prevents common failure modes and ensures data integrity.
"""

from typing import Optional, List, Dict
from municipal_agents.context import MunicipalContext


class ValidationError(Exception):
    """Custom exception for validation errors."""
    pass


def validate_budget_allocation(context: MunicipalContext) -> List[str]:
    """
    Validate that budget allocations are within constraints.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    budget = context.quarterly_budget
    decisions = context.get_portfolio_decisions()
    approved = [d for d in decisions if d.get("decision") == "APPROVED"]
    
    total_allocated = sum(d.get("allocated_budget", 0) for d in approved)
    
    # Check 1: Total allocation doesn't exceed budget
    if total_allocated > budget:
        errors.append(
            f"Budget violation: Total allocated ${total_allocated:,.0f} "
            f"exceeds budget ${budget:,.0f} by ${total_allocated - budget:,.0f}"
        )
    
    # Check 2: No negative allocations
    for decision in approved:
        if decision.get("allocated_budget", 0) < 0:
            errors.append(
                f"Invalid allocation: Project #{decision['project_id']} "
                f"has negative budget ${decision['allocated_budget']:,.0f}"
            )
    
    # Check 3: All approved projects have valid priority ranks
    for decision in approved:
        priority = decision.get("priority_rank")
        if priority is None or priority < 1:
            errors.append(
                f"Invalid priority: Project #{decision['project_id']} "
                f"has invalid priority rank {priority}"
            )
    
    return errors


def validate_schedule_feasibility(context: MunicipalContext) -> List[str]:
    """
    Validate that schedule respects resource constraints.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    tasks = context.get_schedule_tasks()
    projects = context.get_approved_projects()
    
    # Create project lookup
    project_lookup = {p["project_id"]: p for p in projects}
    
    # Check each scheduled task
    for task in tasks:
        project_id = task["project_id"]
        project = project_lookup.get(project_id)
        
        if not project:
            errors.append(f"Orphaned task: Task references non-existent project #{project_id}")
            continue
        
        start_week = task.get("start_week")
        end_week = task.get("end_week")
        resource_type = task.get("resource_type")
        crew_assigned = task.get("crew_assigned", 0)
        
        # Check 1: Valid week range
        if start_week is None or end_week is None:
            errors.append(f"Invalid schedule: Project #{project_id} has missing start/end weeks")
            continue
        
        if start_week < 1 or end_week < start_week:
            errors.append(
                f"Invalid schedule: Project #{project_id} has invalid week range "
                f"({start_week}-{end_week})"
            )
        
        # Check 2: Duration matches estimated weeks
        actual_duration = end_week - start_week + 1
        estimated_duration = project.get("estimated_weeks", 0)
        if actual_duration != estimated_duration:
            errors.append(
                f"Duration mismatch: Project #{project_id} scheduled for {actual_duration} weeks "
                f"but estimated {estimated_duration} weeks"
            )
        
        # Check 3: Resource capacity constraints
        for week in range(start_week, end_week + 1):
            available = context.get_available_capacity(resource_type, week)
            if available < crew_assigned:
                errors.append(
                    f"Resource violation: Project #{project_id} needs {crew_assigned} "
                    f"{resource_type} in week {week}, but only {available} available"
                )
    
    return errors


def validate_project_candidates(context: MunicipalContext) -> List[str]:
    """
    Validate project candidates have required fields and reasonable values.
    
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    candidates = context.get_project_candidates()
    
    for candidate in candidates:
        project_id = candidate.get("project_id")
        
        # Check 1: Required fields
        required_fields = ["title", "estimated_cost", "estimated_weeks", "risk_score"]
        for field in required_fields:
            if field not in candidate or candidate[field] is None:
                errors.append(
                    f"Missing field: Project #{project_id} missing required field '{field}'"
                )
        
        # Check 2: Reasonable cost (not negative, not absurdly high)
        cost = candidate.get("estimated_cost", 0)
        if cost < 0:
            errors.append(f"Invalid cost: Project #{project_id} has negative cost ${cost:,.0f}")
        if cost > context.quarterly_budget * 10:  # More than 10x budget is suspicious
            errors.append(
                f"Suspicious cost: Project #{project_id} cost ${cost:,.0f} "
                f"exceeds 10x quarterly budget"
            )
        
        # Check 3: Reasonable duration
        weeks = candidate.get("estimated_weeks", 0)
        if weeks < 1:
            errors.append(f"Invalid duration: Project #{project_id} has duration {weeks} weeks")
        if weeks > context.planning_horizon_weeks * 2:  # More than 2x horizon is suspicious
            errors.append(
                f"Suspicious duration: Project #{project_id} duration {weeks} weeks "
                f"exceeds 2x planning horizon"
            )
        
        # Check 4: Valid risk score
        risk_score = candidate.get("risk_score", -1)
        if risk_score < 0 or risk_score > 10:  # Allow some buffer beyond max 8
            errors.append(
                f"Invalid risk score: Project #{project_id} has risk score {risk_score} "
                f"(expected 0-8)"
            )
    
    return errors


def validate_complete_pipeline(context: MunicipalContext) -> Dict[str, List[str]]:
    """
    Run all validations and return comprehensive results.
    
    Returns:
        Dictionary with validation results for each stage
    """
    return {
        "project_candidates": validate_project_candidates(context),
        "budget_allocation": validate_budget_allocation(context),
        "schedule_feasibility": validate_schedule_feasibility(context),
    }


def has_critical_errors(validation_results: Dict[str, List[str]]) -> bool:
    """Check if there are any critical validation errors."""
    return any(len(errors) > 0 for errors in validation_results.values())


def format_validation_report(validation_results: Dict[str, List[str]]) -> str:
    """Format validation results as a readable report."""
    report = "Validation Report\n" + "=" * 60 + "\n\n"
    
    for stage, errors in validation_results.items():
        report += f"{stage.replace('_', ' ').title()}:\n"
        if errors:
            for error in errors:
                report += f"  ❌ {error}\n"
        else:
            report += "  ✅ No errors\n"
        report += "\n"
    
    return report

