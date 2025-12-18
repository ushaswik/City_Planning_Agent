import React, { useState } from 'react';
import axios from 'axios';
import GanttChart from './GanttChart';
import './App.css';

function App() {
  const [budget, setBudget] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(amount);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const response = await axios.post('/api/run-pipeline', {
        budget: parseFloat(budget.replace(/[,$]/g, '')),
      });

      if (response.data.success) {
        setResults(response.data);
      } else {
        setError(response.data.error || 'An error occurred');
      }
    } catch (err) {
      setError(err.response?.data?.error || err.message || 'Failed to run pipeline');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="App">
      <header className="app-header">
        <div className="header-content">
          <div className="logo-section">
            <h1>Municipal Corporation</h1>
            <p className="subtitle">Multi-Agent Project Management System</p>
          </div>
        </div>
      </header>

      <main className="main-content">
        <div className="container">
          <div className="input-section">
            <div className="card">
              <h2>Quarterly Budget Allocation</h2>
              <p className="card-description">
                Enter the quarterly budget to generate a comprehensive planning report with project allocations and scheduling.
              </p>
              
              <form onSubmit={handleSubmit} className="budget-form">
                <div className="form-group">
                  <label htmlFor="budget">Quarterly Budget (USD)</label>
                  <input
                    type="text"
                    id="budget"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                    placeholder="75,000,000"
                    disabled={loading}
                    required
                  />
                </div>
                <button type="submit" className="btn-primary" disabled={loading}>
                  {loading ? 'Generating Planning Report...' : 'Generate Planning Report'}
                </button>
              </form>
            </div>
          </div>

          {error && (
            <div className="error-message">
              <strong>Error:</strong> {error}
            </div>
          )}

          {results && (
            <div className="results-section">
              <div className="summary-card">
                <h2>Pipeline Results Summary</h2>
                <div className="summary-grid">
                  <div className="summary-item">
                    <div className="summary-label">Projects Formed</div>
                    <div className="summary-value">{results.summary.projects_formed}</div>
                  </div>
                  <div className="summary-item">
                    <div className="summary-label">Projects Approved</div>
                    <div className="summary-value">{results.summary.projects_approved}</div>
                  </div>
                  <div className="summary-item">
                    <div className="summary-label">Tasks Scheduled</div>
                    <div className="summary-value">{results.summary.tasks_scheduled}</div>
                  </div>
                  <div className="summary-item highlight">
                    <div className="summary-label">Total Budget Allocated</div>
                    <div className="summary-value">{formatCurrency(results.summary.total_budget_allocated)}</div>
                  </div>
                  <div className="summary-item highlight">
                    <div className="summary-label">Budget Remaining</div>
                    <div className="summary-value">{formatCurrency(results.summary.budget_remaining)}</div>
                  </div>
                </div>
              </div>

              {results.approved_projects && results.approved_projects.length > 0 && (
                <div className="projects-section">
                  <h2>Project Schedule - Gantt Chart</h2>
                  <GanttChart 
                    projects={results.approved_projects.filter(p => p.start_week && p.end_week)} 
                    planningHorizon={12}
                  />
                </div>
              )}

              {/* Weather Summary Card */}
              {results.approved_projects && results.approved_projects.some(p => p.scheduled && p.is_outdoor) && (
                <div className="weather-summary-card">
                  <h2>Weather Considerations</h2>
                  <div className="weather-projects">
                    {results.approved_projects
                      .filter(p => p.scheduled && p.is_outdoor)
                      .map((project) => (
                        <div key={project.project_id} className="weather-project-item">
                          <div className="weather-project-header">
                            <span className="weather-project-name">{project.title}</span>
                            {project.weather_info && (
                              <span className={`weather-badge ${project.weather_info.weather_risk}`}>
                                {project.weather_info.weather_risk.toUpperCase()}
                              </span>
                            )}
                          </div>
                          {project.weather_info && (
                            <div className="weather-details">
                              <span>
                                Scheduled: Week {project.start_week}-{project.end_week}
                              </span>
                              <span>
                                Adverse Days: {project.weather_info.adverse_days}
                                {project.weather_info.adverse_weather_weeks.length > 0 && (
                                  ` (Weeks ${project.weather_info.adverse_weather_weeks.join(', ')})`
                                )}
                              </span>
                            </div>
                          )}
                          {project.weather_info && project.weather_info.recommendation && (
                            <div className="weather-recommendation-text">
                              {project.weather_info.recommendation}
                            </div>
                          )}
                        </div>
                      ))}
                  </div>
                  <div className="weather-note">
                    ℹ️ Outdoor projects are automatically rescheduled to avoid weeks with 
                    more than 2 adverse weather days.
                  </div>
                </div>
              )}

              {results.rejected_projects && results.rejected_projects.length > 0 && (
                <div className="projects-section">
                  <h2>Rejected Projects</h2>
                  <div className="projects-grid">
                    {results.rejected_projects.map((project) => (
                      <div key={project.project_id} className="project-card rejected">
                        <div className="project-header">
                          <h3>{project.title}</h3>
                          <span className="status-badge rejected">REJECTED</span>
                        </div>
                        <div className="project-details">
                          <div className="detail-row">
                            <span className="detail-label">Estimated Cost:</span>
                            <span className="detail-value">{formatCurrency(project.estimated_cost)}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <footer className="app-footer">
        <p>&copy; 2025 Municipal Corporation. All rights reserved.</p>
      </footer>
    </div>
  );
}

export default App;

