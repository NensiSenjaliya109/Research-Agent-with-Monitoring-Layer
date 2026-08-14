# User Package Manager Preference

Whenever proposing python commands (e.g. installing packages, managing virtual environments), always use the `uv` package manager instead of standard `pip` or `python -m pip`.

## Guidelines
- For installing dependencies: use `uv pip install -r requirements.txt`
- For creating environments: use `uv venv`
- For running python scripts inside the environment: use `uv run <script.py>`
