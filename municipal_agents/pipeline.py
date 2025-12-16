# -*- coding: utf-8 -*-
"""
Municipal Multi-Agent Pipeline Orchestrator

This module provides the main pipeline that chains the three agents:
1. Formation Agent → Creates project candidates from issues
2. Governance Agent → Approves/rejects under budget constraints
3. Scheduling Agent → Optimizes execution schedule

The pipeline can be run end-to-end or step-by-step.
"""

import asyncio
from typing import Optional

from agents import Runner, trace

from .context import MunicipalContext
from .database import init_database, seed_sample_data, clear_agent_outputs
from .formation_agent import create_formation_agent
from .governance_agent import create_governance_agent
from .scheduling_agent import create_scheduling_agent


async def run_formation_stage(
    context: MunicipalContext,
    verbose: bool = True
) -> str:
    """
    Run Agent 1: Project Formation
    
    Converts open issues into structured project candidates.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("STAGE 1: PROJECT FORMATION")
        print("=" * 60)
    
    agent = create_formation_agent(context)
    
    prompt = """Please analyze all open citizen issues and create project candidates 
for HIGH RISK items (risk_score >= 3).

For each high-risk issue:
1. Calculate the risk score
2. Estimate resources needed
3. Create a project candidate

Provide a summary of all candidates created."""
    
    with trace("Formation Stage"):
        result = await Runner.run(agent, prompt, context=context)
    
    if verbose:
        print(f"\nFormation Agent Output:\n{result.final_output}")
    
    return result.final_output


async def run_governance_stage(
    context: MunicipalContext,
    verbose: bool = True
) -> str:
    """
    Run Agent 2: Governance / Budget Allocation
    
    Reviews candidates and makes funding decisions.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("STAGE 2: GOVERNANCE / BUDGET ALLOCATION")
        print("=" * 60)
    
    agent = create_governance_agent(context)
    
    prompt = """Review all project candidates and allocate the quarterly budget.

Steps:
1. Get all project candidates
2. Check budget status
3. Run the knapsack optimization for recommendations
4. Approve high-priority projects (legal mandates first, then by risk)
5. Reject projects that don't fit the budget
6. Show the final portfolio summary

Remember: Stay within the quarterly budget!"""
    
    with trace("Governance Stage"):
        result = await Runner.run(agent, prompt, context=context)
    
    if verbose:
        print(f"\nGovernance Agent Output:\n{result.final_output}")
    
    return result.final_output


async def run_scheduling_stage(
    context: MunicipalContext,
    verbose: bool = True
) -> str:
    """
    Run Agent 3: Scheduling / Resource Optimization
    
    Creates execution schedule for approved projects.
    """
    if verbose:
        print("\n" + "=" * 60)
        print("STAGE 3: SCHEDULING / RESOURCE OPTIMIZATION")
        print("=" * 60)
    
    agent = create_scheduling_agent(context)
    
    prompt = """Create an optimized execution schedule for all approved projects.

Steps:
1. Get the list of approved projects
2. Check resource availability across the planning horizon
3. Run the greedy scheduler to assign start weeks
4. Verify schedule feasibility (no resource violations)
5. Save the schedule to the database
6. Show the final schedule with Gantt chart

Optimize for minimal makespan while respecting resource constraints."""
    
    with trace("Scheduling Stage"):
        result = await Runner.run(agent, prompt, context=context)
    
    if verbose:
        print(f"\nScheduling Agent Output:\n{result.final_output}")
    
    return result.final_output


async def run_municipal_pipeline(
    context: Optional[MunicipalContext] = None,
    reset_data: bool = True,
    verbose: bool = True
) -> dict:
    """
    Run the complete 3-agent municipal pipeline.
    
    Args:
        context: Optional MunicipalContext (creates default if None)
        reset_data: If True, clears previous agent outputs before running
        verbose: If True, prints progress and outputs
    
    Returns:
        dict with results from each stage
    """
    if context is None:
        context = MunicipalContext()
    
    if reset_data:
        clear_agent_outputs(context.db_path)
    
    if verbose:
        print("\n" + "=" * 60)
        print(f"MUNICIPAL MULTI-AGENT PIPELINE")
        print(f"City: {context.city_name}")
        print(f"Quarterly Budget: ${context.quarterly_budget:,.0f}")
        print(f"Planning Horizon: {context.planning_horizon_weeks} weeks")
        print("=" * 60)
    
    with trace("Municipal Pipeline"):
        # Stage 1: Formation
        formation_result = await run_formation_stage(context, verbose)
        
        # Stage 2: Governance
        governance_result = await run_governance_stage(context, verbose)
        
        # Stage 3: Scheduling
        scheduling_result = await run_scheduling_stage(context, verbose)
    
    # Generate summary
    summary = context.get_system_summary()
    
    if verbose:
        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"Project Candidates Created: {summary['project_candidates']}")
        print(f"Projects Approved: {summary['approved_projects']}")
        print(f"Tasks Scheduled: {summary['scheduled_tasks']}")
        print(f"Total Budget Allocated: ${summary['total_allocated']:,.0f}")
        print(f"Budget Remaining: ${context.quarterly_budget - summary['total_allocated']:,.0f}")
    
    return {
        "formation": formation_result,
        "governance": governance_result,
        "scheduling": scheduling_result,
        "summary": summary
    }


def run_pipeline_sync(
    context: Optional[MunicipalContext] = None,
    reset_data: bool = True,
    verbose: bool = True
) -> dict:
    """
    Synchronous wrapper for the pipeline.
    """
    return asyncio.run(run_municipal_pipeline(context, reset_data, verbose))


# ========== Interactive Mode ==========

async def run_interactive_stage(
    stage: str,
    context: Optional[MunicipalContext] = None,
    custom_prompt: Optional[str] = None,
    verbose: bool = True
) -> str:
    """
    Run a single stage interactively with optional custom prompt.
    
    Args:
        stage: One of 'formation', 'governance', 'scheduling'
        context: Optional context (creates default if None)
        custom_prompt: Optional custom prompt (uses default if None)
        verbose: Print output
    
    Returns:
        Agent output
    """
    if context is None:
        context = MunicipalContext()
    
    stage_map = {
        "formation": (create_formation_agent, run_formation_stage),
        "governance": (create_governance_agent, run_governance_stage),
        "scheduling": (create_scheduling_agent, run_scheduling_stage),
    }
    
    if stage not in stage_map:
        raise ValueError(f"Unknown stage: {stage}. Use one of {list(stage_map.keys())}")
    
    if custom_prompt:
        agent_factory, _ = stage_map[stage]
        agent = agent_factory(context)
        
        with trace(f"{stage.title()} Stage (Custom)"):
            result = await Runner.run(agent, custom_prompt, context=context)
        
        if verbose:
            print(f"\n{stage.title()} Agent Output:\n{result.final_output}")
        
        return result.final_output
    else:
        _, stage_runner = stage_map[stage]
        return await stage_runner(context, verbose)


# ========== CLI Entry Point ==========

def main():
    """Command-line entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Municipal Multi-Agent Pipeline")
    parser.add_argument(
        "--init-db", 
        action="store_true",
        help="Initialize database and seed sample data"
    )
    parser.add_argument(
        "--run", 
        action="store_true",
        help="Run the complete pipeline"
    )
    parser.add_argument(
        "--stage",
        choices=["formation", "governance", "scheduling"],
        help="Run a specific stage only"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        default=True,
        help="Clear agent outputs before running (default: True)"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress verbose output"
    )
    
    args = parser.parse_args()
    
    if args.init_db:
        init_database()
        seed_sample_data()
        print("Database initialized with sample data.")
        return
    
    if args.run:
        run_pipeline_sync(reset_data=args.reset, verbose=not args.quiet)
        return
    
    if args.stage:
        asyncio.run(run_interactive_stage(
            args.stage,
            verbose=not args.quiet
        ))
        return
    
    parser.print_help()


if __name__ == "__main__":
    main()
