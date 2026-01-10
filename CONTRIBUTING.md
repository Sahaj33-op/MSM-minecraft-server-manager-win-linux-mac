# Contributing to MSM

We welcome contributions! Please follow these guidelines.

## Development Setup

1.  **Fork and Clone**:
    ```bash
    git clone https://github.com/yourusername/msm.git
    ```

2.  **Install Dependencies**:
    ```bash
    pip install poetry
    poetry install
    ```

3.  **Pre-commit Hooks**:
    ```bash
    poetry run pre-commit install
    ```

## Code Style

- **Python**: Black, Ruff, Isort, Mypy (strict).
- **Frontend**: Prettier, ESLint.

## Testing

Run tests before submitting a PR:
```bash
poetry run pytest
```

## Pull Requests

- Use Conventional Commits for commit messages.
- Ensure all tests pass.
- Update documentation if necessary.
