# Grade Guardian Project Plan

## Project Overview
Automated system to monitor student grades in Denver Public Schools (DPS) via Schoology and send SMS reminders for missing/improvable assignments.

## Development Phases

## Phase 1: Foundation & Manual Testing (Week 1-2)
**Goal**: Establish core infrastructure and prove the scraping works

### Database Setup
- [ ] Create PostgreSQL schema
- [ ] Set up Docker Compose with just postgres
- [ ] Create initial tables (students, courses, assignments, grade_history)
- [ ] Test database connections with psycopg3

### Playwright Scraper Prototype
- [ ] Set up Node.js project with Playwright
- [ ] Create manual login script for DPS portal
- [ ] Handle Duo authentication (manual approval)
- [ ] Navigate to Schoology successfully
- [ ] Scrape one course's grades manually
- [ ] Output JSON structure of scraped data

### Basic Flask API
- [ ] Set up Flask app structure
- [ ] Create database connection module
- [ ] Implement `/health` endpoint
- [ ] Create `/api/test/scrape` endpoint for manual testing

**Deliverable**: Can manually scrape grades and store in database

---

## Phase 2: Automated Scraping & Processing (Week 2-3)
**Goal**: Automate the full scraping flow for multiple students

### Complete Scraper Service
- [ ] Add REST API to scraper (Express)
- [ ] Handle multiple students
- [ ] Iterate through all courses
- [ ] Handle all assignment states (missing, graded, etc.)
- [ ] Add retry logic and error handling
- [ ] Session persistence between runs

### Grade Processing Logic
- [ ] Create GradeProcessor class
- [ ] Implement teacher pattern detection
- [ ] Build YAML config loader
- [ ] Create assignment comparison logic
- [ ] Track grade changes over time

### API Development
- [ ] Implement all `/api/grades/*` endpoints
- [ ] Create `/api/students/*` endpoints
- [ ] Add `/api/system/sync` endpoint
- [ ] Error handling and logging

**Deliverable**: Can trigger full sync via API and see grades in database

---

## Phase 3: Reminder System (Week 3-4)
**Goal**: Send SMS reminders based on missing work

### Reminder Engine
- [ ] Integrate Twilio SDK
- [ ] Create ReminderEngine class
- [ ] Build message generation logic
- [ ] Implement class schedule configuration
- [ ] Add reminder scheduling logic

### Configuration System
- [ ] Create main `config.yaml` structure
- [ ] Build teacher-specific config templates
- [ ] Add per-class makeup rules
- [ ] Implement reminder thresholds

### Manual Testing
- [ ] Test SMS sending
- [ ] Verify reminder timing logic
- [ ] Test combined messages for multiple assignments
- [ ] Validate phone number configuration

**Deliverable**: Can manually trigger reminders that send real SMS messages

---

## Phase 4: Scheduling & Automation (Week 4-5)
**Goal**: Fully automated daily operations

### Ofelia Integration
- [ ] Set up Ofelia container
- [ ] Create `ofelia.ini` configuration
- [ ] Test job execution in backend container
- [ ] Verify job overlap prevention

### Scheduled Scripts
- [ ] Create `daily_sync.py` script
- [ ] Create `send_reminders.py` script
- [ ] Add `parent_summary.py` for daily reports
- [ ] Implement `cleanup.py` for log rotation

### Testing & Monitoring
- [ ] Test full daily workflow
- [ ] Verify morning sync works
- [ ] Confirm reminders sent at correct times
- [ ] Check parent summary emails

**Deliverable**: System runs automatically every day without intervention

---

## Phase 5: Parent Dashboard (Week 5-6)
**Goal**: Web interface for monitoring and control

### React Frontend Setup
- [ ] Create React app structure
- [ ] Set up Material-UI or Ant Design
- [ ] Implement routing
- [ ] Create API service layer

### Core Dashboard Pages
- [ ] Dashboard overview page
- [ ] Student grades view
- [ ] Missing assignments list
- [ ] Reminder history log
- [ ] System status page

### Parent Controls
- [ ] Mark assignments as excused
- [ ] Pause reminders for N days
- [ ] Manual sync trigger
- [ ] Edit notification preferences

**Deliverable**: Functional web dashboard for parents

---

## Phase 6: Advanced Features (Week 6-7)
**Goal**: Enhance system with smart features

### Positive Reinforcement
- [ ] Detect grade improvements
- [ ] Send congratulations messages
- [ ] Track improvement trends
- [ ] Parent notifications for improvements

### Smart Detection
- [ ] Learn teacher patterns automatically
- [ ] Detect makeup opportunities
- [ ] End-of-semester pressure mode
- [ ] Extra credit detection

### Advanced Configuration
- [ ] Per-assignment type strategies
- [ ] School calendar integration
- [ ] Testing period detection
- [ ] Holiday/break handling

**Deliverable**: System adapts to patterns and provides intelligent reminders

---

## Phase 7: Polish & Production (Week 7-8)
**Goal**: Production-ready system

### Security & Reliability
- [ ] Implement secrets management
- [ ] Add authentication to dashboard
- [ ] Set up automated backups
- [ ] Add health checks for all services

### Monitoring & Alerts
- [ ] Set up error alerting
- [ ] Create system health dashboard
- [ ] Add performance monitoring
- [ ] Implement audit logging

### Documentation & Testing
- [ ] Write user documentation
- [ ] Create admin guide
- [ ] Add unit tests for critical paths
- [ ] Create disaster recovery plan

**Deliverable**: Production-ready, maintainable system

---

## Quick Wins Priority List

For immediate results, complete these milestones in order:

1. **Week 1**: Get Playwright scraping working manually
2. **Week 1**: Store scraped data in PostgreSQL  
3. **Week 2**: Send your first test SMS via Twilio
4. **Week 2**: Schedule first automated sync with Ofelia
5. **Week 3**: Send first real reminder to your daughter
6. **Week 4**: Deploy basic dashboard
7. **Week 5**: Full automation running daily

---

## Risk Mitigation

### High Risk Areas

#### DPS/Schoology Changes
- **Risk**: Website structure changes break scraper
- **Mitigation**: Keep scraper modular with clear separation of concerns
- **Contingency**: Manual fallback mode for critical reminders

#### Duo Authentication
- **Risk**: MFA requires manual intervention
- **Mitigation**: Investigate session persistence options
- **Contingency**: Accept manual approval for daily sync initially

#### SMS Delivery
- **Risk**: Messages blocked or rate limited
- **Mitigation**: Test thoroughly with Twilio guidelines
- **Contingency**: Email fallback for parent notifications

#### Teacher Patterns
- **Risk**: Inconsistent grading entry methods
- **Mitigation**: Start with manual rules per teacher
- **Contingency**: Conservative approach - remind for any possible missing work

---

## Development Guidelines

### Version Control Strategy
- Main branch for stable releases
- Feature branches for each phase
- Tag releases at phase completion

### Testing Strategy
- Manual testing for Phase 1-2
- Integration tests for Phase 3-4
- Full test suite by Phase 7

### Deployment Strategy
- Local development with Docker Compose
- Deploy to home server via Portainer
- Use environment variables for all secrets

---

## Success Metrics

### Phase 1-2 Success
- Successfully scrape all grades for one student
- Store 1 week of grade history in database

### Phase 3-4 Success  
- Send 10+ successful reminder SMS messages
- Achieve 95% uptime for daily sync

### Phase 5-6 Success
- Parent uses dashboard at least weekly
- 50% reduction in missing assignments

### Phase 7 Success
- 30 days without manual intervention
- Complete semester of grade tracking

---

## Timeline Summary

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| Phase 1: Foundation | 1-2 weeks | TBD | TBD | Not Started |
| Phase 2: Scraping | 1 week | TBD | TBD | Not Started |
| Phase 3: Reminders | 1 week | TBD | TBD | Not Started |
| Phase 4: Automation | 1 week | TBD | TBD | Not Started |
| Phase 5: Dashboard | 1-2 weeks | TBD | TBD | Not Started |
| Phase 6: Advanced | 1 week | TBD | TBD | Not Started |
| Phase 7: Production | 1 week | TBD | TBD | Not Started |

**Total Duration**: 7-8 weeks

---

## Notes

### Development Environment
- Python 3.13.7 with uv for dependency management
- Node.js 22.18.0 for Playwright scraper
- PostgreSQL 15 for data storage
- Docker & Portainer for deployment

### Key Technologies
- Flask for Python API
- Playwright for web scraping
- React for dashboard
- Twilio for SMS
- Ofelia for job scheduling

### Repository Structure
```
grade-guardian/
├── PROJECT_PLAN.md (this file)
├── spec/dps-grade-monitor-spec.md
├── src/grade_guardian/
├── scraper/
├── frontend/
├── config/
└── docker-compose.yaml
```

---

## Getting Started

1. Review the full specification in `spec/dps-grade-monitor-spec.md`
2. Set up development environment with Python 3.13.7 and Node 22.18.0
3. Create `.env` file from `.env.example`
4. Start with Phase 1 tasks
5. Check off tasks as completed
6. Update status and dates in timeline

---

*Last Updated: [Current Date]*
*Version: 1.0.0*