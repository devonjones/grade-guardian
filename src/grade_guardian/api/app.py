"""Flask API application for Grade Guardian."""

import logging
from datetime import datetime

from flask import Flask, jsonify, request

from ..config import load_config
from ..database import DatabaseManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__)

    # Load configuration
    try:
        config = load_config()
        db = DatabaseManager(config)

        # Store in app context
        app.config["GRADE_GUARDIAN_CONFIG"] = config
        app.config["DATABASE_MANAGER"] = db

        logger.info("Configuration loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        config = None
        db = None

    @app.before_request
    def check_database():
        """Check database availability before processing any request."""
        if request.endpoint not in ["health"]:  # Allow health check even if DB is down
            if not db:
                return jsonify({"error": "Database not available"}), 500

    @app.route("/health")
    def health():
        """Health check endpoint."""
        try:
            if not db:
                return jsonify(
                    {"status": "unhealthy", "error": "Database manager not initialized"}
                ), 500

            # Test database connection
            if db.test_connection():
                health_info = db.get_health_status()
                return jsonify(
                    {
                        "status": "healthy",
                        "timestamp": datetime.now().isoformat(),
                        "database": health_info,
                        "version": "0.1.0",
                    }
                )
            else:
                return jsonify(
                    {
                        "status": "unhealthy",
                        "error": "Database connection failed",
                        "timestamp": datetime.now().isoformat(),
                    }
                ), 500

        except Exception as e:
            logger.error(f"Health check error: {e}")
            return jsonify(
                {"status": "unhealthy", "error": str(e), "timestamp": datetime.now().isoformat()}
            ), 500

    @app.route("/api/students")
    def get_students():
        """Get all students."""
        try:
            students = db.get_students()
            return jsonify({"students": students, "count": len(students)})

        except Exception as e:
            logger.error(f"Error getting students: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/students", methods=["POST"])
    def create_student():
        """Create a new student."""
        try:
            data = request.get_json()
            if not data:
                return jsonify({"error": "No JSON data provided"}), 400

            required_fields = ["name", "phone", "grade_level", "school"]
            for field in required_fields:
                if field not in data:
                    return jsonify({"error": f"Missing required field: {field}"}), 400

            student_id = db.create_student(
                name=data["name"],
                phone=data["phone"],
                grade_level=data["grade_level"],
                school=data["school"],
            )

            if student_id:
                return jsonify(
                    {"message": "Student created successfully", "student_id": student_id}
                ), 201
            else:
                return jsonify({"error": "Failed to create student"}), 500

        except Exception as e:
            logger.error(f"Error creating student: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/system/status")
    def system_status():
        """Get detailed system status."""
        try:
            if not config:
                return jsonify(
                    {"status": "error", "error": "Configuration not properly initialized"}
                ), 500

            # Get database status
            db_health = db.get_health_status()

            # Check data directories
            data_status = {
                "data_dir_exists": config.data_dir.exists(),
                "scraped_dir_exists": config.scraped_dir.exists(),
                "config_dir_exists": config.config_dir.exists(),
                "scraped_files": len(list(config.scraped_dir.glob("*.json")))
                if config.scraped_dir.exists()
                else 0,
            }

            return jsonify(
                {
                    "status": "ok",
                    "timestamp": datetime.now().isoformat(),
                    "database": db_health,
                    "data_directories": data_status,
                    "configuration": {
                        "students_configured": len(config.students),
                        "dps_configured": config.dps is not None,
                    },
                }
            )

        except Exception as e:
            logger.error(f"System status error: {e}")
            return jsonify(
                {"status": "error", "error": str(e), "timestamp": datetime.now().isoformat()}
            ), 500

    @app.route("/api/scraped-data")
    def get_scraped_data():
        """Get list of scraped data files."""
        try:
            scraped_files = []
            if config.scraped_dir.exists():
                for file_path in config.scraped_dir.glob("*.json"):
                    try:
                        stat = file_path.stat()
                        scraped_files.append(
                            {
                                "filename": file_path.name,
                                "size": stat.st_size,
                                "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                                "path": str(file_path),
                            }
                        )
                    except Exception as e:
                        logger.warning(f"Error reading file {file_path}: {e}")

            # Sort by modification time (newest first)
            scraped_files.sort(key=lambda x: x["modified"], reverse=True)

            return jsonify(
                {
                    "scraped_files": scraped_files,
                    "count": len(scraped_files),
                    "scraped_dir": str(config.scraped_dir),
                }
            )

        except Exception as e:
            logger.error(f"Error getting scraped data: {e}")
            return jsonify({"error": str(e)}), 500

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return app


# For development
app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
