"""Database connection and operations for Grade Guardian."""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg.pool import ConnectionPool
from psycopg.rows import dict_row

from .config import AppConfig, get_database_url

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections and operations with connection pooling."""

    def __init__(self, config: AppConfig, pool_size: int = 10, max_size: int = 20):
        self.config = config
        self.connection_url = get_database_url(config)
        # Initialize connection pool for better performance
        self.pool = ConnectionPool(
            self.connection_url, min_size=2, max_size=pool_size, kwargs={"row_factory": dict_row}
        )
        logger.info(f"Database connection pool initialized with max_size={pool_size}")

    @contextmanager
    def get_connection(self) -> Generator[psycopg.Connection]:
        """Get a database connection from the pool with automatic cleanup."""
        conn = None
        try:
            conn = self.pool.getconn()
            conn.autocommit = False
            yield conn
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Database connection error: {e}")
            raise
        finally:
            if conn:
                self.pool.putconn(conn)

    def close_pool(self):
        """Close the connection pool. Should be called when shutting down the application."""
        if self.pool:
            self.pool.close()
            logger.info("Database connection pool closed")

    def test_connection(self) -> bool:
        """Test database connectivity."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                return result is not None
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False

    def get_health_status(self) -> dict[str, Any]:
        """Get database health information."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Test basic connectivity
                cursor.execute("SELECT 1")

                # Get database stats
                cursor.execute(
                    """
                    SELECT
                        (SELECT COUNT(*) FROM students) as student_count,
                        (SELECT COUNT(*) FROM courses) as course_count,
                        (SELECT COUNT(*) FROM assignments) as assignment_count,
                        (SELECT COUNT(*) FROM grade_history) as grade_history_count,
                        (SELECT COUNT(*) FROM reminders) as reminder_count
                """
                )
                stats = cursor.fetchone()

                # Get recent system events
                cursor.execute(
                    """
                    SELECT COUNT(*) as error_count
                    FROM system_events
                    WHERE severity IN ('error', 'critical')
                    AND created_at > NOW() - INTERVAL '24 hours'
                """
                )
                error_count = cursor.fetchone()["error_count"]

                return {
                    "status": "healthy",
                    "database": self.config.database.name,
                    "stats": stats,
                    "recent_errors": error_count,
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}

    def log_system_event(
        self,
        event_type: str,
        severity: str,
        message: str,
        details: dict | None = None,
        source: str = "api",
    ) -> None:
        """Log a system event to the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                import json as json_module

                details_json = json_module.dumps(details) if details else None
                cursor.execute(
                    """
                    INSERT INTO system_events (event_type, severity, message, details, source)
                    VALUES (%(event_type)s, %(severity)s, %(message)s, %(details)s, %(source)s)
                """,
                    {
                        "event_type": event_type,
                        "severity": severity,
                        "message": message,
                        "details": details_json,
                        "source": source,
                    },
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")

    def get_students(self, active_only: bool = True) -> list[dict[str, Any]]:
        """Get all students from the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                query = "SELECT * FROM students"
                params = {}

                if active_only:
                    query += " WHERE active = %(active)s"
                    params["active"] = True

                query += " ORDER BY name"
                cursor.execute(query, params)
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Failed to get students: {e}")
            return []

    def create_student(self, name: str, phone: str, grade_level: int, school: str) -> int | None:
        """Create a new student record."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO students (name, phone, grade_level, school)
                    VALUES (%(name)s, %(phone)s, %(grade_level)s, %(school)s)
                    RETURNING id
                """,
                    {"name": name, "phone": phone, "grade_level": grade_level, "school": school},
                )
                result = cursor.fetchone()
                conn.commit()
                return result["id"] if result else None
        except Exception as e:
            logger.error(f"Failed to create student: {e}")
            return None
