"""Tests for configuration management."""

import os
from pathlib import Path

import yaml

from src.grade_guardian.config import AppConfig, DatabaseConfig, StudentConfig, load_config


class TestDatabaseConfig:
    """Test DatabaseConfig model."""

    def test_default_values(self):
        """Test default database configuration values."""
        config = DatabaseConfig()
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.name == "grade_monitor"
        assert config.user == "gradebot"

    def test_custom_values(self):
        """Test custom database configuration values."""
        config = DatabaseConfig(
            host="custom-host",
            port=3306,
            name="custom_db",
            user="custom_user",
            password="custom_pass",
        )
        assert config.host == "custom-host"
        assert config.port == 3306
        assert config.name == "custom_db"
        assert config.user == "custom_user"
        assert config.password == "custom_pass"


class TestStudentConfig:
    """Test StudentConfig model."""

    def test_student_config_creation(self):
        """Test student configuration creation."""
        student = StudentConfig(
            name="Test Student",
            phone="+1234567890",
            grade_level=7,
            school="Test School",
        )
        assert student.name == "Test Student"
        assert student.phone == "+1234567890"
        assert student.grade_level == 7
        assert student.school == "Test School"


class TestAppConfig:
    """Test AppConfig model."""

    def test_default_config(self):
        """Test default application configuration."""
        config = AppConfig()
        assert isinstance(config.database, DatabaseConfig)
        assert config.students == []
        assert config.dps is None
        assert config.data_dir == Path("data")
        assert config.scraped_dir == Path("data/scraped")
        assert config.config_dir == Path("config")

    def test_config_with_students(self):
        """Test configuration with student data."""
        students_data = [
            {
                "name": "Student 1",
                "phone": "+1111111111",
                "grade_level": 7,
                "school": "School 1",
            }
        ]
        config = AppConfig(students=students_data)
        assert len(config.students) == 1
        assert config.students[0].name == "Student 1"


class TestLoadConfig:
    """Test configuration loading functionality."""

    def test_load_config_with_missing_file(self, tmp_path):
        """Test loading config when file doesn't exist."""
        non_existent_path = tmp_path / "nonexistent.yaml"
        config = load_config(non_existent_path)
        assert isinstance(config, AppConfig)
        assert config.database.host == "localhost"

    def test_load_config_with_yaml_file(self, tmp_path):
        """Test loading config from YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_data = {
            "students": [
                {
                    "name": "Test Student",
                    "phone": "+1234567890",
                    "grade_level": 8,
                    "school": "Test Middle School",
                }
            ],
            "database": {"host": "test-host", "port": 3307, "name": "test_db"},
        }

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        config = load_config(config_file)
        assert len(config.students) == 1
        assert config.students[0].name == "Test Student"
        assert config.students[0].grade_level == 8
        assert config.database.host == "test-host"
        assert config.database.port == 3307

    def test_load_config_with_env_override(self, tmp_path):
        """Test environment variable override."""
        config_file = tmp_path / "test_config.yaml"
        config_data = {"database": {"host": "yaml-host", "port": 5432}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Set environment variables
        os.environ["DATABASE_HOST"] = "env-host"
        os.environ["DATABASE_PORT"] = "9999"

        try:
            config = load_config(config_file)
            assert config.database.host == "env-host"
            assert config.database.port == 9999
        finally:
            # Clean up environment
            os.environ.pop("DATABASE_HOST", None)
            os.environ.pop("DATABASE_PORT", None)

    def test_load_config_with_dps_credentials(self, tmp_path):
        """Test DPS credentials from environment."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump({}, f)

        os.environ["DPS_USERNAME"] = "test_user"
        os.environ["DPS_PASSWORD"] = "test_pass"

        try:
            config = load_config(config_file)
            assert config.dps is not None
            assert config.dps.username == "test_user"
            assert config.dps.password == "test_pass"
        finally:
            os.environ.pop("DPS_USERNAME", None)
            os.environ.pop("DPS_PASSWORD", None)
