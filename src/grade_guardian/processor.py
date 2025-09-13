"""Data processing pipeline for scraped grade data."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
from dateutil import parser as date_parser

from .database import DatabaseManager
from .config import AppConfig

logger = logging.getLogger(__name__)

class GradeDataProcessor:
    """Processes scraped grade data and stores it in the database."""
    
    def __init__(self, config: AppConfig, db: DatabaseManager):
        self.config = config
        self.db = db
    
    def process_scraped_file(self, json_file_path: Path) -> Dict[str, Any]:
        """Process a single scraped JSON file with proper transaction management."""
        try:
            logger.info(f"Processing scraped file: {json_file_path}")
            
            # Load JSON data
            with open(json_file_path, 'r') as f:
                data = json.load(f)
            
            # Validate data structure
            validation_result = self.validate_scraped_data(data)
            if not validation_result['valid']:
                raise ValueError(f"Invalid data format: {validation_result['errors']}")
            
            # Process all data within a single transaction for consistency
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Process the data
                processing_result = {
                    'file': str(json_file_path),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'student_name': data.get('student', 'Unknown'),
                    'courses_processed': 0,
                    'assignments_processed': 0,
                    'new_assignments': 0,
                    'updated_assignments': 0,
                    'grade_changes': 0,
                    'errors': []
                }
                
                # Find or create student
                student_id = self.find_or_create_student_with_cursor(cursor, data.get('student', 'Unknown'))
                if not student_id:
                    raise ValueError("Failed to create or find student record")
                
                # Process each course
                for course_data in data.get('courses', []):
                    try:
                        course_result = self.process_course_with_cursor(cursor, student_id, course_data)
                        processing_result['courses_processed'] += 1
                        processing_result['assignments_processed'] += course_result['assignments_processed']
                        processing_result['new_assignments'] += course_result['new_assignments']
                        processing_result['updated_assignments'] += course_result['updated_assignments']
                        processing_result['grade_changes'] += course_result['grade_changes']
                        
                    except Exception as e:
                        error_msg = f"Error processing course {course_data.get('name', 'Unknown')}: {str(e)}"
                        logger.error(error_msg)
                        processing_result['errors'].append(error_msg)
                        # Don't raise here to allow partial processing if needed
                
                # Commit the entire transaction
                conn.commit()
                
                # Log processing result (outside transaction to avoid nested connections)
                self.db.log_system_event(
                    event_type="data_processing_completed",
                    severity="info",
                    message=f"Processed {processing_result['courses_processed']} courses, {processing_result['assignments_processed']} assignments",
                    details=processing_result,
                    source="processor"
                )
                
                logger.info(f"Processing completed: {processing_result}")
                return processing_result
            
        except Exception as e:
            error_msg = f"Failed to process file {json_file_path}: {str(e)}"
            logger.error(error_msg)
            
            self.db.log_system_event(
                event_type="data_processing_failed",
                severity="error",
                message=error_msg,
                details={'file': str(json_file_path)},
                source="processor"
            )
            
            raise
    
    def validate_scraped_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the structure of scraped data."""
        errors = []
        
        # Check required top-level fields
        required_fields = ['scrape_timestamp', 'student', 'courses']
        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Validate courses structure
        if 'courses' in data:
            if not isinstance(data['courses'], list):
                errors.append("'courses' must be a list")
            else:
                for i, course in enumerate(data['courses']):
                    course_errors = self.validate_course_data(course, i)
                    errors.extend(course_errors)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
    
    def validate_course_data(self, course: Dict[str, Any], course_index: int) -> List[str]:
        """Validate course data structure."""
        errors = []
        prefix = f"Course {course_index}"
        
        required_fields = ['name', 'assignments']
        for field in required_fields:
            if field not in course:
                errors.append(f"{prefix}: Missing required field '{field}'")
        
        # Validate assignments
        if 'assignments' in course:
            if not isinstance(course['assignments'], list):
                errors.append(f"{prefix}: 'assignments' must be a list")
            else:
                for j, assignment in enumerate(course['assignments']):
                    assignment_errors = self.validate_assignment_data(assignment, course_index, j)
                    errors.extend(assignment_errors)
        
        return errors
    
    def validate_assignment_data(self, assignment: Dict[str, Any], course_index: int, assignment_index: int) -> List[str]:
        """Validate assignment data structure."""
        errors = []
        prefix = f"Course {course_index}, Assignment {assignment_index}"
        
        required_fields = ['name', 'status']
        for field in required_fields:
            if field not in assignment:
                errors.append(f"{prefix}: Missing required field '{field}'")
        
        return errors
    
    def find_or_create_student(self, student_name: str) -> Optional[int]:
        """Find existing student or create new one (legacy method for backward compatibility)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            result = self.find_or_create_student_with_cursor(cursor, student_name)
            conn.commit()
            return result
    
    def find_or_create_student_with_cursor(self, cursor, student_name: str) -> Optional[int]:
        """Find existing student or create new one using provided cursor."""
        try:
            # First, try to find existing student
            cursor.execute("SELECT id, name FROM students WHERE active = true")
            students = cursor.fetchall()
            
            for student in students:
                if student['name'].strip().lower() == student_name.strip().lower():
                    return student['id']
            
            # If not found, try to get student details from config
            student_config = None
            for student in self.config.students:
                if student.name.strip().lower() == student_name.strip().lower():
                    student_config = student
                    break
            
            if student_config:
                phone = student_config.phone
                grade_level = student_config.grade_level
                school = student_config.school
            else:
                # Fallback to defaults if not in config (should be rare)
                logger.warning(f"Student {student_name} not found in config, using defaults")
                phone = "+1234567890"
                grade_level = 7
                school = "DPS School"
            
            cursor.execute("""
                INSERT INTO students (name, phone, grade_level, school)
                VALUES (%(name)s, %(phone)s, %(grade_level)s, %(school)s)
                RETURNING id
            """, {
                "name": student_name,
                "phone": phone,
                "grade_level": grade_level,
                "school": school
            })
            
            result = cursor.fetchone()
            student_id = result['id'] if result else None
            
            if student_id:
                logger.info(f"Created new student: {student_name} (ID: {student_id})")
            
            return student_id
            
        except Exception as e:
            logger.error(f"Error finding/creating student {student_name}: {e}")
            return None
    
    def process_course(self, student_id: int, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single course and its assignments (legacy method)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            result = self.process_course_with_cursor(cursor, student_id, course_data)
            conn.commit()
            return result
    
    def process_course_with_cursor(self, cursor, student_id: int, course_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single course and its assignments using provided cursor."""
        result = {
            'assignments_processed': 0,
            'new_assignments': 0,
            'updated_assignments': 0,
            'grade_changes': 0
        }
        
        # Find or create course
        course_id = self.find_or_create_course_with_cursor(cursor, student_id, course_data)
        if not course_id:
            raise ValueError(f"Failed to create course: {course_data.get('name', 'Unknown')}")
        
        # Process assignments
        for assignment_data in course_data.get('assignments', []):
            try:
                assignment_result = self.process_assignment_with_cursor(cursor, course_id, assignment_data)
                result['assignments_processed'] += 1
                
                if assignment_result['is_new']:
                    result['new_assignments'] += 1
                else:
                    result['updated_assignments'] += 1
                
                if assignment_result['grade_changed']:
                    result['grade_changes'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing assignment {assignment_data.get('name', 'Unknown')}: {e}")
                raise
        
        return result
    
    def find_or_create_course(self, student_id: int, course_data: Dict[str, Any]) -> Optional[int]:
        """Find existing course or create new one (legacy method)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            result = self.find_or_create_course_with_cursor(cursor, student_id, course_data)
            conn.commit()
            return result
    
    def find_or_create_course_with_cursor(self, cursor, student_id: int, course_data: Dict[str, Any]) -> Optional[int]:
        """Find existing course or create new one using provided cursor."""
        try:
            # Try to find existing course
            cursor.execute("""
                SELECT id FROM courses 
                WHERE student_id = %(student_id)s 
                AND (schoology_id = %(schoology_id)s OR name = %(name)s)
                AND active = true
            """, {
                'student_id': student_id,
                'schoology_id': course_data.get('schoology_id'),
                'name': course_data.get('name')
            })
            
            existing = cursor.fetchone()
            if existing:
                return existing['id']
            
            # Create new course
            cursor.execute("""
                INSERT INTO courses (student_id, schoology_id, name, teacher, semester, year)
                VALUES (%(student_id)s, %(schoology_id)s, %(name)s, %(teacher)s, %(semester)s, %(year)s)
                RETURNING id
            """, {
                'student_id': student_id,
                'schoology_id': course_data.get('schoology_id'),
                'name': course_data.get('name'),
                'teacher': course_data.get('teacher'),
                'semester': course_data.get('semester', 'Current'),
                'year': datetime.now().year
            })
            
            result = cursor.fetchone()
            
            if result:
                logger.info(f"Created new course: {course_data.get('name')} (ID: {result['id']})")
                return result['id']
            
        except Exception as e:
            logger.error(f"Error finding/creating course {course_data.get('name', 'Unknown')}: {e}")
            
        return None
    
    def process_assignment(self, course_id: int, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single assignment and its grade history (legacy method)."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            result = self.process_assignment_with_cursor(cursor, course_id, assignment_data)
            conn.commit()
            return result
    
    def process_assignment_with_cursor(self, cursor, course_id: int, assignment_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single assignment and its grade history using provided cursor."""
        try:
            # Find or create assignment
            assignment_result = self.find_or_create_assignment_with_cursor(cursor, course_id, assignment_data)
            if not assignment_result:
                raise ValueError("Failed to create assignment")
            
            assignment_id, is_new = assignment_result
            
            # Process grade history
            grade_changed = self.process_grade_history_with_cursor(cursor, assignment_id, assignment_data)
            
            return {
                'is_new': is_new,
                'grade_changed': grade_changed
            }
                
        except Exception as e:
            logger.error(f"Error processing assignment {assignment_data.get('name', 'Unknown')}: {e}")
            raise
    
    def find_or_create_assignment(self, cursor, course_id: int, assignment_data: Dict[str, Any]) -> Optional[int]:
        """Find existing assignment or create new one (legacy method)."""
        result = self.find_or_create_assignment_with_cursor(cursor, course_id, assignment_data)
        return result[0] if result else None
    
    def find_or_create_assignment_with_cursor(self, cursor, course_id: int, assignment_data: Dict[str, Any]) -> Optional[tuple[int, bool]]:
        """Find existing assignment or create new one, returns (id, is_new)."""
        try:
            # Try to find existing assignment
            cursor.execute("""
                SELECT id FROM assignments 
                WHERE course_id = %(course_id)s 
                AND (schoology_id = %(schoology_id)s OR name = %(name)s)
            """, {
                'course_id': course_id,
                'schoology_id': assignment_data.get('schoology_id'),
                'name': assignment_data.get('name')
            })
            
            existing = cursor.fetchone()
            if existing:
                return existing['id'], False  # Found existing, not new
            
            # Parse dates
            due_date = None
            assigned_date = None
            
            if assignment_data.get('due_date'):
                try:
                    due_date = date_parser.parse(assignment_data['due_date'])
                except Exception as e:
                    logger.warning(f"Failed to parse due_date: {e}")
            
            if assignment_data.get('assigned_date'):
                try:
                    assigned_date = date_parser.parse(assignment_data['assigned_date'])
                except Exception as e:
                    logger.warning(f"Failed to parse assigned_date: {e}")
            
            # Create new assignment
            cursor.execute("""
                INSERT INTO assignments (
                    course_id, schoology_id, name, category, category_weight,
                    due_date, assigned_date, points_possible, can_be_resubmitted
                )
                VALUES (
                    %(course_id)s, %(schoology_id)s, %(name)s, %(category)s, %(category_weight)s,
                    %(due_date)s, %(assigned_date)s, %(points_possible)s, %(can_be_resubmitted)s
                )
                RETURNING id
            """, {
                'course_id': course_id,
                'schoology_id': assignment_data.get('schoology_id'),
                'name': assignment_data.get('name'),
                'category': assignment_data.get('category'),
                'category_weight': assignment_data.get('category_weight'),
                'due_date': due_date,
                'assigned_date': assigned_date,
                'points_possible': assignment_data.get('points_possible'),
                'can_be_resubmitted': assignment_data.get('can_be_resubmitted', False)
            })
            
            result = cursor.fetchone()
            return (result['id'], True) if result else None  # Created new
            
        except Exception as e:
            logger.error(f"Error finding/creating assignment: {e}")
            return None
    
    def process_grade_history(self, cursor, assignment_id: int, assignment_data: Dict[str, Any]) -> bool:
        """Process grade history for an assignment (legacy method)."""
        return self.process_grade_history_with_cursor(cursor, assignment_id, assignment_data)
    
    def process_grade_history_with_cursor(self, cursor, assignment_id: int, assignment_data: Dict[str, Any]) -> bool:
        """Process grade history for an assignment using provided cursor."""
        try:
            # Get current grade status
            points_earned = assignment_data.get('points_earned')
            percentage = assignment_data.get('grade_percentage')
            status = assignment_data.get('status', 'unknown')
            raw_display = assignment_data.get('raw_display', '')
            
            # Check if this grade already exists
            cursor.execute("""
                SELECT id FROM grade_history 
                WHERE assignment_id = %(assignment_id)s 
                AND is_current = true
                AND points_earned IS NOT DISTINCT FROM %(points_earned)s
                AND status = %(status)s
            """, {
                'assignment_id': assignment_id,
                'points_earned': points_earned,
                'status': status
            })
            
            existing = cursor.fetchone()
            if existing:
                return False  # No change
            
            # Mark previous grades as not current
            cursor.execute("""
                UPDATE grade_history 
                SET is_current = false 
                WHERE assignment_id = %(assignment_id)s AND is_current = true
            """, {'assignment_id': assignment_id})
            
            # Insert new grade record
            cursor.execute("""
                INSERT INTO grade_history (
                    assignment_id, points_earned, percentage, status, raw_display, is_current
                )
                VALUES (%(assignment_id)s, %(points_earned)s, %(percentage)s, %(status)s, %(raw_display)s, true)
            """, {
                'assignment_id': assignment_id,
                'points_earned': points_earned,
                'percentage': percentage,
                'status': status,
                'raw_display': raw_display
            })
            
            return True  # Grade changed
            
        except Exception as e:
            logger.error(f"Error processing grade history: {e}")
            return False