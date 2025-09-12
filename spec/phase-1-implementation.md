# Phase 1 Implementation Plan

## Overview
**Goal**: Establish core infrastructure and prove the scraping works  
**Deliverable**: Can manually scrape grades and store in database via CLI command

## Architecture Decisions

### Development Environment
- **PostgreSQL**: Docker container (isolated network)
- **Flask API**: Docker container with volume mounts for auto-reload
- **Playwright Scraper**: One-shot Docker container (not persistent)
- **Scheduling**: Ofelia in Portainer (external to compose stack)
- **Local Development**: Python 3.13 + uv already installed

### Data Flow (Phase 1)
1. Playwright scraper → JSON files → Manual CLI trigger → Flask processes JSON → PostgreSQL
2. CLI command `uv run grade-guardian --test-scrape` triggers the workflow

## Implementation Tasks

### 1. Database Setup
- [ ] Create `docker-compose.yml` with PostgreSQL service
- [ ] Create isolated Docker network for grade-guardian stack
- [ ] Define PostgreSQL environment variables and secrets
- [ ] Create database initialization SQL scripts
- [ ] Implement core tables from spec:
  - `students`
  - `courses` 
  - `assignments`
  - `grade_history`
  - `reminders`
  - `parent_actions`
  - `system_events`
- [ ] Test database connection from host using psycopg3

### 2. Python Project Structure
- [ ] Set up proper `src/grade_guardian/` package structure
- [ ] Configure `pyproject.toml` dependencies:
  - Flask
  - psycopg3 (PostgreSQL adapter)
  - pyyaml (config files)
  - click (CLI interface)
- [ ] Create database connection module (`src/grade_guardian/database.py`)
- [ ] Implement basic configuration loading (`src/grade_guardian/config.py`)
- [ ] Create CLI entry points (`src/grade_guardian/cli.py`)

### 3. Flask API Foundation  
- [ ] Create basic Flask app structure (`src/grade_guardian/api/`)
- [ ] Implement database connection pooling
- [ ] Create `/health` endpoint for Docker healthchecks
- [ ] Create basic error handling and logging
- [ ] Set up Flask development mode with auto-reload
- [ ] Configure Flask to work in Docker container with volume mounts

### 4. Playwright Scraper Prototype
- [ ] Create `scraper/` directory structure
- [ ] Set up Node.js project with `package.json`
- [ ] Install Playwright dependencies
- [ ] Create manual DPS portal login script (`scraper/dps_login.js`)
- [ ] Implement Duo authentication handling (manual approval initially)
- [ ] Create Schoology navigation script (`scraper/schoology_nav.js`)
- [ ] Implement single course grade scraping
- [ ] Output structured JSON to `data/scraped/` directory
- [ ] Create Dockerfile for one-shot scraper execution

### 5. Data Processing Pipeline
- [ ] Create JSON schema validation for scraped data
- [ ] Implement data transformation from scraper JSON to database schema
- [ ] Create database insertion logic for assignments/grades
- [ ] Add duplicate detection and data diffing
- [ ] Implement basic error handling and logging

### 6. Docker Integration
- [ ] Create multi-service `docker-compose.yml`:
  - PostgreSQL database
  - Flask API with volume mounts
  - Scraper service (one-shot execution)
- [ ] Configure Docker networking (isolated subnet)
- [ ] Set up environment variable management
- [ ] Create development vs production configurations
- [ ] Implement proper container health checks

### 7. CLI Interface
- [ ] Implement `--test-scrape` command:
  - Runs Playwright scraper container
  - Processes resulting JSON files
  - Stores data in database
  - Reports success/failure and data summary
- [ ] Add `--health` command for system status
- [ ] Add `--init-db` command for database setup
- [ ] Implement proper command-line argument parsing

### 8. Testing & Validation
- [ ] Create test configuration for DPS credentials (test mode)
- [ ] Verify complete scraper → database workflow
- [ ] Test Flask API endpoints work correctly
- [ ] Validate database schema with real scraped data
- [ ] Test Docker container startup and networking
- [ ] Verify CLI commands work as expected

## File Structure

```
grade-guardian/
├── docker-compose.yml
├── pyproject.toml
├── src/grade_guardian/
│   ├── __init__.py
│   ├── cli.py
│   ├── config.py
│   ├── database.py
│   └── api/
│       ├── __init__.py
│       └── app.py
├── scraper/
│   ├── package.json
│   ├── Dockerfile
│   ├── dps_login.js
│   └── schoology_scraper.js
├── data/
│   ├── scraped/      # JSON output from scraper
│   └── config/       # YAML configuration files
├── sql/
│   └── init.sql      # Database initialization
└── spec/
    ├── project-plan.md
    ├── dps-grade-monitor-spec.md
    └── phase-1-implementation.md (this file)
```

## Environment Configuration

### Docker Compose Environment
```yaml
# .env file for compose
POSTGRES_DB=grade_monitor
POSTGRES_USER=gradebot
POSTGRES_PASSWORD=secure_password
POSTGRES_PORT=5432
FLASK_ENV=development
FLASK_DEBUG=1
```

### Application Environment
```yaml
# data/config/config.yaml
database:
  host: "localhost"  # Will be postgres container name in compose
  port: 5432
  name: "grade_monitor"
  user: "gradebot"
  password: "${POSTGRES_PASSWORD}"

students:
  - name: "Test Student"
    phone: "+1234567890"
    grade_level: 7
    school: "Test School"

# DPS credentials (separate secure config)
dps:
  username: "${DPS_USERNAME}"
  password: "${DPS_PASSWORD}"
```

## Success Criteria

### Phase 1 Complete When:
- [ ] `docker-compose up` starts PostgreSQL successfully
- [ ] `uv run grade-guardian --health` reports all systems operational  
- [ ] `uv run grade-guardian --test-scrape` successfully:
  - Logs into DPS portal (with manual Duo approval)
  - Navigates to Schoology
  - Scrapes at least one course's assignments
  - Outputs valid JSON structure
  - Stores data in PostgreSQL
  - Reports summary of scraped assignments
- [ ] Can query database directly to see stored assignment data
- [ ] Flask `/health` endpoint responds correctly

### Data Validation
- [ ] At least 10 assignments scraped and stored
- [ ] All required fields populated in database
- [ ] No duplicate assignments created on re-run
- [ ] Grade history properly tracks changes over time

## Next Phase Preparation

### Ready for Phase 2 When:
- [ ] Scraper handles authentication reliably
- [ ] Database schema supports all required data
- [ ] Error handling provides useful debugging info
- [ ] Docker setup is reproducible and documented
- [ ] Configuration system is flexible and secure

### Technical Debt to Address in Phase 2:
- Playwright direct database integration (remove JSON intermediate step)
- Multiple student support
- Session persistence across scraper runs
- Comprehensive error handling and retry logic
- Production-ready logging and monitoring

## Risk Mitigation

### High-Risk Areas:
1. **DPS Authentication**: Keep sessions separate, handle MFA gracefully
2. **Schoology Structure**: Make selectors resilient, log HTML structure changes
3. **Docker Networking**: Test database connectivity thoroughly
4. **Data Consistency**: Implement proper transaction handling

### Fallback Plans:
- Manual JSON editing if scraper fails
- Database rollback procedures
- Local development without Docker if container issues
- Screenshot capture on scraper failures for debugging

## Timeline Estimate

### Week 1:
- Days 1-2: Database and Docker setup
- Days 3-4: Basic Flask API and CLI
- Days 5-7: Playwright scraper development

### Week 2:  
- Days 1-3: Integration and data pipeline
- Days 4-5: Testing and validation
- Days 6-7: Documentation and Phase 2 prep

**Total Duration**: 10-14 days
**Key Milestone**: Working end-to-end scrape by day 10