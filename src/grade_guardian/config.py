"""Configuration management for Grade Guardian."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()


class DatabaseConfig(BaseModel):
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    name: str = Field(default="grade_monitor")
    user: str = Field(default="gradebot")
    password: str | None = Field(default=None)


class StudentConfig(BaseModel):
    name: str
    phone: str
    grade_level: int
    school: str


class DPSConfig(BaseModel):
    username: str
    password: str
    base_url: str = Field(default="https://portal.dpsk12.org/")


class AppConfig(BaseModel):
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    students: list[StudentConfig] = Field(default_factory=list)
    dps: DPSConfig | None = None
    data_dir: Path = Field(default=Path("data"))
    scraped_dir: Path = Field(default=Path("data/scraped"))
    config_dir: Path = Field(default=Path("config"))

    def __init__(self, **data):
        super().__init__(**data)
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.scraped_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load configuration from YAML file and environment variables."""

    if config_path is None:
        config_path = Path("config/config.yaml")

    # Start with defaults
    config_data = {}

    # Load from YAML file if it exists
    if config_path.exists():
        with open(config_path) as f:
            config_data = yaml.safe_load(f) or {}

    # Override with environment variables
    # When running in Docker, DATABASE_HOST will be set to 'postgres'
    # When running locally, we need to connect via the exposed Docker network
    default_host = "localhost" if os.getenv("DATABASE_HOST") is None else os.getenv("DATABASE_HOST")

    db_config = {
        "host": os.getenv(
            "DATABASE_HOST", config_data.get("database", {}).get("host", default_host)
        ),
        "port": int(os.getenv("DATABASE_PORT", config_data.get("database", {}).get("port", 5432))),
        "name": os.getenv(
            "DATABASE_NAME", config_data.get("database", {}).get("name", "grade_monitor")
        ),
        "user": os.getenv("DATABASE_USER", config_data.get("database", {}).get("user", "gradebot")),
        "password": os.getenv("DATABASE_PASSWORD", config_data.get("database", {}).get("password")),
    }

    config_data["database"] = db_config

    # DPS credentials from environment
    dps_username = os.getenv("DPS_USERNAME")
    dps_password = os.getenv("DPS_PASSWORD")
    if dps_username and dps_password:
        config_data["dps"] = {"username": dps_username, "password": dps_password}

    return AppConfig(**config_data)


def get_database_url(config: AppConfig) -> str:
    """Get PostgreSQL connection URL."""
    db = config.database
    return f"postgresql://{db.user}:{db.password}@{db.host}:{db.port}/{db.name}"


def create_default_config(config_path: Path) -> None:
    """Create a default configuration file."""
    default_config = {
        "students": [
            {
                "name": "Test Student",
                "phone": "+1234567890",
                "grade_level": 7,
                "school": "Test School",
            }
        ],
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "grade_monitor",
            "user": "gradebot",
            "password": "${DATABASE_PASSWORD}",
        },
    }

    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        yaml.dump(default_config, f, default_flow_style=False)
