# -*- coding: utf-8 -*-
"""
Pydantic models for structured agent outputs.
These enforce typed handoffs between pipeline stages.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ProjectCandidate(BaseModel):
    """Agent 1 output: A structured project proposal with estimates."""
    
    project_id: Optional[int] = Field(None, description="Database ID (set after insertion)")
    issue_id: int = Field(..., description="Reference to the original issue")
    title: str = Field(..., description="Project title")
    scope: str = Field(..., description="Brief scope description")
    estimated_cost: float = Field(..., ge=0, description="Estimated cost in USD")
    estimated_weeks: int = Field(..., ge=1, description="Estimated duration in weeks")
    required_crew_type: str = Field(..., description="Type of crew needed")
    crew_size: int = Field(1, ge=1, description="Number of crew units needed")
    risk_score: float = Field(..., ge=0, description="Computed risk score")
    feasibility_score: float = Field(1.0, ge=0, le=1, description="Feasibility rating 0-1")
    
    class Config:
        json_schema_extra = {
            "example": {
                "issue_id": 1,
                "title": "Water Pipeline Emergency Repair",
                "scope": "Replace ruptured 24-inch main line in downtown",
                "estimated_cost": 45000000,
                "estimated_weeks": 4,
                "required_crew_type": "water_crew",
                "crew_size": 3,
                "risk_score": 8,
                "feasibility_score": 0.9
            }
        }


class ProjectCandidateList(BaseModel):
    """List of project candidates from Agent 1."""
    candidates: list[ProjectCandidate] = Field(default_factory=list)
    total_estimated_cost: float = Field(0, description="Sum of all candidate costs")
    high_risk_count: int = Field(0, description="Number of high-risk projects")


class ApprovedProject(BaseModel):
    """A project that has been approved for funding."""
    project_id: int
    title: str
    allocated_budget: float
    priority_rank: int
    estimated_weeks: int
    required_crew_type: str
    crew_size: int


class PortfolioSelection(BaseModel):
    """Agent 2 output: Portfolio decision with approved projects."""
    
    approved_projects: list[ApprovedProject] = Field(default_factory=list)
    rejected_project_ids: list[int] = Field(default_factory=list)
    total_budget_used: float = Field(0, description="Total allocated budget")
    budget_remaining: float = Field(0, description="Remaining budget")
    rationale: str = Field("", description="Explanation of selection logic")
    
    class Config:
        json_schema_extra = {
            "example": {
                "approved_projects": [
                    {
                        "project_id": 1,
                        "title": "Water Pipeline Repair",
                        "allocated_budget": 45000000,
                        "priority_rank": 1,
                        "estimated_weeks": 4,
                        "required_crew_type": "water_crew",
                        "crew_size": 3
                    }
                ],
                "rejected_project_ids": [5],
                "total_budget_used": 45000000,
                "budget_remaining": 30000000,
                "rationale": "Prioritized by risk score, legal mandates first"
            }
        }


class ScheduleTask(BaseModel):
    """A scheduled task assignment."""
    project_id: int
    title: str
    start_week: int
    end_week: int
    resource_type: str
    crew_assigned: int


class ScheduleOutput(BaseModel):
    """Agent 3 output: Optimized execution schedule."""
    
    tasks: list[ScheduleTask] = Field(default_factory=list)
    total_weeks: int = Field(0, description="Total schedule span in weeks")
    resource_utilization: dict[str, float] = Field(
        default_factory=dict, 
        description="Utilization percentage by resource type"
    )
    schedule_feasible: bool = Field(True, description="Whether schedule is feasible")
    optimization_notes: str = Field("", description="Notes from the scheduler")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tasks": [
                    {
                        "project_id": 1,
                        "title": "Water Pipeline Repair",
                        "start_week": 1,
                        "end_week": 4,
                        "resource_type": "water_crew",
                        "crew_assigned": 3
                    }
                ],
                "total_weeks": 12,
                "resource_utilization": {"water_crew": 0.75, "construction_crew": 0.60},
                "schedule_feasible": True,
                "optimization_notes": "Optimized for minimal makespan"
            }
        }


class AuditLogEntry(BaseModel):
    """Audit log entry for governance trail."""
    event_type: str
    agent_name: str
    payload: dict
    timestamp: datetime = Field(default_factory=datetime.now)
