# -*- coding: utf-8 -*-
"""
Municipal Multi-Agent System - Main Entry Point

This script demonstrates the complete 3-agent pipeline:
1. Formation Agent: Issues → Project Candidates
2. Governance Agent: Budget Allocation & Approval
3. Scheduling Agent: Resource-Constrained Scheduling

Usage:
    python run_pipeline.py [--init] [--stage STAGE]
    
    --init      Initialize database with sample data
    --stage     Run specific stage: formation, governance, scheduling
"""

import asyncio
import sys
import os

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from municipal_agents.database import init_database, seed_sample_data, clear_agent_outputs, DB_PATH
from municipal_agents.context import MunicipalContext
from municipal_agents.pipeline import run_municipal_pipeline, run_interactive_stage


async def main():
    """Main entry point for the municipal multi-agent system."""
    
    print("""
╔══════════════════════════════════════════════════════════════╗
║     MUNICIPAL CORPORATION MULTI-AGENT SYSTEM                ║
║     Project Formation → Governance → Scheduling              ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Parse simple command line args
    args = sys.argv[1:]
    
    if "--help" in args or "-h" in args:
        print(__doc__)
        return
    
    # Initialize database
    if "--init" in args or not os.path.exists(DB_PATH):
        print("Initializing database...")
        init_database()
        seed_sample_data()
    
    # Create context
    context = MunicipalContext()
    
    # Show current state
    summary = context.get_system_summary()
    print(f"""
System State:
  City: {summary['city']}
  Quarterly Budget: ${summary['quarterly_budget']:,.0f}
  Open Issues: {summary['open_issues']}
  Project Candidates: {summary['project_candidates']}
  Approved Projects: {summary['approved_projects']}
  Scheduled Tasks: {summary['scheduled_tasks']}
    """)
    
    # Run specific stage or full pipeline
    if "--stage" in args:
        idx = args.index("--stage")
        if idx + 1 < len(args):
            stage = args[idx + 1]
            print(f"\nRunning {stage} stage only...")
            await run_interactive_stage(stage, context)
        else:
            print("Error: --stage requires a value (formation, governance, scheduling)")
        return
    
    # Run full pipeline
    if "--run" in args or True:  # Default to running
        print("\nRunning complete pipeline...")
        print("Note: Ensure OPENAI_API_KEY is set in environment.\n")
        
        try:
            results = await run_municipal_pipeline(context, reset_data=True, verbose=True)
            
            # Final summary
            print("\n" + "=" * 60)
            print("EXECUTION COMPLETE")
            print("=" * 60)
            print(f"""
Final Results:
  Projects Formed: {results['summary']['project_candidates']}
  Projects Approved: {results['summary']['approved_projects']}
  Tasks Scheduled: {results['summary']['scheduled_tasks']}
  Budget Allocated: ${results['summary']['total_allocated']:,.0f}
  Budget Remaining: ${context.quarterly_budget - results['summary']['total_allocated']:,.0f}
            """)
            
        except Exception as e:
            print(f"\n❌ Error running pipeline: {e}")
            print("\nTroubleshooting:")
            print("1. Ensure OPENAI_API_KEY is set: export OPENAI_API_KEY='your-key'")
            print("2. Install dependencies: pip install openai-agents pydantic")
            print("3. Check database exists: python run_pipeline.py --init")
            raise


if __name__ == "__main__":
    asyncio.run(main())
