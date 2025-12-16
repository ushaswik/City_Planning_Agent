# -*- coding: utf-8 -*-
"""
Database schema and initialization for Municipal Multi-Agent System.
Extended schema to support the full 3-agent pipeline.
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "database/city_risk.db"


def init_database(db_path: str = DB_PATH) -> None:
    """
    Initialize the database with all required tables for the multi-agent pipeline.
    
    Tables:
    - issues: Raw citizen complaints/demands (input)
    - issue_signals: Risk/impact signals attached to issues
    - project_candidates: Agent 1 output - structured project proposals
    - portfolio_decisions: Agent 2 output - approved/rejected decisions
    - resource_calendar: Available resources by week
    - schedule_tasks: Agent 3 output - scheduled work
    - audit_log: Governance audit trail
    """
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Raw Issues (The Demand) - citizen complaints, reports, mandates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issues (
        issue_id INTEGER PRIMARY KEY,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT,
        source TEXT DEFAULT 'citizen_complaint',
        status TEXT DEFAULT 'OPEN',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # 2. Issue Signals (The Data) - quantified impact/risk metrics
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS issue_signals (
        issue_id INTEGER PRIMARY KEY,
        population_affected INTEGER CHECK(population_affected >= 0),
        complaint_count INTEGER CHECK(complaint_count >= 0),
        safety_risk INTEGER CHECK(safety_risk IN (0, 1)),
        legal_mandate INTEGER CHECK(legal_mandate IN (0, 1)),
        estimated_cost INTEGER,
        urgency_days INTEGER DEFAULT 90,
        FOREIGN KEY(issue_id) REFERENCES issues(issue_id)
    )
    """)
    
    # 3. Project Candidates (Agent 1 Output)
    # Transforms a "problem" into a "proposed solution" with estimates
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS project_candidates (
        project_id INTEGER PRIMARY KEY AUTOINCREMENT,
        issue_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        scope TEXT,
        estimated_cost REAL NOT NULL,
        estimated_weeks INTEGER NOT NULL,
        required_crew_type TEXT DEFAULT 'general',
        crew_size INTEGER DEFAULT 1,
        risk_score REAL NOT NULL,
        feasibility_score REAL DEFAULT 1.0,
        created_by TEXT DEFAULT 'formation_agent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(issue_id) REFERENCES issues(issue_id)
    )
    """)
    
    # 4. Portfolio Decisions (Agent 2 Output)
    # Records which projects got funding approval
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS portfolio_decisions (
        decision_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        decision TEXT CHECK(decision IN ('APPROVED', 'REJECTED', 'DEFERRED')),
        allocated_budget REAL,
        priority_rank INTEGER,
        rationale TEXT,
        decided_by TEXT DEFAULT 'governance_agent',
        decided_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES project_candidates(project_id)
    )
    """)
    
    # 5. Resource Calendar - available resources by week
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS resource_calendar (
        resource_id INTEGER PRIMARY KEY AUTOINCREMENT,
        resource_type TEXT NOT NULL,
        week_number INTEGER NOT NULL,
        year INTEGER NOT NULL,
        capacity INTEGER NOT NULL,
        allocated INTEGER DEFAULT 0,
        UNIQUE(resource_type, week_number, year)
    )
    """)
    
    # 6. Schedule Tasks (Agent 3 Output)
    # The actual execution schedule
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS schedule_tasks (
        task_id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        start_week INTEGER NOT NULL,
        end_week INTEGER NOT NULL,
        resource_type TEXT NOT NULL,
        crew_assigned INTEGER DEFAULT 1,
        status TEXT DEFAULT 'SCHEDULED',
        created_by TEXT DEFAULT 'scheduling_agent',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(project_id) REFERENCES project_candidates(project_id)
    )
    """)
    
    # 7. Audit Log - governance trail for all agent decisions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        log_id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        agent_name TEXT NOT NULL,
        payload TEXT,  -- JSON serialized
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    print("✓ Database schema initialized")


def seed_sample_data(db_path: str = DB_PATH) -> None:
    """
    Insert sample issues and signals for demonstration.
    """
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Clear existing data to prevent duplicates on re-runs
    cursor.execute("DELETE FROM schedule_tasks")
    cursor.execute("DELETE FROM portfolio_decisions")
    cursor.execute("DELETE FROM project_candidates")
    cursor.execute("DELETE FROM resource_calendar")
    cursor.execute("DELETE FROM issue_signals")
    cursor.execute("DELETE FROM issues")
    cursor.execute("DELETE FROM audit_log")
    
    # Sample Issues
    issues_data = [
        (1, "Major Water Pipeline Rupture", "Water", 
         "Critical water main break affecting downtown area", "emergency_report", "OPEN"),
        (2, "Hospital Power Backup Failure", "Health",
         "Primary backup generator at City Hospital non-functional", "facility_inspection", "OPEN"),
        (3, "Urban Flooding in Low-Lying Areas", "Disaster Management",
         "Recurring flooding in Districts 4 and 7 during monsoon", "citizen_complaint", "OPEN"),
        (4, "Pothole Complaints in Residential Zones", "Infrastructure",
         "Multiple potholes reported on Main St and Oak Ave", "citizen_complaint", "OPEN"),
        (5, "Public Park Renovation Delay", "Recreation",
         "Central Park playground equipment outdated", "council_request", "OPEN"),
        (6, "Street Light Outages", "Infrastructure",
         "Multiple street lights non-functional in Sector 12", "citizen_complaint", "OPEN"),
        (7, "School Zone Safety Improvements", "Education",
         "Need for crosswalks and speed bumps near Lincoln Elementary", "citizen_complaint", "OPEN"),
    ]
    
    # Signals: (issue_id, population, complaints, safety, legal, est_cost, urgency_days)
    signals_data = [
        (1, 450000, 1200, 1, 1, 45000000, 7),    # Critical - affects half the city
        (2, 180000, 300, 1, 1, 12000000, 14),    # Critical - hospital safety
        (3, 600000, 900, 1, 0, 60000000, 30),    # High - monsoon preparedness
        (4, 80000, 40, 0, 0, 4000000, 60),       # Medium - quality of life
        (5, 15000, 12, 0, 0, 2500000, 180),      # Low - can wait
        (6, 25000, 85, 1, 0, 800000, 45),        # Medium-High - safety concern
        (7, 5000, 150, 1, 0, 500000, 30),        # Medium - child safety
    ]
    
    cursor.executemany(
        "INSERT INTO issues (issue_id, title, category, description, source, status) VALUES (?, ?, ?, ?, ?, ?)",
        issues_data
    )
    
    cursor.executemany(
        "INSERT INTO issue_signals (issue_id, population_affected, complaint_count, safety_risk, legal_mandate, estimated_cost, urgency_days) VALUES (?, ?, ?, ?, ?, ?, ?)",
        signals_data
    )
    
    # Seed resource calendar (12 weeks, 2025)
    resource_types = ["water_crew", "electrical_crew", "construction_crew", "general_crew"]
    capacities = {"water_crew": 3, "electrical_crew": 2, "construction_crew": 5, "general_crew": 4}
    
    for week in range(1, 13):
        for rtype in resource_types:
            cursor.execute(
                "INSERT INTO resource_calendar (resource_type, week_number, year, capacity, allocated) VALUES (?, ?, ?, ?, ?)",
                (rtype, week, 2025, capacities[rtype], 0)
            )
    
    conn.commit()
    conn.close()
    print("✓ Sample data seeded")


def clear_agent_outputs(db_path: str = DB_PATH) -> None:
    """Clear all agent-generated data (for re-running pipeline)."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM schedule_tasks")
    cursor.execute("DELETE FROM portfolio_decisions")
    cursor.execute("DELETE FROM project_candidates")
    cursor.execute("UPDATE resource_calendar SET allocated = 0")
    cursor.execute("DELETE FROM audit_log")
    
    conn.commit()
    conn.close()
    print("✓ Agent outputs cleared")


# City Profile and Risk Configuration
CITY_PROFILE = {
    "city_name": "Metroville",
    "population": 2_500_000,
    "quarterly_budget": 75_000_000,  # $75M quarterly budget
}

RISK_THRESHOLDS = {
    "high_population": 100_000,
    "high_complaints": 75,
    "high_risk_score": 3,
}

RISK_WEIGHTS = {
    "safety_risk": 3,
    "legal_mandate": 3,
    "population_impact": 1,
    "complaint_volume": 1,
}

# Crew type mapping by category
CREW_MAPPING = {
    "Water": "water_crew",
    "Health": "electrical_crew",
    "Disaster Management": "construction_crew",
    "Infrastructure": "construction_crew",
    "Recreation": "general_crew",
    "Education": "general_crew",
}


if __name__ == "__main__":
    init_database()
    seed_sample_data()
