# Contributing to Engram

Thanks for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/emipanelliok/engram.git
cd engram
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check src/ tests/
ruff format src/ tests/
```

## Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/my-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linting (`ruff check src/ tests/`)
6. Submit a PR with a clear description

## Reporting Issues

Open an issue on GitHub with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your Python version and OS
