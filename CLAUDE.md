# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Grade Guardian is a Python 3.13 project that appears to be in early development stages. The project uses `uv` as its package manager and build system.

## Development Environment

- **Python Version**: 3.13 (specified in `.python-version`)
- **Package Manager**: uv (Ultra Violet)
- **Project Structure**: Standard Python package in `src/grade_guardian/`

## Common Commands

### Package Management
```bash
# Install dependencies
uv sync

# Add a new dependency
uv add <package_name>

# Remove a dependency
uv remove <package_name>

# Update lockfile
uv lock
```

### Running the Application
```bash
# Run the main application
uv run grade-guardian

# Run Python scripts directly
uv run python <script.py>
```

### Building
```bash
# Build the package
uv build
```

### Code Formatting
```bash
# Format Python code
uv format
```

## Project Structure

The project follows a standard Python package layout:
- `src/grade_guardian/` - Main package directory
- `pyproject.toml` - Project configuration and dependencies
- Entry point: `grade_guardian:main` function in `src/grade_guardian/__init__.py`