"""Lightweight shim for the external `agents` SDK used by this project.

This module provides minimal implementations of the following symbols so the
local repository can run without the full OpenAI Agents SDK during
development and testing:

- Agent: simple container for agent metadata and tools
- function_tool: decorator that marks a callable as a tool
- RunContextWrapper: wrapper exposing the pipeline context to tools
- Runner.run: async runner that executes a simple deterministic workflow
- trace: context manager used for simple tracing/logging

The implementations here are intentionally small and deterministic — they
implement the pipeline logic directly using the application's `MunicipalContext`
APIs (database interactions, scoring, insertion). This keeps behavior
reproducible for the UI and local usage.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, List, Optional
import asyncio


class RunContextWrapper:
    """Wrapper passed into tool functions so they receive the shared context.

    Tools in the repo expect a parameter `ctx` with a `.context` attribute.
    """

    def __init__(self, context: Any):
        self.context = context


def function_tool(func: Callable) -> Callable:
    """Decorator to mark a function as a tool. For compatibility we simply
    attach metadata and return the function unchanged.
    """

    setattr(func, "_is_tool", True)
    return func


@contextmanager
def trace(label: str):
    print(f"--- TRACE START: {label} ---")
    try:
        yield
    finally:
        print(f"--- TRACE END: {label} ---")


@dataclass
class Agent:
    name: str
    instructions: str
    model: Optional[str] = None
    tools: List[Callable] = None
    output_type: Optional[Any] = None


class _RunResult:
    def __init__(self, final_output: str):
        self.final_output = final_output


class Runner:
    """Very small runner that executes agent logic deterministically.

    The runner understands the three agents used by the repo (Formation,
    Governance, Scheduling) and runs a deterministic sequence against the
    provided `MunicipalContext`. This is sufficient for local development and
    for the UI integration.
    """

    @staticmethod
    async def run(agent: Agent, prompt: str, context: Any = None) -> _RunResult:
        # Simulate some async work and return an informative string.
        # Use the context methods (DB operations) directly to ensure state is
        # persisted and visible to the UI.
        if context is None:
            raise RuntimeError("Runner requires a MunicipalContext via `context=`")

        out_lines: List[str] = []

        # Formation agent: create project candidates for high-risk issues
        if agent.name and "Formation" in agent.name:
            with trace("Formation Runner"):
                issues = context.get_open_issues()
                out_lines.append(f"Found {len(issues)} open issues")
                created = 0
                for issue in issues:
                    score = context.compute_risk_score(issue)
                    out_lines.append(f"Issue #{issue['issue_id']} risk={score}")
                    if score >= context.risk_thresholds["high_risk_score"]:
                        # Estimate resources using repo heuristics
                        crew_type = context.get_crew_type(issue["category"])
                        est_cost = issue.get("estimated_cost", 0) or 0
                        # durations/crew size heuristic (matches original tool)
                        if est_cost >= 50_000_000:
                            weeks = 8; crew = 3
                        elif est_cost >= 10_000_000:
                            weeks = 4; crew = 2
                        elif est_cost >= 1_000_000:
                            weeks = 2; crew = 2
                        else:
                            weeks = 1; crew = 1

                        pid = context.insert_project_candidate(
                            issue_id=issue["issue_id"],
                            title=f"Project for {issue['title']}",
                            scope=f"Auto-generated candidate for issue {issue['issue_id']}",
                            estimated_cost=est_cost,
                            estimated_weeks=weeks,
                            required_crew_type=crew_type,
                            crew_size=crew,
                            risk_score=score,
                        )
                        created += 1
                        out_lines.append(f"Created project candidate #{pid} for issue {issue['issue_id']}")

                out_lines.append(f"Total project candidates created: {created}")

        # Governance agent: naive greedy selection within budget
        elif agent.name and "Governance" in agent.name:
            with trace("Governance Runner"):
                candidates = context.get_project_candidates()
                budget = context.quarterly_budget
                out_lines.append(f"Budget: ${budget:,.0f}")

                # Prioritize legal mandate projects first
                def score_density(c):
                    # Avoid division by zero
                    return (c.get("risk_score", 0) / (c.get("estimated_cost", 1) or 1))

                # Sort legal mandate projects first
                prioritized = sorted(candidates, key=lambda c: (-c.get("risk_score", 0), score_density(c)), reverse=False)

                remaining = budget
                rank = 1
                approvals = 0
                for c in prioritized:
                    cost = c.get("estimated_cost", 0) or 0
                    if cost <= remaining:
                        context.insert_portfolio_decision(
                            project_id=c["project_id"],
                            decision="APPROVED",
                            allocated_budget=cost,
                            priority_rank=rank,
                            rationale="Auto-approved by governance agent"
                        )
                        remaining -= cost
                        approvals += 1
                        out_lines.append(f"APPROVED project {c['project_id']} (${cost:,.0f})")
                        rank += 1
                    else:
                        context.insert_portfolio_decision(
                            project_id=c["project_id"],
                            decision="REJECTED",
                            allocated_budget=0,
                            priority_rank=rank,
                            rationale="Insufficient budget"
                        )
                        out_lines.append(f"REJECTED project {c['project_id']} (${cost:,.0f}) - insufficient budget")
                        rank += 1

                out_lines.append(f"Approvals: {approvals}, Remaining budget: ${remaining:,.0f}")

        # Scheduling agent: schedule approved projects earliest-first
        elif agent.name and "Scheduling" in agent.name:
            with trace("Scheduling Runner"):
                approved = context.get_approved_projects()
                out_lines.append(f"Approved projects: {len(approved)}")
                scheduled = 0
                for proj in approved:
                    crew_type = proj.get("required_crew_type", "general_crew")
                    weeks = proj.get("estimated_weeks", 1)
                    # find earliest week with capacity across consecutive weeks
                    for start in range(1, context.planning_horizon_weeks + 1):
                        can_allocate = True
                        # check each week
                        for w in range(start, min(start + weeks, context.planning_horizon_weeks + 1)):
                            if context.get_available_capacity(crew_type, w) < proj.get("crew_size", 1):
                                can_allocate = False
                                break
                        if can_allocate:
                            # allocate
                            for w in range(start, min(start + weeks, context.planning_horizon_weeks + 1)):
                                context.allocate_resource(crew_type, w, proj.get("crew_size", 1))
                            context.insert_schedule_task(project_id=proj["project_id"], start_week=start, end_week=start + weeks - 1, resource_type=crew_type, crew_assigned=proj.get("crew_size", 1))
                            scheduled += 1
                            out_lines.append(f"Scheduled project {proj['project_id']} wks {weeks} starting week {start}")
                            break

                out_lines.append(f"Total scheduled: {scheduled}")

        else:
            # Fallback behaviour: echo prompt
            out_lines.append("Agent run echo (no-op)")
            out_lines.append(prompt or "(no prompt provided)")

        # Simulate I/O latency
        await asyncio.sleep(0)

        return _RunResult(final_output="\n".join(out_lines))


__all__ = [
    "Agent",
    "Runner",
    "function_tool",
    "RunContextWrapper",
    "trace",
]
