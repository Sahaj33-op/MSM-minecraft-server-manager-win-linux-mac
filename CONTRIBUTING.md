# Contributing to MSM

We welcome contributions! Please follow these guidelines.

## Development Setup

1. **Fork and Clone**:
   ```bash
   git clone https://github.com/Sahaj33-op/MSM-minecraft-server-manager-win-linux-mac.git
   cd MSM-minecraft-server-manager-win-linux-mac
   ```

2. **Install Dependencies**:
   ```bash
   pip install poetry
   poetry install
   ```

3. **Pre-commit Hooks**:
   ```bash
   poetry run pre-commit install
   ```

4. **Frontend Setup** (optional):
   ```bash
   cd web/frontend
   npm install
   cd ../..
   ```

## Code Style

### Python
- **Black**: Code formatting
- **Ruff**: Linting
- **Isort**: Import sorting
- **Mypy**: Type checking (strict mode)

Run all checks:
```bash
poetry run black .
poetry run ruff check --fix .
poetry run mypy .
```

### Frontend
- **Prettier**: Code formatting
- **ESLint**: Linting
- **TypeScript**: Strict mode

Run checks:
```bash
cd web/frontend
npm run lint
```

## Testing

Run tests before submitting a PR:

```bash
# All tests
poetry run pytest

# Unit tests only
poetry run pytest tests/unit

# Integration tests only
poetry run pytest tests/integration

# With coverage
poetry run pytest --cov=msm_core --cov=cli --cov=web

# Verbose output
poetry run pytest -v
```

## Project Structure

Understanding the project structure helps with contributions:

| Directory | Purpose |
|-----------|---------|
| `msm_core/` | Core business logic (OS-agnostic) |
| `platform_adapters/` | Platform-specific implementations |
| `cli/` | Command-line interface |
| `web/backend/` | FastAPI REST API |
| `web/frontend/` | React dashboard |
| `tests/` | Unit and integration tests |

## Adding Features

### Adding a New Core Module

1. Create your module in `msm_core/`
2. Add any new database models to `msm_core/db.py`
3. Create API functions in your module
4. Add CLI commands in `cli/main.py`
5. Add REST endpoints in `web/backend/app.py`
6. Write tests in `tests/unit/`

### Adding a Platform Adapter

1. Create new file in `platform_adapters/`
2. Inherit from `PlatformAdapter` in `platform_adapters/base.py`
3. Implement all abstract methods
4. Update `msm_core/utils.py` to select adapter based on `sys.platform`

### Database Patterns

Use the context manager pattern for database operations:

```python
from msm_core.db import get_session, Server

with get_session() as session:
    server = session.query(Server).filter(Server.id == server_id).first()
    # Changes are auto-committed on context exit
```

### Adding REST Endpoints

Follow the existing patterns in `web/backend/app.py`:

```python
@app.get("/api/v1/your-endpoint", tags=["YourCategory"])
def your_endpoint():
    """Endpoint description."""
    try:
        result = your_core_function()
        return result
    except MSMError as e:
        raise handle_msm_error(e)
```

## Pull Requests

### Before Submitting

1. Ensure all tests pass: `poetry run pytest`
2. Format code: `poetry run black .`
3. Check linting: `poetry run ruff check .`
4. Type check: `poetry run mypy .`
5. Update documentation if necessary

### Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat: add plugin update checker
fix: correct backup restoration path
docs: update API documentation
refactor: simplify scheduler logic
test: add plugin manager tests
```

### PR Description

Include in your PR description:
- What changes were made
- Why the changes were needed
- How to test the changes
- Any breaking changes

## Reporting Issues

When reporting issues, include:
- MSM version
- Operating system and version
- Python version
- Steps to reproduce
- Expected vs actual behavior
- Relevant log output

## Feature Requests

Feature requests are welcome! Please:
- Check if the feature already exists
- Describe the use case
- Suggest implementation approach if possible

## Questions?

Feel free to open a discussion or issue if you have questions about contributing.
