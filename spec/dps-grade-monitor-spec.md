# DPS Grade Monitor and Reminder System Specification

## Overview
Automated system to monitor student grades in Denver Public Schools (DPS) via Schoology and send SMS reminders for missing/improvable assignments via Twilio to help students with ADHD stay on track.

## System Architecture

### Core Components
- **Playwright-based Web Scraper**: Node.js script that automates login through DPS portal and Schoology
- **Python Core Application**: Main business logic, database operations, and orchestration
- **PostgreSQL Database**: Stores historical grades, assignments, reminders sent
- **Twilio Integration**: Python SDK for sending SMS reminders to student devices
- **Parent Dashboard**: Python web UI (FastAPI/Flask) for monitoring and configuration
- **Docker Container**: Multi-stage deployment for Python and Node.js
- **Scheduler**: Python-based scheduling (APScheduler) or cron for nightly batch processing

### Technology Stack
- **Primary Runtime**: Python 3.13
- **Web Automation**: Playwright (via Node.js subprocess)
- **Database**: PostgreSQL (psycopg3)
- **SMS Service**: Twilio API (Python SDK)
- **Web Framework**: FastAPI or Flask
- **Task Queue**: Celery with Redis (optional)
- **Container**: Docker
- **Configuration**: YAML files (pyyaml)

## Authentication Flow

### DPS Portal Login
1. Navigate to https://portal.dpsk12.org/
2. Enter username/password (stored securely)
3. Handle Duo MFA (manual approval initially, explore automation)
4. Select appropriate student from dropdown
5. Navigate to "See All Apps" → Schoology tile
6. Complete Google authentication
7. Maintain session state for reuse

### Error Handling
- Detect authentication failures
- Send SMS alert to parent phone on auth failure
- Log all authentication attempts
- Implement retry logic with backoff

## Data Extraction

### Schoology Navigation
1. Click "Courses" dropdown
2. Iterate through each course
3. Click "Grades" section for each course
4. Extract all assignment data

### Assignment Data Structure
```yaml
assignment:
  course_name: string
  course_id: string
  teacher_name: string
  assignment_name: string
  category: process|work_product|final
  category_weight: number (35|55|10)
  due_date: datetime
  assigned_date: datetime
  points_possible: number
  points_earned: number|null
  status: missing|graded|pending
  grade_percentage: number|null
  can_be_resubmitted: boolean
  extended_time: datetime|null
```

### Teacher Pattern Detection
- Store raw score display per teacher
- Learn patterns: "Missing", "0", blank, "-"
- Apply teacher-specific rules from config

## Configuration System

### Global Configuration
```yaml
# config.yaml
students:
  - name: "Aurelia"
    phone: "+1XXXXXXXXXX"
    grade_level: 7
    school: "Denver School of Arts MS"
  - name: "Anastasia"
    phone: "+1XXXXXXXXXX"
    grade_level: 3
    school: "Willow Elementary"

parent:
  phone: "+1XXXXXXXXXX"
  email: "parent@example.com"

school_calendar:
  holidays: []
  early_release_days: []
  testing_periods: []

notification_settings:
  before_class_minutes: 5
  after_class_start_minutes: -5  # 5 min before class ends
  max_reminders_per_assignment: 3
  reminder_cooldown_days: 1

database:
  host: "localhost"
  port: 5432
  name: "grade_monitor"

twilio:
  account_sid: "XXXX"
  auth_token: "XXXX"
  from_phone: "+1XXXXXXXXXX"
```

### Per-Class Configuration
```yaml
# classes/7th_grade_language_arts.yaml
course_id: "01018"
teacher: "Teacher Name"
schedule:
  monday: "08:30"
  tuesday: "09:45"
  wednesday: "08:30"
  thursday: "09:45"
  friday: "08:30"

grading:
  categories:
    process: 35
    work_product: 55
    final: 10

makeup_rules:
  enabled: true
  window_days: 14
  max_improvement_score: 80
  minimum_original_score: 0
  eligible_if_below: 80

patterns:
  missing_indicators: ["Missing", "M", "0", ""]
  excused_indicators: ["E", "Excused"]

reminder_rules:
  enabled: true
  priority: high  # high|medium|low
  include_extra_credit: false
  reminder_threshold: 80  # Remind if score below this
```

## Database Schema

### Tables

```sql
-- Students
CREATE TABLE students (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100),
  phone VARCHAR(20),
  grade_level INTEGER,
  school VARCHAR(200),
  active BOOLEAN DEFAULT true
);

-- Courses
CREATE TABLE courses (
  id SERIAL PRIMARY KEY,
  student_id INTEGER REFERENCES students(id),
  schoology_id VARCHAR(50),
  name VARCHAR(200),
  teacher VARCHAR(100),
  semester VARCHAR(20),
  year INTEGER
);

-- Assignments
CREATE TABLE assignments (
  id SERIAL PRIMARY KEY,
  course_id INTEGER REFERENCES courses(id),
  schoology_id VARCHAR(100),
  name VARCHAR(500),
  category VARCHAR(50),
  due_date TIMESTAMP,
  assigned_date TIMESTAMP,
  points_possible DECIMAL(10,2),
  created_at TIMESTAMP DEFAULT NOW()
);

-- Grade History
CREATE TABLE grade_history (
  id SERIAL PRIMARY KEY,
  assignment_id INTEGER REFERENCES assignments(id),
  points_earned DECIMAL(10,2),
  percentage DECIMAL(5,2),
  status VARCHAR(50),
  recorded_at TIMESTAMP DEFAULT NOW(),
  is_current BOOLEAN DEFAULT true
);

-- Reminders
CREATE TABLE reminders (
  id SERIAL PRIMARY KEY,
  assignment_id INTEGER REFERENCES assignments(id),
  student_id INTEGER REFERENCES students(id),
  scheduled_for TIMESTAMP,
  sent_at TIMESTAMP,
  message_text TEXT,
  status VARCHAR(50), -- pending|sent|failed|cancelled
  twilio_sid VARCHAR(100)
);

-- Parent Actions
CREATE TABLE parent_actions (
  id SERIAL PRIMARY KEY,
  assignment_id INTEGER REFERENCES assignments(id),
  action_type VARCHAR(50), -- excuse|ignore|prioritize
  reason TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

-- System Events
CREATE TABLE system_events (
  id SERIAL PRIMARY KEY,
  event_type VARCHAR(100),
  severity VARCHAR(20),
  message TEXT,
  details JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);
```

## Reminder Logic

### Detection Rules
1. Check all assignments for each student
2. Identify improvable assignments:
   - Status = "Missing" OR
   - Score below teacher-configured threshold OR
   - Score = 0 OR null OR blank
   - Within makeup window per teacher rules

### Message Generation
```python
def generate_reminder_message(assignments, student, class_time):
    if len(assignments) == 1:
        return (f"Hi {student.name}! Class starts in 5 min. "
                f"Please turn in: {assignments[0].name} for {assignments[0].course}")
    else:
        items = ', '.join(f"{a.name} ({a.course})" for a in assignments)
        return f"Hi {student.name}! You have {len(assignments)} items to turn in: {items}"
```

### Positive Reinforcement
- Detect grade improvements (comparing current to previous in grade_history)
- Send congratulations message when assignment turned in
- Track improvement trends

## Parent Dashboard

### Features
- **Current Overview**: Display all current grades by class
- **Missing Work**: List all assignments needing attention
- **Reminder History**: Log of all sent reminders
- **Grade Trends**: Charts showing grade changes over time
- **System Status**: Last sync time, auth status, errors

### Pages
1. **Dashboard** - Summary view with alerts
2. **Students** - Manage student profiles
3. **Courses** - View/edit course configurations
4. **Assignments** - Detailed assignment list with actions
5. **Reminders** - History and scheduling
6. **Settings** - System configuration
7. **Calendar** - School calendar with pause periods

### Controls
- Mark assignment as excused/ignored
- Manually trigger reminder
- Pause reminders for N days
- Edit teacher configurations
- Test mode toggle

## Operational Modes

### Test Mode
- Scrape and process all data
- Generate reminders but don't send
- Log would-be messages to dashboard
- Send test summary to parent email

### Production Mode
- Full automation with SMS sending
- Error alerts to parent
- Automatic retry on failures

### Maintenance Mode
- Pause all operations
- Display maintenance message on dashboard
- Queue reminders for later

## Scheduling

### Daily Batch Job (Cron)
```cron
# Run at 2 AM Mountain Time daily
0 2 * * * /app/grade-monitor/run.sh
```

### Processing Steps
1. Authenticate to DPS/Schoology
2. Scrape all courses for all active students
3. Compare to previous data
4. Generate reminders based on class schedules
5. Schedule SMS sends via Twilio
6. Send parent summary email
7. Update dashboard data

## Error Handling & Monitoring

### Alert Triggers
- Authentication failure (3 retries then alert)
- Schoology structure change detected
- Database connection failure
- Twilio API errors
- No data extracted (possible site change)

### Logging
- All scraping attempts
- Authentication events
- Grade changes detected
- Reminders generated/sent
- Parent dashboard access
- System errors

### Recovery
- Automatic retry with exponential backoff
- Session persistence across runs
- Transaction rollback on partial failure
- Manual intervention alerts

## Security Considerations

### Credentials
- Environment variables for sensitive data
- Encrypted storage for passwords
- Twilio credentials in env vars
- No auth on dashboard (internal network only)

### Data Privacy
- Student data remains local
- No external APIs except Twilio
- PostgreSQL access restricted to container
- Regular backup of database

## Future Enhancements

### Phase 2
- Multi-district support
- Email reminders in addition to SMS
- Integration with Google Calendar for school closures
- Advanced analytics on grade patterns
- Teacher communication templates

### Phase 3
- Mobile app for parents
- Student self-service portal
- Predictive alerts based on patterns
- Integration with other school systems
- Natural language configuration via LLM

## Development Priorities

### MVP (Phase 1)
1. Basic scraper with Playwright
2. PostgreSQL setup with core tables
3. Simple reminder logic
4. Twilio integration
5. Basic web dashboard
6. Docker deployment

### Testing Strategy
- Unit tests for reminder logic
- Integration tests for scraping
- Mock Twilio in test mode
- Snapshot testing for UI
- Load testing for database

## Deployment

### Docker Configuration
```dockerfile
# Multi-stage build for Python and Node.js
FROM python:3.13-slim as python-base

# Install Node.js for Playwright
RUN apt-get update && apt-get install -y \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_22.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g playwright \
    && playwright install-deps \
    && playwright install chromium

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml .
RUN pip install uv && uv sync

# Copy application code
COPY . .

# Set up Playwright scripts
COPY scraper/ ./scraper/

CMD ["python", "-m", "grade_guardian"]
```

### Environment Setup
```bash
# .env file
PYTHON_ENV=production
DB_HOST=postgres
DB_PORT=5432
DB_NAME=grade_monitor
DB_USER=gradebot
DB_PASSWORD=secure_password
TWILIO_ACCOUNT_SID=xxx
TWILIO_AUTH_TOKEN=xxx
TWILIO_FROM_PHONE=+1xxx
PARENT_PHONE=+1xxx
PLAYWRIGHT_SCRIPT_PATH=./scraper/dps_scraper.js
```

## Success Metrics

- Reduction in missing assignments
- Improvement in end-of-semester grades
- Consistent reminder delivery
- System uptime >99%
- Parent satisfaction with visibility

## Support & Maintenance

- Daily monitoring of system health
- Weekly review of reminder effectiveness
- Monthly update of teacher patterns
- Semester archival of historical data
- Annual review of system architecture
