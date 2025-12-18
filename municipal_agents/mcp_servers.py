# -*- coding: utf-8 -*-
"""
Mock MCP Server for Weather Service

This simulates external municipal weather system that would be accessed via MCP in production.
For demo purposes, it returns realistic mock data. In production, this would be 
replaced with an actual MCP server connecting to a real weather API.
"""

from typing import Dict, Any, List


class WeatherServiceMCPServer:
    """Mock Weather Service MCP Server - Simulates weather forecast data"""
    
    def call_tool(self, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a tool on this MCP server"""
        if tool == "get_forecast_for_weeks":
            start_week = arguments.get("start_week", 1)
            end_week = arguments.get("end_week", 12)
            location = arguments.get("location", "")
            
            # Simulate weather forecast
            # Weeks 3-4 typically have adverse weather (winter), weeks 8-9 have some rain
            adverse_weather_weeks = []
            adverse_days = 0
            
            # Weeks 3-4: Winter weather (adverse for outdoor work)
            if start_week <= 4 <= end_week or (3 <= start_week <= 4):
                adverse_weather_weeks.extend([w for w in range(max(3, start_week), min(5, end_week + 1))])
                adverse_days += 5  # 5 days of adverse weather
            
            # Weeks 8-9: Some rain
            if start_week <= 9 <= end_week or (8 <= start_week <= 9):
                adverse_weather_weeks.extend([w for w in range(max(8, start_week), min(10, end_week + 1))])
                adverse_days += 2  # 2 days of rain
            
            weather_risk = "high" if adverse_days > 3 else ("medium" if adverse_days > 0 else "low")
            
            recommendation = "Consider rescheduling outdoor work" if adverse_days > 2 else (
                "Monitor weather, minor risk" if adverse_days > 0 else "Weather looks favorable"
            )
            
            return {
                "adverse_days": adverse_days,
                "adverse_weather_weeks": adverse_weather_weeks,
                "weather_risk": weather_risk,
                "recommendation": recommendation,
                "location": location,
                "forecast_period": f"Weeks {start_week}-{end_week}"
            }
        
        return {}
    
    def is_outdoor_project(self, category: str, crew_type: str) -> bool:
        """Determine if a project type is typically outdoor work"""
        outdoor_categories = ["Infrastructure", "Water", "Construction"]
        outdoor_crews = ["construction_crew", "water_crew", "general_crew"]
        
        return category in outdoor_categories or crew_type in outdoor_crews


# Global MCP client wrapper
class MCPClient:
    """
    Simple MCP client for accessing mock external services.
    
    In production, this would use the actual MCP SDK to connect to real MCP servers.
    """
    
    def __init__(self):
        """Initialize MCP client with registered servers"""
        self.servers = {
            "weather_service": WeatherServiceMCPServer(),
        }
    
    def call_tool(self, server: str, tool: str, arguments: dict) -> any:
        """
        Call an MCP tool on a registered server.
        
        Args:
            server: Name of the MCP server
            tool: Name of the tool to call
            arguments: Arguments for the tool
            
        Returns:
            Result from the MCP tool
        """
        if server not in self.servers:
            raise ValueError(f"MCP server '{server}' not found. Available: {list(self.servers.keys())}")
        
        return self.servers[server].call_tool(tool, arguments)
    
    def get_server(self, server: str):
        """Get a server instance for direct access to helper methods"""
        if server not in self.servers:
            raise ValueError(f"MCP server '{server}' not found")
        return self.servers[server]


# Global MCP client instance
_mcp_client = None

def get_mcp_client() -> MCPClient:
    """Get or create the global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client

