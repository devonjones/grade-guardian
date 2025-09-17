"""Tests for database operations."""

from unittest.mock import Mock, patch

import pytest

from src.grade_guardian.config import AppConfig, DatabaseConfig
from src.grade_guardian.database import DatabaseManager


class TestDatabaseManager:
    """Test DatabaseManager class."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            name="test_db",
            user="test_user",
            password="test_pass",
        )
        config = AppConfig(database=db_config)
        return config

    @patch("src.grade_guardian.database.ConnectionPool")
    def test_database_manager_init(self, mock_pool, mock_config):
        """Test DatabaseManager initialization."""
        db_manager = DatabaseManager(mock_config)

        assert db_manager.config == mock_config
        assert (
            db_manager.connection_url == "postgresql://test_user:test_pass@localhost:5432/test_db"
        )
        mock_pool.assert_called_once()

    @patch("src.grade_guardian.database.ConnectionPool")
    def test_database_manager_custom_pool_size(self, mock_pool, mock_config):
        """Test DatabaseManager with custom pool size."""
        DatabaseManager(mock_config, pool_size=20)

        mock_pool.assert_called_once()

    def test_get_database_url(self, mock_config):
        """Test database URL generation."""
        from src.grade_guardian.config import get_database_url

        url = get_database_url(mock_config)
        expected = "postgresql://test_user:test_pass@localhost:5432/test_db"
        assert url == expected

    @patch("src.grade_guardian.database.ConnectionPool")
    def test_close_pool(self, mock_pool, mock_config):
        """Test connection pool closure."""
        db_manager = DatabaseManager(mock_config)
        mock_pool_instance = mock_pool.return_value

        db_manager.close_pool()
        mock_pool_instance.close.assert_called_once()

    @patch("src.grade_guardian.database.ConnectionPool")
    def test_test_connection_success(self, mock_pool, mock_config):
        """Test successful database connection test."""
        db_manager = DatabaseManager(mock_config)

        # Mock successful connection
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = {"result": 1}
        mock_conn.cursor.return_value = mock_cursor

        mock_pool_instance = mock_pool.return_value
        mock_pool_instance.getconn.return_value = mock_conn

        result = db_manager.test_connection()
        assert result is True

    @patch("src.grade_guardian.database.ConnectionPool")
    def test_test_connection_failure(self, mock_pool, mock_config):
        """Test failed database connection test."""
        db_manager = DatabaseManager(mock_config)

        # Mock connection failure
        mock_pool_instance = mock_pool.return_value
        mock_pool_instance.getconn.side_effect = Exception("Connection failed")

        result = db_manager.test_connection()
        assert result is False
