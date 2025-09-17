"""Tests for data processing pipeline."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, MagicMock

import pytest

from src.grade_guardian.config import AppConfig
from src.grade_guardian.processor import GradeDataProcessor


class TestGradeDataProcessor:
    """Test GradeDataProcessor class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        return AppConfig()

    @pytest.fixture
    def mock_db(self):
        """Create a mock database manager."""
        return Mock()

    @pytest.fixture
    def processor(self, mock_config, mock_db):
        """Create a processor instance for testing."""
        return GradeDataProcessor(mock_config, mock_db)

    def test_validate_scraped_data_valid(self, processor):
        """Test validation with valid scraped data."""
        valid_data = {
            "scrape_timestamp": "2024-01-01T12:00:00Z",
            "student": "Test Student",
            "courses": [
                {
                    "name": "Test Course",
                    "assignments": [{"name": "Test Assignment", "status": "missing"}],
                }
            ],
        }

        result = processor.validate_scraped_data(valid_data)
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_validate_scraped_data_missing_fields(self, processor):
        """Test validation with missing required fields."""
        invalid_data = {"student": "Test Student"}

        result = processor.validate_scraped_data(invalid_data)
        assert result["valid"] is False
        assert "Missing required field: scrape_timestamp" in result["errors"]
        assert "Missing required field: courses" in result["errors"]

    def test_validate_course_data_missing_assignments(self, processor):
        """Test course validation with missing assignments."""
        course_data = {"name": "Test Course"}

        errors = processor.validate_course_data(course_data, 0)
        assert "Course 0: Missing required field 'assignments'" in errors

    def test_validate_assignment_data_missing_status(self, processor):
        """Test assignment validation with missing status."""
        assignment_data = {"name": "Test Assignment"}

        errors = processor.validate_assignment_data(assignment_data, 0, 0)
        assert "Course 0, Assignment 0: Missing required field 'status'" in errors

    def test_process_scraped_file_with_valid_data(self, processor, mock_db):
        """Test processing a valid scraped JSON file."""
        # Create temporary JSON file
        valid_data = {
            "scrape_timestamp": "2024-01-01T12:00:00Z",
            "student": "Test Student",
            "courses": [
                {
                    "schoology_id": "12345",
                    "name": "Test Course",
                    "teacher": "Test Teacher",
                    "assignments": [
                        {
                            "schoology_id": "assign_001",
                            "name": "Test Assignment",
                            "status": "missing",
                            "points_possible": 100,
                        }
                    ],
                }
            ],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(valid_data, f)
            temp_path = Path(f.name)

        try:
            # Mock database operations
            mock_conn = Mock()
            mock_cursor = Mock()
            mock_conn.cursor.return_value = mock_cursor
            
            # Mock the context manager properly using MagicMock for magic methods
            mock_context = MagicMock()
            mock_context.__enter__.return_value = mock_conn
            mock_context.__exit__.return_value = None
            mock_db.get_connection.return_value = mock_context

            # Mock the cursor-based methods
            processor.find_or_create_student_with_cursor = Mock(return_value=1)
            processor.process_course_with_cursor = Mock(
                return_value={
                    "assignments_processed": 1,
                    "new_assignments": 1,
                    "updated_assignments": 0,
                    "grade_changes": 1,
                }
            )

            result = processor.process_scraped_file(temp_path)

            assert result["student_name"] == "Test Student"
            assert result["courses_processed"] == 1
            assert result["assignments_processed"] == 1
            assert len(result["errors"]) == 0

        finally:
            # Clean up
            temp_path.unlink()

    def test_process_scraped_file_with_invalid_data(self, processor):
        """Test processing an invalid scraped JSON file."""
        invalid_data = {"invalid": "data"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(invalid_data, f)
            temp_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Invalid data format"):
                processor.process_scraped_file(temp_path)
        finally:
            temp_path.unlink()
