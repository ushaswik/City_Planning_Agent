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
from .mcp_servers import get_mcp_client


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
    Run a greedy scheduling algorithm that respects resource constraints, weather, and emergencies.
    
    Algorithm:
    1. Check for active emergencies (may affect priorities)
    2. Sort projects by priority rank (1 = highest)
    3. For each project, find earliest feasible start week
    4. A start week is feasible if:
       - Resource capacity >= crew_size for all weeks
       - Weather is acceptable for outdoor projects
    5. Allocate resources and record schedule
    
    Returns:
        Proposed schedule with start/end weeks for each project
    """
    projects = ctx.context.get_approved_projects()
    
    if not projects:
        return "No approved projects to schedule."
    
    horizon = ctx.context.planning_horizon_weeks
    mcp_client = get_mcp_client()
    weather_server = mcp_client.get_server("weather_service")
    
    # Sort by priority
    projects_sorted = sorted(projects, key=lambda x: x["priority_rank"])
    
    schedule = []
    infeasible = []
    weather_warnings = []
    
    # Get project categories for weather checks
    candidates = {c['project_id']: c for c in ctx.context.get_project_candidates()}
    issues = {i['issue_id']: i for i in ctx.context.get_open_issues()}
    
    for p in projects_sorted:
        project_id = p["project_id"]
        duration = p["estimated_weeks"]
        resource_type = p["required_crew_type"]
        crew_size = p["crew_size"]
        
        # Get category for weather checks
        candidate = candidates.get(project_id, {})
        issue_id = candidate.get('issue_id')
        issue = issues.get(issue_id, {}) if issue_id else {}
        category = issue.get('category', '')
        
        # Determine if outdoor work
        is_outdoor = weather_server.is_outdoor_project(category, resource_type)
        
        # Find earliest feasible start
        scheduled = False
        for start_week in range(1, horizon - duration + 2):
            end_week = start_week + duration - 1
            
            # Check resource capacity
            feasible = True
            for week in range(start_week, start_week + duration):
                if week > horizon:
                    feasible = False
                    break
                available = ctx.context.get_available_capacity(resource_type, week)
                if available < crew_size:
                    feasible = False
                    break
            
            if not feasible:
                continue
            
            # Check weather for outdoor projects
            if is_outdoor:
                try:
                    forecast = mcp_client.call_tool(
                        server="weather_service",
                        tool="get_forecast_for_weeks",
                        arguments={
                            "start_week": start_week,
                            "end_week": end_week,
                            "location": ctx.context.city_name
                        }
                    )
                    
                    # Skip if significant adverse weather (>2 days)
                    if forecast.get('adverse_days', 0) > 2:
                        weather_warnings.append({
                            "project": p["title"],
                            "start_week": start_week,
                            "adverse_days": forecast.get('adverse_days', 0),
                            "reason": "Adverse weather forecasted"
                        })
                        continue  # Try next week
                except:
                    # If weather check fails, proceed (don't block scheduling)
                    pass
            
            # Allocate resources
            for week in range(start_week, start_week + duration):
                ctx.context.allocate_resource(resource_type, week, crew_size)
            
            # Save to database immediately
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
                    "crew_assigned": crew_size,
                    "considerations": {
                        "weather_checked": is_outdoor
                    }
                }
            )
            
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
    
    if weather_warnings:
        result += "\n📊 Weather Considerations:\n"
        result += f"  {len(weather_warnings)} schedule options skipped due to adverse weather\n"
        result += "  (Outdoor projects rescheduled to avoid bad weather)\n"
    
    if infeasible:
        result += "\n⚠️ COULD NOT SCHEDULE (resource/weather constraints):\n"
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
    Save the current schedule to the database.
    
    Note: run_greedy_scheduler now saves the schedule automatically as it schedules projects.
    This function is kept for compatibility but will check what's already scheduled.
    """
    existing_tasks = ctx.context.get_schedule_tasks()
    
    return f"""✓ Schedule Status

Tasks in database: {len(existing_tasks)}

Note: The scheduler (run_greedy_scheduler) automatically saves tasks to the database.
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
def check_weather_for_schedule(
    ctx: RunContextWrapper["MunicipalContext"],
    start_week: int,
    end_week: int,
    category: str = None
) -> str:
    """
    Check weather forecast for a specific date range via MCP.
    
    Args:
        start_week: Starting week number
        end_week: Ending week number
        category: Optional project category to determine if outdoor work
    
    Returns:
        Weather forecast information with recommendations
    """
    mcp_client = get_mcp_client()
    weather_server = mcp_client.get_server("weather_service")
    
    try:
        forecast = mcp_client.call_tool(
            server="weather_service",
            tool="get_forecast_for_weeks",
            arguments={
                "start_week": start_week,
                "end_week": end_week,
                "location": ctx.context.city_name
            }
        )
        
        is_outdoor = weather_server.is_outdoor_project(category or "", "")
        
        result = f"Weather Forecast for Weeks {start_week}-{end_week}\n"
        result += "=" * 50 + "\n"
        result += f"Weather Risk: {forecast.get('weather_risk', 'unknown')}\n"
        result += f"Adverse Weather Days: {forecast.get('adverse_days', 0)}\n"
        
        if forecast.get('adverse_weather_weeks'):
            result += f"Adverse Weather Weeks: {forecast['adverse_weather_weeks']}\n"
        
        result += f"\nRecommendation: {forecast.get('recommendation', 'N/A')}\n"
        
        if is_outdoor and forecast.get('adverse_days', 0) > 2:
            result += "\n⚠️ WARNING: This is outdoor work and adverse weather is forecasted. Consider rescheduling.\n"
        elif not is_outdoor:
            result += "\nℹ️ Indoor work - weather impact is minimal.\n"
        
        return result
    
    except Exception as e:
        return f"Weather check error: {str(e)}. Proceeding without weather data."


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
3. Use check_weather_for_schedule to check weather for specific date ranges
4. Use run_greedy_scheduler to compute a feasible schedule (considers weather conditions)
5. Use check_schedule_feasibility to verify no violations
6. Use save_schedule_to_db to persist the schedule
7. Use get_final_schedule to show the complete plan

CONSTRAINTS:
- Each resource type has a fixed weekly capacity (crew units)
- A project needs its crew_size for ALL weeks of its duration
- Cannot exceed capacity in any week
- Projects cannot be split across non-consecutive weeks
- Outdoor projects should avoid weeks with adverse weather (>2 adverse days)
- Non-urgent projects should avoid weeks affected by active emergencies

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
            check_weather_for_schedule,
            run_greedy_scheduler,
            check_schedule_feasibility,
            save_schedule_to_db,
            get_final_schedule,
        ],
    )
