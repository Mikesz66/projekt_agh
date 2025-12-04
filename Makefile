# Use .PHONY to declare targets that don't correspond to actual files.
# This prevents 'make' from getting confused if a file named 'setup' is ever created.
.PHONY: all setup data run test clean

# Default command to run when you just type 'make'
all: setup

# Sets up the development environment.
# Creates the virtual environment and installs dependencies from uv.lock.
setup: .venv
	@echo ">>> Environment is set up. Activate with: source .venv/bin/activate"

# The .venv target is a clever 'make' trick.
# This rule only runs if the .venv directory does NOT exist.
# So, running 'make setup' a second time does nothing, which is fast and efficient.
.venv: pyproject.toml uv.lock
	@echo ">>> Creating virtual environment and installing dependencies..."
	uv venv
	uv sync
	@touch .venv # We 'touch' the file to update its timestamp for 'make'

# Manages the data pipeline.
# Note: You need to create the 'scripts/download_data.sh' script.
data:
	@echo ">>> Downloading raw data..."
	@bash scripts/download_data.sh
	@echo ">>> Processing data..."
	uv run python scripts/process_data.py
	@echo ">>> Data is ready in the data/ directory."

# Run the main application using uv to ensure it's run inside the venv.
run:
	@echo ">>> Running the application..."
	uv run python -m src

# Run tests using uv.
test:
	@echo ">>> Running tests..."
	uv run pytest

# Clean up generated files and directories.
clean:
	@echo ">>> Cleaning up project..."
	@rm -rf .venv __pycache__ */__pycache__
	@rm -rf data/
	@echo ">>> Cleanup complete."
