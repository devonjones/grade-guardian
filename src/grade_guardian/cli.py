"""Command Line Interface for Grade Guardian."""

import datetime
import json
import logging
import subprocess
from pathlib import Path

import click

from .config import create_default_config, load_config
from .database import DatabaseManager
from .processor import GradeDataProcessor

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@click.group()
@click.pass_context
def cli(ctx):
    """Grade Guardian - Automated grade monitoring for DPS/Schoology."""
    ctx.ensure_object(dict)

    # Load configuration
    try:
        config = load_config()
        db = DatabaseManager(config)
        processor = GradeDataProcessor(config, db)

        ctx.obj["config"] = config
        ctx.obj["db"] = db
        ctx.obj["processor"] = processor
    except Exception as e:
        logger.error(f"Failed to load configuration: {e}")
        ctx.obj["config"] = None
        ctx.obj["db"] = None
        ctx.obj["processor"] = None


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health status."""
    config = ctx.obj.get("config")
    db = ctx.obj.get("db")

    if not config or not db:
        click.echo("❌ Configuration failed to load")
        return

    click.echo("🏥 Grade Guardian Health Check")
    click.echo("=" * 40)

    # Test database connection
    if db.test_connection():
        click.echo("✅ Database connection: OK")

        # Get detailed health info
        health_info = db.get_health_status()
        if health_info.get("status") == "healthy":
            stats = health_info["stats"]
            click.echo(f"📊 Students: {stats['student_count']}")
            click.echo(f"📚 Courses: {stats['course_count']}")
            click.echo(f"📝 Assignments: {stats['assignment_count']}")
            click.echo(f"📈 Grade History: {stats['grade_history_count']}")
            click.echo(f"💬 Reminders: {stats['reminder_count']}")
            click.echo(f"🚨 Recent Errors: {health_info['recent_errors']}")
        else:
            click.echo(f"⚠️  Database health: {health_info.get('error', 'Unknown error')}")
    else:
        click.echo("❌ Database connection: FAILED")

    # Check data directories
    if config.data_dir.exists():
        click.echo("✅ Data directory: OK")
    else:
        click.echo("❌ Data directory: Missing")

    if config.scraped_dir.exists():
        click.echo("✅ Scraped data directory: OK")
    else:
        click.echo("❌ Scraped data directory: Missing")

    # Check for scraped data
    scraped_files = list(config.scraped_dir.glob("*.json"))
    click.echo(f"📄 Scraped files: {len(scraped_files)}")


@cli.command()
@click.option("--student-name", help="Scrape data for specific student only")
@click.option("--output-dir", help="Directory to save scraped JSON files")
@click.option(
    "--run-scraper",
    is_flag=True,
    help="Run actual Playwright scraper instead of generating sample data",
)
@click.pass_context
def test_scrape(ctx, student_name: str | None, output_dir: str | None, run_scraper: bool):
    """Run a test scrape of DPS/Schoology data (generates sample data by default, use --run-scraper for real scraping)."""
    config = ctx.obj.get("config")
    db = ctx.obj.get("db")
    processor = ctx.obj.get("processor")

    if not config or not db:
        click.echo("❌ Configuration failed to load")
        return

    if not processor:
        click.echo("❌ Data processor not available")
        return

    click.echo("🕸️  Starting test scrape...")
    click.echo("=" * 40)

    # Set output directory
    output_path = Path(output_dir) if output_dir else config.scraped_dir

    output_path.mkdir(parents=True, exist_ok=True)

    # Log the attempt
    db.log_system_event(
        event_type="scrape_started",
        severity="info",
        message=f"Manual test scrape initiated for student: {student_name or 'all'}",
        source="cli",
    )

    try:
        if run_scraper:
            # Run scraper via Docker
            click.echo("🐳 Running Playwright scraper in Docker...")
            output_file = run_docker_scraper(output_path, student_name)
        else:
            # Create sample data for testing
            output_file = create_sample_data(output_path, student_name)

        if not output_file:
            raise Exception("No scraper output generated")

        click.echo("✅ Scrape completed successfully!")
        click.echo(f"📄 Data saved to: {output_file}")

        # Process the scraped data
        click.echo("\n🔄 Processing scraped data...")
        processing_result = processor.process_scraped_file(output_file)

        click.echo("📊 Processing Results:")
        click.echo(f"   - Courses processed: {processing_result['courses_processed']}")
        click.echo(f"   - Assignments processed: {processing_result['assignments_processed']}")
        click.echo(f"   - New assignments: {processing_result['new_assignments']}")
        click.echo(f"   - Grade changes: {processing_result['grade_changes']}")

        if processing_result["errors"]:
            click.echo(f"⚠️  Errors encountered: {len(processing_result['errors'])}")
            for error in processing_result["errors"][:3]:  # Show first 3 errors
                click.echo(f"   - {error}")

        # Log success
        db.log_system_event(
            event_type="scrape_completed",
            severity="info",
            message=f"Test scrape completed successfully. Processed {processing_result['assignments_processed']} assignments",
            details=processing_result,
            source="cli",
        )

    except Exception as e:
        click.echo(f"❌ Scrape failed: {e}")
        logger.error(f"Scrape error: {e}")

        # Log failure
        db.log_system_event(
            event_type="scrape_failed",
            severity="error",
            message=f"Test scrape failed: {str(e)}",
            source="cli",
        )


def run_docker_scraper(output_path: Path, student_name: str | None) -> Path | None:
    """Run the Playwright scraper using Docker Compose."""
    try:
        # Build the scraper container if needed
        click.echo("🔨 Building scraper container...")
        subprocess.run(["docker-compose", "build", "scraper"], check=True, capture_output=True)

        # Run the scraper
        click.echo("🚀 Running scraper container...")
        cmd = ["docker-compose", "run", "--rm", "scraper"]

        if student_name:
            cmd.append(f"--student={student_name}")

        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Find the most recent scraped file
        scraped_files = list(output_path.glob("*.json"))
        if scraped_files:
            return max(scraped_files, key=lambda x: x.stat().st_mtime)

        return None

    except subprocess.CalledProcessError as e:
        logger.error(f"Docker scraper failed: {e.stderr}")
        raise Exception(f"Docker scraper failed: {e.stderr}") from e


def create_sample_data(output_path: Path, student_name: str | None) -> Path:
    """Create sample scraped data for testing."""
    click.echo("🔐 Simulating DPS authentication...")
    click.echo("🏫 Simulating Schoology navigation...")
    click.echo("📚 Creating sample course data...")

    sample_data = {
        "scrape_timestamp": datetime.datetime.now().isoformat(),
        "student": student_name or "Test Student",
        "courses": [
            {
                "schoology_id": "12345",
                "name": "7th Grade Language Arts",
                "teacher": "Ms. Johnson",
                "semester": "Fall 2024",
                "assignments": [
                    {
                        "schoology_id": "assign_001",
                        "name": "Essay on Romeo and Juliet",
                        "category": "work_product",
                        "category_weight": 55,
                        "due_date": "2024-12-15T23:59:00Z",
                        "assigned_date": "2024-12-01T08:00:00Z",
                        "points_possible": 100,
                        "points_earned": None,
                        "status": "missing",
                        "raw_display": "Missing",
                        "can_be_resubmitted": True,
                    },
                    {
                        "schoology_id": "assign_002",
                        "name": "Vocabulary Quiz Chapter 5",
                        "category": "process",
                        "category_weight": 35,
                        "due_date": "2024-12-10T23:59:00Z",
                        "assigned_date": "2024-12-03T08:00:00Z",
                        "points_possible": 50,
                        "points_earned": 42,
                        "status": "graded",
                        "raw_display": "42",
                        "can_be_resubmitted": False,
                    },
                ],
            },
            {
                "schoology_id": "67890",
                "name": "7th Grade Math",
                "teacher": "Mr. Smith",
                "semester": "Fall 2024",
                "assignments": [
                    {
                        "schoology_id": "assign_003",
                        "name": "Algebra Practice Set 3",
                        "category": "work_product",
                        "category_weight": 55,
                        "due_date": "2024-12-12T23:59:00Z",
                        "assigned_date": "2024-12-05T08:00:00Z",
                        "points_possible": 75,
                        "points_earned": 0,
                        "status": "missing",
                        "raw_display": "0",
                        "can_be_resubmitted": True,
                    }
                ],
            },
        ],
    }

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = output_path / f"scrape_{student_name or 'test'}_{timestamp}.json"
    with open(output_file, "w") as f:
        json.dump(sample_data, f, indent=2)

    return output_file


@cli.command()
@click.pass_context
def init_db(ctx):
    """Initialize the database with default configuration."""
    db = ctx.obj.get("db")

    if not db:
        click.echo("❌ Database connection not available")
        return

    click.echo("🗃️  Initializing database...")

    if db.test_connection():
        click.echo("✅ Database connection successful")
        click.echo("📊 Database already initialized (tables exist)")

        # Show current stats
        health_info = db.get_health_status()
        if health_info.get("status") == "healthy":
            stats = health_info["stats"]
            click.echo(
                f"Current data: {stats['student_count']} students, {stats['assignment_count']} assignments"
            )
    else:
        click.echo("❌ Database connection failed")


@cli.command()
@click.option("--config-path", help="Path to create config file")
@click.pass_context
def create_config(ctx, config_path: str | None):
    """Create a default configuration file."""
    path = Path(config_path) if config_path else Path("config/config.yaml")

    if path.exists():
        click.confirm(f"Config file {path} already exists. Overwrite?", abort=True)

    create_default_config(path)
    click.echo(f"✅ Created default configuration at {path}")
    click.echo("📝 Edit the file to add your DPS credentials and student information")


def main():
    """Main entry point for the CLI."""
    cli()
