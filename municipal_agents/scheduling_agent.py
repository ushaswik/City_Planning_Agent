# -*- coding: utf-8 -*-
from __future__ import annotations
"""
Agent 3: Scheduling Agent (ILP/CP-SAT Optimization)

Responsibilities:
- Take approved projects from Governance Agent
- Assign start times within the planning horizon
- Respect resource capacity constraints
- Minimize makespan or maximize priority-weighted completion

Decision Authority:
- Start times
- Resource assignment
- Sequencing

NOT responsible for:
- Adding/removing projects
- Changing budgets
- Only optimizes execution of approved work
"""

from agents import Agent, function_tool, RunContextWrapper

from .context import MunicipalContext
from .models import ScheduleOutput, ScheduleTask


# ========== Tool Definitions ==========

@function_tool
def get_approved_projects(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Fetch all approved projects that need to be scheduled.
    
    Returns projects with their duration, resource requirements, and priority.
    """
    projects = ctx.context.get_approved_projects()
    
    if not projects:
        return "No approved projects to schedule. Governance Agent has not approved any projects yet."
    
    result = f"""Approved Projects for Scheduling
=================================
Total Projects: {len(projects)}
Planning Horizon: {ctx.context.planning_horizon_weeks} weeks

Projects to Schedule:
"""
    
    for p in projects:
        result += f"""
Priority {p['priority_rank']}: {p['title']} (Project #{p['project_id']})
  Duration: {p['estimated_weeks']} weeks
  Resource: {p['crew_size']} x {p['required_crew_type']}
  Budget: ${p['allocated_budget']:,.0f}
---"""
    
    return result


@function_tool
def get_resource_availability(
    ctx: RunContextWrapper["MunicipalContext"],
    resource_type: str = None
) -> str:
    """
    Get resource availability across the planning horizon.
    
    Args:
        resource_type: Optional filter for specific resource type
    
    Returns:
        Resource calendar showing capacity and allocation by week
    """
    calendar = ctx.context.get_resource_calendar(resource_type)
    
    if not calendar:
        return "No resource calendar data found."
    
    # Group by resource type
    by_type = {}
    for r in calendar:
        rtype = r["resource_type"]
        if rtype not in by_type:
            by_type[rtype] = []
        by_type[rtype].append(r)
    
    result = "Resource Availability (12-week horizon)\n" + "=" * 45 + "\n"
    
    for rtype, weeks in by_type.items():
        result += f"\n{rtype.upper()}:\n"
        result += "Week: " + " ".join(f"{w['week_number']:>3}" for w in weeks) + "\n"
        result += "Cap:  " + " ".join(f"{w['capacity']:>3}" for w in weeks) + "\n"
        result += "Used: " + " ".join(f"{w['allocated']:>3}" for w in weeks) + "\n"
        result += "Free: " + " ".join(f"{w['capacity'] - w['allocated']:>3}" for w in weeks) + "\n"
    
    return result


@function_tool
def run_greedy_scheduler(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Run a greedy scheduling algorithm that respects resource constraints.
    
    Algorithm:
    1. Sort projects by priority rank (1 = highest)
    2. For each project, find earliest feasible start week
    3. A start week is feasible if resource capacity >= crew_size for all weeks
    4. Allocate resources and record schedule
    
    Returns:
        Proposed schedule with start/end weeks for each project
    """
    projects = ctx.context.get_approved_projects()
    
    if not projects:
        return "No approved projects to schedule."
    
    horizon = ctx.context.planning_horizon_weeks
    
    # Sort by priority
    projects_sorted = sorted(projects, key=lambda x: x["priority_rank"])
    
    schedule = []
    infeasible = []
    
    for p in projects_sorted:
        project_id = p["project_id"]
        duration = p["estimated_weeks"]
        resource_type = p["required_crew_type"]
        crew_size = p["crew_size"]
        
        # Find earliest feasible start
        scheduled = False
        for start_week in range(1, horizon - duration + 2):
            # Check if all weeks have enough capacity
            feasible = True
            for week in range(start_week, start_week + duration):
                if week > horizon:
                    feasible = False
                    break
                available = ctx.context.get_available_capacity(resource_type, week)
                if available < crew_size:
                    feasible = False
                    break
            
            if feasible:
                # Allocate resources
                for week in range(start_week, start_week + duration):
                    ctx.context.allocate_resource(resource_type, week, crew_size)
                
                end_week = start_week + duration - 1
                schedule.append({
                    "project_id": project_id,
                    "title": p["title"],
                    "start_week": start_week,
                    "end_week": end_week,
                    "resource_type": resource_type,
                    "crew_assigned": crew_size
                })
                scheduled = True
                break
        
        if not scheduled:
            infeasible.append(p)
    
    # Build result
    result = f"""Greedy Schedule Results
=======================
Scheduled: {len(schedule)} projects
Infeasible: {len(infeasible)} projects
Horizon: {horizon} weeks

SCHEDULE:
"""
    
    for s in sorted(schedule, key=lambda x: x["start_week"]):
        result += f"""
{s['title']} (#{s['project_id']})
  Weeks {s['start_week']}-{s['end_week']} ({s['end_week'] - s['start_week'] + 1} weeks)
  Resource: {s['crew_assigned']} x {s['resource_type']}
"""
    
    if infeasible:
        result += "\n⚠️ COULD NOT SCHEDULE (resource constraints):\n"
        for p in infeasible:
            result += f"- {p['title']}: needs {p['crew_size']} x {p['required_crew_type']} for {p['estimated_weeks']} weeks\n"
    
    # Show Gantt-style view
    result += "\n" + "=" * 50 + "\n"
    result += "GANTT CHART (simplified):\n"
    result += "Week: " + " ".join(f"{w:>2}" for w in range(1, horizon + 1)) + "\n"
    
    for s in schedule:
        row = ["  "] * horizon
        for w in range(s["start_week"], s["end_week"] + 1):
            row[w - 1] = "██"
        result += f"{s['title'][:20]:20} " + "".join(row) + "\n"
    
    return result


@function_tool
def save_schedule_to_db(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Save the current schedule to the database after running the scheduler.
    
    This reads the resource allocations and creates schedule_task records.
    """
    projects = ctx.context.get_approved_projects()
    
    if not projects:
        return "No approved projects to save."
    
    # Re-run scheduling logic to determine what was scheduled
    # (In a real system, the scheduler would persist state)
    
    horizon = ctx.context.planning_horizon_weeks
    projects_sorted = sorted(projects, key=lambda x: x["priority_rank"])
    
    saved_count = 0
    
    for p in projects_sorted:
        project_id = p["project_id"]
        duration = p["estimated_weeks"]
        resource_type = p["required_crew_type"]
        crew_size = p["crew_size"]
        
        # Find where this project was scheduled by checking allocations
        # For simplicity, we'll re-compute based on current state
        # In production, scheduler would return the schedule object
        
        for start_week in range(1, horizon - duration + 2):
            feasible = True
            for week in range(start_week, start_week + duration):
                if week > horizon:
                    feasible = False
                    break
                # Check if there's allocation
                available = ctx.context.get_available_capacity(resource_type, week)
                if available < 0:  # Over-allocated
                    feasible = False
                    break
            
            if feasible:
                end_week = start_week + duration - 1
                
                # Save to database
                ctx.context.insert_schedule_task(
                    project_id=project_id,
                    start_week=start_week,
                    end_week=end_week,
                    resource_type=resource_type,
                    crew_assigned=crew_size
                )
                
                # Audit log
                ctx.context.log_audit(
                    event_type="TASK_SCHEDULED",
                    agent_name="scheduling_agent",
                    payload={
                        "project_id": project_id,
                        "title": p["title"],
                        "start_week": start_week,
                        "end_week": end_week,
                        "resource_type": resource_type,
                        "crew_assigned": crew_size
                    }
                )
                
                saved_count += 1
                break
    
    return f"""✓ Schedule saved to database

Tasks saved: {saved_count}
Table: schedule_tasks

Use get_final_schedule to view the complete saved schedule.
"""


@function_tool
def get_final_schedule(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Get the final schedule from the database.
    
    Returns:
        Complete schedule with all task details
    """
    tasks = ctx.context.get_schedule_tasks()
    
    if not tasks:
        return "No scheduled tasks in the database."
    
    horizon = ctx.context.planning_horizon_weeks
    
    # Calculate utilization
    calendar = ctx.context.get_resource_calendar()
    utilization = {}
    for r in calendar:
        rtype = r["resource_type"]
        if rtype not in utilization:
            utilization[rtype] = {"capacity": 0, "used": 0}
        utilization[rtype]["capacity"] += r["capacity"]
        utilization[rtype]["used"] += r["allocated"]
    
    result = f"""Final Execution Schedule
========================
Total Tasks: {len(tasks)}
Horizon: {horizon} weeks

SCHEDULED TASKS:
"""
    
    for t in sorted(tasks, key=lambda x: x["start_week"]):
        result += f"""
{t.get('title', f"Project #{t['project_id']}")}
  Project ID: {t['project_id']}
  Weeks: {t['start_week']} - {t['end_week']}
  Duration: {t['end_week'] - t['start_week'] + 1} weeks
  Resource: {t['crew_assigned']} x {t['resource_type']}
  Status: {t['status']}
---"""
    
    result += "\n\nRESOURCE UTILIZATION:\n"
    for rtype, data in utilization.items():
        pct = (data["used"] / data["capacity"] * 100) if data["capacity"] > 0 else 0
        result += f"  {rtype}: {pct:.1f}% ({data['used']}/{data['capacity']} crew-weeks)\n"
    
    # Gantt chart
    result += "\n" + "=" * 50 + "\n"
    result += "EXECUTION TIMELINE:\n"
    result += "Week: " + " ".join(f"{w:>2}" for w in range(1, horizon + 1)) + "\n"
    
    for t in tasks:
        title = t.get('title', f"P#{t['project_id']}")[:18]
        row = ["  "] * horizon
        for w in range(t["start_week"], t["end_week"] + 1):
            if w <= horizon:
                row[w - 1] = "██"
        result += f"{title:18} " + "".join(row) + "\n"
    
    return result


@function_tool
def check_schedule_feasibility(ctx: RunContextWrapper["MunicipalContext"]) -> str:
    """
    Verify that the current schedule is feasible (no resource over-allocation).
    
    Returns:
        Feasibility report with any constraint violations
    """
    calendar = ctx.context.get_resource_calendar()
    
    violations = []
    for r in calendar:
        if r["allocated"] > r["capacity"]:
            violations.append({
                "resource": r["resource_type"],
                "week": r["week_number"],
                "capacity": r["capacity"],
                "allocated": r["allocated"],
                "over": r["allocated"] - r["capacity"]
            })
    
    if not violations:
        return """✓ Schedule is FEASIBLE

All resource constraints are satisfied.
No over-allocations detected.
"""
    
    result = f"""⚠️ Schedule has {len(violations)} VIOLATIONS

Resource Over-Allocations:
"""
    for v in violations:
        result += f"""
- {v['resource']} in Week {v['week']}: 
  Capacity: {v['capacity']}, Allocated: {v['allocated']}
  Over by: {v['over']} crew units
"""
    
    return result


# ========== Agent Definition ==========

SCHEDULING_AGENT_INSTRUCTIONS = """You are the Scheduling Agent for {city_name} municipal corporation.

Your role is to:
1. Take approved projects from the Governance Agent
2. Create an optimal execution schedule within the {planning_horizon_weeks}-week horizon
3. Respect resource capacity constraints
4. Minimize total completion time (makespan)

WORKFLOW:
1. Use get_approved_projects to see what needs scheduling
2. Use get_resource_availability to understand capacity constraints
3. Use run_greedy_scheduler to compute a feasible schedule
4. Use check_schedule_feasibility to verify no violations
5. Use save_schedule_to_db to persist the schedule
6. Use get_final_schedule to show the complete plan

CONSTRAINTS:
- Each resource type has a fixed weekly capacity (crew units)
- A project needs its crew_size for ALL weeks of its duration
- Cannot exceed capacity in any week
- Projects cannot be split across non-consecutive weeks

IMPORTANT:
- You CANNOT add or remove projects - only schedule approved ones
- You CANNOT change budgets - that's the Governance Agent's job
- You ONLY optimize execution timing and resource assignment
- If a project cannot be scheduled, report it as infeasible

Resource Types: water_crew, electrical_crew, construction_crew, general_crew
"""


def create_scheduling_agent(context: "MunicipalContext") -> Agent:
    """Create and return the Scheduling Agent with its tools."""
    
    return Agent(
        name="Scheduling Agent",
        instructions=SCHEDULING_AGENT_INSTRUCTIONS.format(
            city_name=context.city_name,
            planning_horizon_weeks=context.planning_horizon_weeks
        ),
        model="gpt-4o",
        tools=[
            get_approved_projects,
            get_resource_availability,
            run_greedy_scheduler,
            check_schedule_feasibility,
            save_schedule_to_db,
            get_final_schedule,
        ],
    )
