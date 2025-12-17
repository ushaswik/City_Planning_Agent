# -*- coding: utf-8 -*-
"""
Flask API for Municipal Multi-Agent System
Provides REST endpoints for running the pipeline and retrieving results
"""

import asyncio
import os
import sys
from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from municipal_agents.database import init_database, seed_sample_data, clear_agent_outputs, DB_PATH
from municipal_agents.context import MunicipalContext
from municipal_agents.pipeline import run_municipal_pipeline

app = Flask(__name__)
CORS(app)  # Enable CORS for React frontend


def get_detailed_project_info(context: MunicipalContext) -> list:
    """Get comprehensive project information for the API response."""
    # Get all project candidates
    candidates = context.get_project_candidates()
    
    # Get portfolio decisions
    decisions = context.get_portfolio_decisions()
    
    # Get schedule tasks
    tasks = context.get_schedule_tasks()
    
    # Get issues for additional context
    issues = {issue['issue_id']: issue for issue in context.get_open_issues()}
    
    # Build detailed project list
    projects_formed = []
    for candidate in candidates:
        issue = issues.get(candidate['issue_id'], {})
        decision = next((d for d in decisions if d['project_id'] == candidate['project_id']), None)
        task = next((t for t in tasks if t['project_id'] == candidate['project_id']), None)
        
        project_info = {
            'project_id': candidate['project_id'],
            'title': candidate['title'],
            'scope': candidate.get('scope', ''),
            'issue_id': candidate['issue_id'],
            'issue_title': issue.get('title', ''),
            'category': issue.get('category', ''),
            'estimated_cost': float(candidate['estimated_cost']),
            'estimated_weeks': int(candidate['estimated_weeks']),
            'required_crew_type': candidate['required_crew_type'],
            'crew_size': int(candidate['crew_size']),
            'risk_score': float(candidate['risk_score']),
            'feasibility_score': float(candidate.get('feasibility_score', 1.0)),
            'status': 'formed',
            'decision': None,
            'allocated_budget': None,
            'priority_rank': None,
            'rationale': None,
            'start_week': None,
            'end_week': None,
            'scheduled': False
        }
        
        if decision:
            project_info['status'] = decision['decision'].lower()
            project_info['decision'] = decision['decision']
            project_info['allocated_budget'] = float(decision.get('allocated_budget', 0)) if decision.get('allocated_budget') else None
            project_info['priority_rank'] = int(decision.get('priority_rank', 0)) if decision.get('priority_rank') else None
            project_info['rationale'] = decision.get('rationale', '')
        
        if task:
            project_info['start_week'] = int(task.get('start_week', 0)) if task.get('start_week') else None
            project_info['end_week'] = int(task.get('end_week', 0)) if task.get('end_week') else None
            project_info['scheduled'] = True
        
        projects_formed.append(project_info)
    
    return projects_formed


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Municipal Multi-Agent System API is running'
    })


@app.route('/api/run-pipeline', methods=['POST'])
def run_pipeline():
    """Run the complete municipal pipeline with given budget."""
    try:
        data = request.get_json()
        budget = data.get('budget')
        
        if budget is None:
            return jsonify({'error': 'Budget is required'}), 400
        
        try:
            budget = float(budget)
            if budget <= 0:
                return jsonify({'error': 'Budget must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Budget must be a valid number'}), 400
        
        # Initialize database if needed
        if not os.path.exists(DB_PATH):
            init_database()
            seed_sample_data()
        
        # Create context with provided budget
        context = MunicipalContext(quarterly_budget=budget)
        
        # Clear previous agent outputs
        clear_agent_outputs(context.db_path)
        
        # Run the pipeline
        results = asyncio.run(run_municipal_pipeline(context, reset_data=False, verbose=False))
        
        # Get detailed project information
        projects = get_detailed_project_info(context)
        
        # Get summary
        summary = context.get_system_summary()
        
        # Prepare response with sorted projects
        approved = [p for p in projects if p['decision'] == 'APPROVED']
        # Sort approved projects by priority_rank (1 = highest priority)
        approved.sort(key=lambda x: x['priority_rank'] if x['priority_rank'] is not None else 999)
        
        # Renumber approved projects sequentially (1, 2, 3, 4...) for display
        # This makes it clearer when some projects were rejected
        for idx, project in enumerate(approved, start=1):
            project['display_priority'] = idx
            project['original_priority'] = project.get('priority_rank')
        
        response = {
            'success': True,
            'summary': {
                'projects_formed': summary['project_candidates'],
                'projects_approved': summary['approved_projects'],
                'tasks_scheduled': summary['scheduled_tasks'],
                'total_budget_allocated': summary['total_allocated'],
                'budget_remaining': budget - summary['total_allocated'],
                'quarterly_budget': budget
            },
            'projects': projects,
            'approved_projects': approved,
            'rejected_projects': [p for p in projects if p['decision'] == 'REJECTED']
        }
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/init-db', methods=['POST'])
def init_db():
    """Initialize database with sample data."""
    try:
        init_database()
        seed_sample_data()
        return jsonify({
            'success': True,
            'message': 'Database initialized with sample data'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    # Initialize database on startup if it doesn't exist
    if not os.path.exists(DB_PATH):
        print("Initializing database...")
        init_database()
        seed_sample_data()
    
    app.run(debug=True, port=5000, host='0.0.0.0')

