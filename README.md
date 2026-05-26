# symphony-go

Minimal Python project scaffold for experiments and new service code.

## Status

This repository is currently a lightweight starting point. At the moment it
contains:

- `README.md` with project notes
- `.gitignore` tuned for common Python tooling and local environments
- `LICENSE`

Application code, dependency metadata, and tests have not been added yet.

## Getting Started

1. Install Python 3.11 or newer.
2. Create a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

3. Add project metadata with `pyproject.toml` or `requirements.txt`.
4. Add source code and tests.

## Recommended Layout

```text
.
├── README.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── symphony_go/
└── tests/
```

## Development Notes

- Keep dependencies isolated in a virtual environment.
- Prefer `pyproject.toml` for dependency and tool configuration.
- Store importable code under `src/` and automated tests under `tests/`.

## License

See [LICENSE](LICENSE) for the full license text.
