import React from 'react';
import './GanttChart.css';

function GanttChart({ projects, planningHorizon = 12 }) {
  if (!projects || projects.length === 0) {
    return <div className="gantt-empty">No projects scheduled</div>;
  }

  // Calculate the maximum week for scaling
  const maxWeek = Math.max(
    planningHorizon,
    ...projects.map(p => p.end_week || p.start_week || 0)
  );

  // Sort projects by priority
  const sortedProjects = [...projects].sort((a, b) => {
    const priorityA = a.display_priority || a.priority_rank || 999;
    const priorityB = b.display_priority || b.priority_rank || 999;
    return priorityA - priorityB;
  });

  // Calculate week width (percentage)
  const weekWidth = 100 / maxWeek;

  // Color palette for different projects
  const colors = [
    '#2563eb', // blue
    '#059669', // green
    '#dc2626', // red
    '#d97706', // orange
    '#7c3aed', // purple
    '#db2777', // pink
    '#0891b2', // cyan
    '#ca8a04', // yellow
  ];

  return (
    <div className="gantt-container">
      <div className="gantt-header">
        <div className="gantt-header-left">Project</div>
        <div className="gantt-header-right">
          <div className="gantt-week-labels">
            {Array.from({ length: maxWeek }, (_, i) => (
              <div key={i + 1} className="gantt-week-label" style={{ width: `${weekWidth}%` }}>
                W{i + 1}
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="gantt-body">
        {sortedProjects.map((project, index) => {
          const startWeek = project.start_week || 0;
          const endWeek = project.end_week || startWeek;
          const duration = endWeek - startWeek + 1;
          const leftOffset = ((startWeek - 1) / maxWeek) * 100;
          const width = (duration / maxWeek) * 100;
          const color = colors[index % colors.length];

          // Build tooltip with weather info
          let tooltipText = `${project.title}: Week ${startWeek} - Week ${endWeek} (${duration} weeks)`;
          if (project.weather_info) {
            tooltipText += `\nWeather: ${project.weather_info.adverse_days} adverse days (${project.weather_info.weather_risk} risk)`;
            if (project.weather_info.adverse_weather_weeks.length > 0) {
              tooltipText += `\nAdverse weeks: ${project.weather_info.adverse_weather_weeks.join(', ')}`;
            }
          }

          return (
            <div key={project.project_id} className="gantt-row">
              <div className="gantt-row-label">
                <div className="gantt-project-name" title={project.title}>
                  {project.title}
                </div>
                <div className="gantt-project-meta">
                  <span className="gantt-priority">P{project.display_priority || project.priority_rank || '?'}</span>
                  <span className="gantt-duration">{duration}w</span>
                  {project.is_outdoor && (
                    <span className="gantt-outdoor-badge" title="Outdoor project">🌤️</span>
                  )}
                </div>
              </div>
              <div className="gantt-row-bar-container">
                <div className="gantt-week-grid">
                  {Array.from({ length: maxWeek }, (_, i) => (
                    <div key={i + 1} className="gantt-week-cell" style={{ width: `${weekWidth}%` }} />
                  ))}
                </div>
                {startWeek > 0 && (
                  <div
                    className="gantt-bar"
                    style={{
                      left: `${leftOffset}%`,
                      width: `${width}%`,
                      backgroundColor: color,
                      border: project.weather_info && project.weather_info.adverse_days > 0 
                        ? '2px solid #ffa500' 
                        : 'none',
                    }}
                    title={tooltipText}
                  >
                    <div className="gantt-bar-label">
                      {project.title.length > 20 
                        ? project.title.substring(0, 20) + '...' 
                        : project.title}
                    </div>
                    {/* Weather indicator icon */}
                    {project.weather_info && project.weather_info.adverse_days > 0 && (
                      <div className="weather-indicator" title={`${project.weather_info.adverse_days} adverse weather days`}>
                        ⚠️
                      </div>
                    )}
                    {project.is_outdoor && project.weather_info && project.weather_info.adverse_days === 0 && (
                      <div className="weather-indicator" title="Weather OK for outdoor work">
                        ☀️
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      <div className="gantt-legend">
        <div className="gantt-legend-title">Legend:</div>
        <div className="gantt-legend-items">
          {sortedProjects.map((project, index) => (
            <div key={project.project_id} className="gantt-legend-item">
              <div
                className="gantt-legend-color"
                style={{ backgroundColor: colors[index % colors.length] }}
              />
              <span className="gantt-legend-text">
                P{project.display_priority || project.priority_rank || '?'}: {project.title}
                {project.weather_info && project.weather_info.adverse_days > 0 && ' ⚠️'}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default GanttChart;


