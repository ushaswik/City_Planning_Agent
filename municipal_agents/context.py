# -*- coding: utf-8 -*-
"""
Shared context for the Municipal Multi-Agent System.
This context is passed to all agents and tools, providing access to:
- Database connection
- City configuration
- Budget constraints
- Resource availability
"""

import sqlite3
import json
from dataclasses import dataclass, field
from typing import Any, Optional
from datetime import datetime

from .database import (
    DB_PATH, 
    CITY_PROFILE, 
    RISK_THRESHOLDS, 
    RISK_WEIGHTS,
    CREW_MAPPING
)


@dataclass
class MunicipalContext:
    """
    Shared context object for all agents in the pipeline.
    
    This provides:
    - Database access methods
    - City configuration (name, population, budget)
    - Risk calculation parameters
    - Audit logging
    """
    
    db_path: str = DB_PATH
    city_name: str = field(default_factory=lambda: CITY_PROFILE["city_name"])
    population: int = field(default_factory=lambda: CITY_PROFILE["population"])
    quarterly_budget: float = field(default_factory=lambda: CITY_PROFILE["quarterly_budget"])
    planning_horizon_weeks: int = 12
    
    # Risk configuration
    risk_thresholds: dict = field(default_factory=lambda: RISK_THRESHOLDS.copy())
    risk_weights: dict = field(default_factory=lambda: RISK_WEIGHTS.copy())
    crew_mapping: dict = field(default_factory=lambda: CREW_MAPPING.copy())
    
    def get_connection(self) -> sqlite3.Connection:
        """Get a new database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        """Execute a SELECT query and return results as list of dicts."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(sql, params)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            conn.close()
    
    def execute(self, sql: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE and return lastrowid."""
        conn = self.get_connection()
        try:
            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def execute_many(self, sql: str, params_list: list[tuple]) -> None:
        """Execute multiple INSERT/UPDATE/DELETE statements."""
        conn = self.get_connection()
        try:
            conn.executemany(sql, params_list)
            conn.commit()
        finally:
            conn.close()
    
    def log_audit(self, event_type: str, agent_name: str, payload: dict) -> None:
        """Log an audit event for governance trail."""
        self.execute(
            "INSERT INTO audit_log (event_type, agent_name, payload, timestamp) VALUES (?, ?, ?, ?)",
            (event_type, agent_name, json.dumps(payload), datetime.now().isoformat())
        )
    
    # ========== Issue/Signal Queries ==========
    
    def get_open_issues(self) -> list[dict]:
        """Fetch all open issues with their signals."""
        return self.query("""
            SELECT 
                i.issue_id,
                i.title,
                i.category,
                i.description,
                i.source,
                s.population_affected,
                s.complaint_count,
                s.safety_risk,
                s.legal_mandate,
                s.estimated_cost,
                s.urgency_days
            FROM issues i
            LEFT JOIN issue_signals s ON i.issue_id = s.issue_id
            WHERE i.status = 'OPEN'
            ORDER BY s.urgency_days ASC
        """)
    
    def get_issue_by_id(self, issue_id: int) -> Optional[dict]:
        """Fetch a single issue by ID."""
        results = self.query("""
            SELECT 
                i.issue_id, i.title, i.category, i.description,
                s.population_affected, s.complaint_count, 
                s.safety_risk, s.legal_mandate, s.estimated_cost, s.urgency_days
            FROM issues i
            LEFT JOIN issue_signals s ON i.issue_id = s.issue_id
            WHERE i.issue_id = ?
        """, (issue_id,))
        return results[0] if results else None
    
    # ========== Project Candidate Queries ==========
    
    def get_project_candidates(self) -> list[dict]:
        """Fetch all project candidates."""
        return self.query("""
            SELECT * FROM project_candidates ORDER BY risk_score DESC
        """)
    
    def insert_project_candidate(
        self,
        issue_id: int,
        title: str,
        scope: str,
        estimated_cost: float,
        estimated_weeks: int,
        required_crew_type: str,
        crew_size: int,
        risk_score: float,
        feasibility_score: float = 1.0
    ) -> int:
        """Insert a new project candidate, return project_id."""
        return self.execute("""
            INSERT INTO project_candidates 
            (issue_id, title, scope, estimated_cost, estimated_weeks, 
             required_crew_type, crew_size, risk_score, feasibility_score, created_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'formation_agent')
        """, (issue_id, title, scope, estimated_cost, estimated_weeks,
              required_crew_type, crew_size, risk_score, feasibility_score))
    
    # ========== Portfolio Decision Queries ==========
    
    def get_portfolio_decisions(self) -> list[dict]:
        """Fetch all portfolio decisions."""
        return self.query("""
            SELECT pd.*, pc.title, pc.estimated_weeks, pc.required_crew_type, pc.crew_size
            FROM portfolio_decisions pd
            JOIN project_candidates pc ON pd.project_id = pc.project_id
            ORDER BY pd.priority_rank ASC
        """)
    
    def get_approved_projects(self) -> list[dict]:
        """Fetch only approved projects with full details."""
        return self.query("""
            SELECT 
                pd.project_id, pd.allocated_budget, pd.priority_rank,
                pc.title, pc.estimated_weeks, pc.required_crew_type, pc.crew_size
            FROM portfolio_decisions pd
            JOIN project_candidates pc ON pd.project_id = pc.project_id
            WHERE pd.decision = 'APPROVED'
            ORDER BY pd.priority_rank ASC
        """)
    
    def insert_portfolio_decision(
        self,
        project_id: int,
        decision: str,
        allocated_budget: float,
        priority_rank: int,
        rationale: str
    ) -> int:
        """Insert a portfolio decision."""
        return self.execute("""
            INSERT INTO portfolio_decisions 
            (project_id, decision, allocated_budget, priority_rank, rationale, decided_by)
            VALUES (?, ?, ?, ?, ?, 'governance_agent')
        """, (project_id, decision, allocated_budget, priority_rank, rationale))
    
    # ========== Resource Calendar Queries ==========
    
    def get_resource_calendar(self, resource_type: Optional[str] = None) -> list[dict]:
        """Fetch resource calendar, optionally filtered by type."""
        if resource_type:
            return self.query("""
                SELECT * FROM resource_calendar 
                WHERE resource_type = ? 
                ORDER BY week_number
            """, (resource_type,))
        return self.query("""
            SELECT * FROM resource_calendar ORDER BY resource_type, week_number
        """)
    
    def get_available_capacity(self, resource_type: str, week: int) -> int:
        """Get available capacity for a resource type in a given week."""
        results = self.query("""
            SELECT capacity - allocated as available
            FROM resource_calendar
            WHERE resource_type = ? AND week_number = ? AND year = 2025
        """, (resource_type, week))
        return results[0]["available"] if results else 0
    
    def allocate_resource(self, resource_type: str, week: int, units: int) -> bool:
        """Allocate resource units for a week. Returns True if successful."""
        available = self.get_available_capacity(resource_type, week)
        if available >= units:
            self.execute("""
                UPDATE resource_calendar 
                SET allocated = allocated + ?
                WHERE resource_type = ? AND week_number = ? AND year = 2025
            """, (units, resource_type, week))
            return True
        return False
    
    # ========== Schedule Task Queries ==========
    
    def get_schedule_tasks(self) -> list[dict]:
        """Fetch all scheduled tasks."""
        return self.query("""
            SELECT st.*, pc.title
            FROM schedule_tasks st
            JOIN project_candidates pc ON st.project_id = pc.project_id
            ORDER BY st.start_week, st.project_id
        """)
    
    def insert_schedule_task(
        self,
        project_id: int,
        start_week: int,
        end_week: int,
        resource_type: str,
        crew_assigned: int
    ) -> int:
        """Insert a scheduled task."""
        return self.execute("""
            INSERT INTO schedule_tasks 
            (project_id, start_week, end_week, resource_type, crew_assigned, created_by)
            VALUES (?, ?, ?, ?, ?, 'scheduling_agent')
        """, (project_id, start_week, end_week, resource_type, crew_assigned))
    
    # ========== Risk Calculation ==========
    
    def compute_risk_score(self, signal: dict) -> float:
        """
        Compute risk score based on signal data.
        Uses the configured weights and thresholds.
        """
        score = 0.0
        
        if signal.get("safety_risk"):
            score += self.risk_weights["safety_risk"]
        
        if signal.get("legal_mandate"):
            score += self.risk_weights["legal_mandate"]
        
        if signal.get("population_affected", 0) >= self.risk_thresholds["high_population"]:
            score += self.risk_weights["population_impact"]
        
        if signal.get("complaint_count", 0) >= self.risk_thresholds["high_complaints"]:
            score += self.risk_weights["complaint_volume"]
        
        return score
    
    def get_crew_type(self, category: str) -> str:
        """Map issue category to crew type."""
        return self.crew_mapping.get(category, "general_crew")
    
    # ========== Summary Methods ==========
    
    def get_system_summary(self) -> dict:
        """Get a summary of the current system state."""
        candidates = self.get_project_candidates()
        decisions = self.get_portfolio_decisions()
        tasks = self.get_schedule_tasks()
        
        approved = [d for d in decisions if d.get("decision") == "APPROVED"]
        
        return {
            "city": self.city_name,
            "quarterly_budget": self.quarterly_budget,
            "planning_horizon_weeks": self.planning_horizon_weeks,
            "open_issues": len(self.get_open_issues()),
            "project_candidates": len(candidates),
            "approved_projects": len(approved),
            "scheduled_tasks": len(tasks),
            "total_allocated": sum(d.get("allocated_budget", 0) for d in approved),
        }
