# Failure Cases and Fixes for Municipal Multi-Agent System

##  Critical Failure Cases

### 1. **LLM Agent Hallucinations/Wrong Decisions**

**Problem:**
- Agent approves projects exceeding budget
- Agent assigns invalid priority ranks
- Agent creates projects with impossible constraints

**Current State:**  Limited validation

**Fix:**
```python
# Added: municipal_agents/validation.py
# Validates all agent outputs before committing
```

**Implementation:**
- ✅ Budget constraint validation
- ✅ Priority rank validation
- ✅ Resource capacity validation
- ✅ Data type and range validation

---

### 2. **Budget Constraint Violations**

**Problem:**
- Total approved projects exceed budget
- Negative budget allocations
- Duplicate project approvals

**Current State:**  Basic check in `approve_project()` tool

**Fix:**
```python
# Use validation.validate_budget_allocation(context)
# Runs after Governance Agent completes
```

**Prevention:**
- Hard constraint in `approve_project()` tool (already exists)
- Post-processing validation (NEW)
- Transaction rollback on violation

---

### 3. **Resource Capacity Violations**

**Problem:**
- Schedule exceeds crew capacity
- Projects scheduled in impossible timeframes
- Resource overallocation

**Current State:** ⚠️ Basic greedy scheduler checks

**Fix:**
```python
# Use validation.validate_schedule_feasibility(context)
# Validates all scheduled tasks
```

**Prevention:**
- Capacity check before allocation (already exists)
- Post-scheduling validation (NEW)
- Automatic rescheduling on violation

---

### 4. **Database Integrity Issues**

**Problem:**
- Missing foreign keys
- Orphaned records
- Data corruption

**Current State:** ⚠️ Basic foreign key constraints

**Fix:**
```python
# Add database constraints:
# - Foreign key cascades
# - Check constraints for valid ranges
# - Unique constraints where needed
```

**Prevention:**
- Database transactions
- Foreign key constraints (already exists)
- Data validation before insert

---

### 5. **API/OpenAI Service Failures**

**Problem:**
- OpenAI API timeout
- Rate limiting
- Network failures
- Invalid API key

**Current State:** ⚠️ No retry logic

**Fix:**
```python
# Add retry logic with exponential backoff
import time
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def run_agent_with_retry(agent, prompt, context):
    return Runner.run(agent, prompt, context=context)
```

**Prevention:**
- Retry mechanism (NEW)
- Timeout handling
- Graceful degradation
- Error messages to user

---

## 🟡 Medium Priority Issues

### 6. **Invalid Input Data**

**Problem:**
- Negative budgets
- Missing required fields
- Invalid data types
- Malformed JSON

**Current State:** ✅ Basic validation in Flask API

**Fix:**
```python
# Enhanced input validation:
- Budget must be positive number
- Required fields checked
- Type validation
- Range validation
```

---

### 7. **Agent Timeout/Infinite Loops**

**Problem:**
- Agent takes too long
- Agent gets stuck in loop
- No progress indication

**Current State:** ⚠️ No timeout mechanism

**Fix:**
```python
# Add timeout wrapper:
import signal
from contextlib import contextmanager

@contextmanager
def timeout(seconds):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {seconds} seconds")
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(seconds)
    try:
        yield
    finally:
        signal.alarm(0)
```

---

### 8. **Concurrent Access Issues**

**Problem:**
- Multiple users running pipeline simultaneously
- Database locks
- Race conditions

**Current State:**  No locking mechanism

**Fix:**
```python
# Add file-based locking:
import fcntl
import os

class PipelineLock:
    def __init__(self, lock_file=".pipeline.lock"):
        self.lock_file = lock_file
    
    def __enter__(self):
        self.fd = open(self.lock_file, 'w')
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self
    
    def __exit__(self, *args):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        self.fd.close()
```

---

### 9. **Missing Data/Empty Results**

**Problem:**
- No issues in database
- No projects formed
- All projects rejected

**Current State:** ⚠️ Basic checks

**Fix:**
```python
# Add comprehensive checks:
- Minimum data requirements
- Meaningful error messages
- Suggestions for fixes
```

---

### 10. **UI/Backend Communication Failures**

**Problem:**
- CORS errors
- Network timeouts
- Malformed responses

**Current State:**  Basic error handling

**Fix:**
- Already implemented in React (try/catch)
- Add request timeout
- Add retry logic in frontend

---

## 🟢 Low Priority / Edge Cases

### 11. **Priority Rank Conflicts**

**Problem:**
- Duplicate priority ranks
- Missing priority ranks
- Non-sequential priorities

**Current State:** Fixed (sequential renumbering)

**Fix:**
- Already implemented in `app.py`

---

### 12. **Cost Estimation Errors**

**Problem:**
- Unrealistic cost estimates
- Missing cost data
- Cost doesn't match signals

**Current State:** No validation

**Fix:**
```python
# Add cost validation:
- Compare with issue_signals.estimated_cost
- Check for reasonable ranges
- Flag suspicious estimates
```

---

### 13. **Schedule Conflicts**

**Problem:**
- Projects scheduled simultaneously
- Resource overallocation
- Impossible timeframes

**Current State:**  Basic greedy scheduler

**Fix:**
- Upgrade to CP-SAT solver (mentioned in README)
- Add conflict detection
- Automatic conflict resolution

---

## 📋 Implementation Priority

### **Phase 1: Critical (Do First)**
1.  Budget validation (DONE - validation.py)
2.  Schedule feasibility validation (DONE - validation.py)
3. ⏳ Retry logic for API calls
4. ⏳ Input validation enhancement

### **Phase 2: Important (Do Next)**
5. ⏳ Timeout handling
6. ⏳ Concurrent access locking
7. ⏳ Better error messages
8. ⏳ Transaction rollback

### **Phase 3: Nice to Have**
9. ⏳ Cost estimation validation
10. ⏳ Advanced conflict resolution
11. ⏳ Performance monitoring
12. ⏳ Automated testing

---

## 🛠️ Quick Fixes You Can Apply Now

### 1. Add Validation to Pipeline

```python
# In app.py, after pipeline runs:
from municipal_agents.validation import validate_complete_pipeline, format_validation_report

validation_results = validate_complete_pipeline(context)
if has_critical_errors(validation_results):
    return jsonify({
        'success': False,
        'error': 'Validation failed',
        'validation_report': format_validation_report(validation_results)
    }), 400
```

### 2. Add Retry Logic

```bash
pip install tenacity
```

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def run_pipeline_with_retry(context):
    return asyncio.run(run_municipal_pipeline(context))
```

### 3. Add Timeout

```python
import signal

def run_with_timeout(func, timeout_seconds=300):
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Pipeline timed out after {timeout_seconds} seconds")
    
    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(timeout_seconds)
    try:
        result = func()
        signal.alarm(0)
        return result
    except TimeoutError:
        signal.alarm(0)
        raise
```

---

## 📊 Monitoring & Detection

### Add Logging:
```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler()
    ]
)
```

### Add Metrics:
- Track validation failures
- Monitor API call success rate
- Log execution times
- Track budget utilization

---

## ✅ Summary

**Current Protection Level:** 🟡 Medium
- Basic validation exists
- Some error handling
- Missing: retry logic, timeouts, comprehensive validation

**Recommended Next Steps:**
1. Integrate validation.py into pipeline
2. Add retry logic for API calls
3. Add timeout handling
4. Enhance error messages
5. Add monitoring/logging

**Risk Level:** 🟡 Medium Risk
- System works for normal cases
- Edge cases may cause failures
- LLM errors not fully prevented

