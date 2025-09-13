"""Tests for CLI functionality."""

from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.grade_guardian.cli import cli


class TestCLI:
    """Test CLI commands."""

    @pytest.fixture
    def runner(self):
        """Create CLI test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_context(self):
        """Create mock CLI context."""
        mock_config = Mock()
        mock_config.data_dir.exists.return_value = True
        mock_config.scraped_dir.exists.return_value = True
        mock_config.scraped_dir.glob.return_value = []

        mock_db = Mock()
        mock_db.test_connection.return_value = True
        mock_db.get_health_status.return_value = {
            "status": "healthy",
            "stats": {
                "student_count": 1,
                "course_count": 2,
                "assignment_count": 5,
                "grade_history_count": 5,
                "reminder_count": 0,
            },
            "recent_errors": 0,
        }

        mock_processor = Mock()

        return {
            "config": mock_config,
            "db": mock_db,
            "processor": mock_processor,
        }

    @patch("src.grade_guardian.cli.load_config")
    @patch("src.grade_guardian.cli.DatabaseManager")
    @patch("src.grade_guardian.cli.GradeDataProcessor")
    def test_health_command_success(
        self, mock_processor_class, mock_db_class, mock_load_config, runner, mock_context
    ):
        """Test health command with successful database connection."""
        mock_load_config.return_value = mock_context["config"]
        mock_db_class.return_value = mock_context["db"]
        mock_processor_class.return_value = mock_context["processor"]

        result = runner.invoke(cli, ["health"])

        assert result.exit_code == 0
        assert "✅ Database connection: OK" in result.output
        assert "📊 Students: 1" in result.output

    @patch("src.grade_guardian.cli.load_config")
    def test_health_command_config_failure(self, mock_load_config, runner):
        """Test health command when configuration fails to load."""
        mock_load_config.side_effect = Exception("Config failed")

        result = runner.invoke(cli, ["health"])

        assert result.exit_code == 0
        assert "❌ Configuration failed to load" in result.output

    @patch("src.grade_guardian.cli.load_config")
    @patch("src.grade_guardian.cli.DatabaseManager")
    @patch("src.grade_guardian.cli.GradeDataProcessor")
    def test_health_command_db_failure(
        self, mock_processor_class, mock_db_class, mock_load_config, runner, mock_context
    ):
        """Test health command with database connection failure."""
        mock_load_config.return_value = mock_context["config"]
        mock_db = mock_context["db"]
        mock_db.test_connection.return_value = False
        mock_db_class.return_value = mock_db
        mock_processor_class.return_value = mock_context["processor"]

        result = runner.invoke(cli, ["health"])

        assert result.exit_code == 0
        assert "❌ Database connection: FAILED" in result.output

    @patch("src.grade_guardian.cli.load_config")
    @patch("src.grade_guardian.cli.DatabaseManager")
    @patch("src.grade_guardian.cli.GradeDataProcessor")
    @patch("src.grade_guardian.cli.create_sample_data")
    def test_test_scrape_command_sample_data(
        self,
        mock_create_sample,
        mock_processor_class,
        mock_db_class,
        mock_load_config,
        runner,
        mock_context,
    ):
        """Test test-scrape command with sample data generation."""
        mock_load_config.return_value = mock_context["config"]
        mock_db_class.return_value = mock_context["db"]
        mock_processor = mock_context["processor"]
        mock_processor_class.return_value = mock_processor

        # Mock sample data creation
        from pathlib import Path

        mock_file_path = Path("/tmp/test_file.json")
        mock_create_sample.return_value = mock_file_path

        # Mock processor results
        mock_processor.process_scraped_file.return_value = {
            "courses_processed": 2,
            "assignments_processed": 3,
            "new_assignments": 3,
            "grade_changes": 2,
            "errors": [],
        }

        result = runner.invoke(cli, ["test-scrape", "--student-name", "Test Student"])

        assert result.exit_code == 0
        assert "🔐 Simulating DPS authentication..." in result.output
        assert "✅ Scrape completed successfully!" in result.output
        assert "📊 Processing Results:" in result.output
