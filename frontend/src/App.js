import React, { useState } from 'react';
import axios from 'axios';
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
                  <h2>Approved Projects Details</h2>
                  <div className="projects-grid">
                    {results.approved_projects.map((project) => (
                      <div key={project.project_id} className="project-card approved">
                        <div className="project-header">
                          <h3>{project.title}</h3>
                          <span className="priority-badge">Priority #{project.display_priority || project.priority_rank}</span>
                        </div>
                        <div className="project-details">
                          <div className="detail-row">
                            <span className="detail-label">Category:</span>
                            <span className="detail-value">{project.category || 'N/A'}</span>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Allocated Budget:</span>
                            <span className="detail-value highlight">{formatCurrency(project.allocated_budget)}</span>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Duration:</span>
                            <span className="detail-value">{project.estimated_weeks} weeks</span>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Crew Type:</span>
                            <span className="detail-value">{project.required_crew_type.replace('_', ' ')}</span>
                          </div>
                          <div className="detail-row">
                            <span className="detail-label">Crew Size:</span>
                            <span className="detail-value">{project.crew_size} units</span>
                          </div>
                          {project.start_week && (
                            <div className="detail-row">
                              <span className="detail-label">Schedule:</span>
                              <span className="detail-value">Week {project.start_week} - Week {project.end_week}</span>
                            </div>
                          )}
                          <div className="detail-row">
                            <span className="detail-label">Risk Score:</span>
                            <span className="detail-value">{project.risk_score}</span>
                          </div>
                        </div>
                      </div>
                    ))}
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

