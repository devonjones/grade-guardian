-- Grade Guardian Database Initialization
-- PostgreSQL 15+ compatible

-- Create database extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Students table
CREATE TABLE students (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    grade_level INTEGER,
    school VARCHAR(200),
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Courses table
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    schoology_id VARCHAR(50),
    name VARCHAR(200) NOT NULL,
    teacher VARCHAR(100),
    semester VARCHAR(20),
    year INTEGER,
    active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(student_id, schoology_id, semester, year)
);

-- Assignments table  
CREATE TABLE assignments (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    course_id INTEGER REFERENCES courses(id) ON DELETE CASCADE,
    schoology_id VARCHAR(100),
    name VARCHAR(500) NOT NULL,
    category VARCHAR(50),
    category_weight DECIMAL(5,2),
    due_date TIMESTAMP,
    assigned_date TIMESTAMP,
    points_possible DECIMAL(10,2),
    can_be_resubmitted BOOLEAN DEFAULT false,
    extended_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(course_id, schoology_id)
);

-- Grade History table
CREATE TABLE grade_history (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    assignment_id INTEGER REFERENCES assignments(id) ON DELETE CASCADE,
    points_earned DECIMAL(10,2),
    percentage DECIMAL(5,2),
    status VARCHAR(50), -- missing|graded|pending|excused
    raw_display VARCHAR(100), -- What was actually displayed in Schoology
    is_current BOOLEAN DEFAULT true,
    recorded_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Reminders table
CREATE TABLE reminders (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    assignment_id INTEGER REFERENCES assignments(id) ON DELETE CASCADE,
    student_id INTEGER REFERENCES students(id) ON DELETE CASCADE,
    scheduled_for TIMESTAMP NOT NULL,
    sent_at TIMESTAMP,
    message_text TEXT,
    status VARCHAR(50) DEFAULT 'pending', -- pending|sent|failed|cancelled
    twilio_sid VARCHAR(100),
    failure_reason TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Parent Actions table
CREATE TABLE parent_actions (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    assignment_id INTEGER REFERENCES assignments(id) ON DELETE CASCADE,
    action_type VARCHAR(50) NOT NULL, -- excuse|ignore|prioritize|pause
    reason TEXT,
    expires_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- System Events table
CREATE TABLE system_events (
    id SERIAL PRIMARY KEY,
    uuid UUID DEFAULT uuid_generate_v4() UNIQUE NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) NOT NULL, -- info|warning|error|critical
    message TEXT NOT NULL,
    details JSONB,
    source VARCHAR(50), -- scraper|api|scheduler|etc
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_students_active ON students(active);
CREATE INDEX idx_courses_student_active ON courses(student_id, active);
CREATE INDEX idx_assignments_course ON assignments(course_id);
CREATE INDEX idx_grade_history_assignment_current ON grade_history(assignment_id, is_current);
CREATE INDEX idx_grade_history_recorded_at ON grade_history(recorded_at DESC);
CREATE INDEX idx_reminders_status_scheduled ON reminders(status, scheduled_for);
CREATE INDEX idx_reminders_student ON reminders(student_id);
CREATE INDEX idx_parent_actions_assignment ON parent_actions(assignment_id);
CREATE INDEX idx_system_events_created_at ON system_events(created_at DESC);
CREATE INDEX idx_system_events_severity ON system_events(severity);

-- Update triggers for updated_at fields
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_students_updated_at BEFORE UPDATE ON students FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_courses_updated_at BEFORE UPDATE ON courses FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_assignments_updated_at BEFORE UPDATE ON assignments FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_reminders_updated_at BEFORE UPDATE ON reminders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_parent_actions_updated_at BEFORE UPDATE ON parent_actions FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert initial test data
INSERT INTO students (name, phone, grade_level, school) VALUES 
('Test Student', '+1234567890', 7, 'Test School');

-- Log successful initialization
INSERT INTO system_events (event_type, severity, message, source) VALUES 
('database_init', 'info', 'Database schema initialized successfully', 'init_script');