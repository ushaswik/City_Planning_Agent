# Municipal Multi-Agent System - Web UI

A professional web interface for the Municipal Corporation Multi-Agent Project Management System.

## Features

- **Budget Input**: Enter quarterly budget to analyze municipal projects
- **Pipeline Execution**: Automatically runs the 3-agent pipeline (Formation → Governance → Scheduling)
- **Detailed Results**: View comprehensive project details including:
  - Projects formed, approved, and scheduled
  - Budget allocation and remaining funds
  - Individual project details (cost, duration, crew, schedule)
  - Approval rationale for each project

## Setup Instructions

### 1. Install Python Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # On Mac/Linux
# or: venv\Scripts\activate  # On Windows

# Install Flask and Flask-CORS
pip install flask flask-cors
```

### 2. Install React Dependencies

```bash
cd frontend
npm install
```

### 3. Set Up Environment Variables

Make sure your `.env` file (or `api.env`) contains:
```
OPENAI_API_KEY=your-api-key-here
```

### 4. Run the Application

**Terminal 1 - Start Flask Backend:**
```bash
# From project root
python app.py
```
The Flask server will run on `http://localhost:5000`

**Terminal 2 - Start React Frontend:**
```bash
cd frontend
npm start
```
The React app will run on `http://localhost:3000`

### 5. Access the Application

Open your browser and navigate to:
```
http://localhost:3000
```

## Usage

1. Enter the quarterly budget (e.g., `75000000` or `75,000,000`)
2. Click "Run Pipeline Analysis"
3. Wait for the pipeline to complete (this may take 1-2 minutes)
4. View the results:
   - Summary statistics
   - Detailed approved project information
   - Rejected projects (if any)

## API Endpoints

- `POST /api/run-pipeline` - Run the pipeline with a budget
  - Body: `{ "budget": 75000000 }`
  - Returns: Complete pipeline results with project details

- `POST /api/init-db` - Initialize database with sample data

- `GET /api/health` - Health check endpoint

## Project Structure

```
city_gov/
├── app.py                 # Flask backend API
├── frontend/
│   ├── src/
│   │   ├── App.js        # Main React component
│   │   ├── App.css       # Styling
│   │   └── index.js      # React entry point
│   └── package.json      # React dependencies
└── municipal_agents/      # Core pipeline logic
```

## Troubleshooting

**Backend not starting:**
- Check if port 5000 is available
- Ensure all Python dependencies are installed
- Verify OPENAI_API_KEY is set

**Frontend not connecting:**
- Ensure Flask backend is running on port 5000
- Check browser console for CORS errors
- Verify proxy setting in `package.json`

**Pipeline errors:**
- Ensure database is initialized: `python run_pipeline.py --init`
- Check OpenAI API key is valid
- Review backend logs for detailed error messages

