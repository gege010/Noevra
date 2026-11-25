# Noevra

[![CI](https://github.com/gege010/Noevra/actions/workflows/ci.yml/badge.svg)](https://github.com/gege010/Noevra/actions/workflows/ci.yml)

Noevra is a local research workspace for turning a question into a cited report. Open a finding to inspect its supporting passages, check the original sources, and see which questions the evidence leaves unresolved. Your investigations stay in a searchable SQLite library.

## Quick start

Install Git and Python 3.11 or 3.12, then run the following commands.

```sh
git clone https://github.com/gege010/Noevra.git
cd Noevra
python run.py
```

Open **http://127.0.0.1:8000**. The first launch downloads dependencies into a project-local virtual environment. Later launches reuse it. On Windows you can use `py -3.11 run.py`. On macOS or Linux use `python3 run.py` if needed. Press **Ctrl+C** to stop the server.

## Run your first investigation

1. Open **Connections**, select a provider, and discover the models available to your account. You can also use a running Ollama or custom OpenAI-compatible endpoint.
2. Enter a question or select an editable example. Choose a research depth and model, then select **Research**.
3. Follow the five stages from planning to review. Open **Evidence** to inspect the passages behind a claim and **Sources** to visit the originals.
4. Reopen the investigation from **Library**. Export the report as Markdown or PDF, or download its references as BibTeX.

The workspace starts without credentials. Running research requires a model connection and network access for source retrieval. Model and search providers may charge for requests. Even with local inference, enabled source searches reach external services. Check the original sources before relying on a finding.

## Configuration and storage

| Task | Where to start |
| --- | --- |
| Connect a hosted model | Choose Groq, OpenAI, Anthropic, Gemini, DeepSeek, or OpenRouter in Connections. The model picker uses the provider's catalog. |
| Configure server-side credentials | Copy [.env.example](.env.example) to `.env`, fill the settings you need, and restart. Credentials entered through the browser last only for the current tab session. |
| Choose where research is saved | Set `NOEVRA_DATA_DIR` and leave `DATABASE_URL` empty to use SQLite there. The local launcher defaults to `data/`. |
| Back up the library | Stop the server and copy the complete data directory. Each running workspace needs its own database. |
| Check a startup problem | Run `python run.py --check`. If the port is busy, try `python run.py --port 8001`. |
| Run with Docker | With Docker Compose 2.24 or newer, run `docker compose up --build`. Compose stores research in a separate named volume. |

For OAuth setup, deployment settings, and hosting requirements, read the [deployment guide](DEPLOYMENT.md).

## Development

FastAPI serves the HTML, CSS, and JavaScript workspace. A LangGraph workflow coordinates the planner, researcher, verifier, writer, and reviewer. See the [architecture](ARCHITECTURE.md) for the job lifecycle and the [interaction contract](UX-CONTRACT.md) for expected browser behavior.

Run `python run.py --install`, then activate `.venv` with `.\.venv\Scripts\Activate.ps1` in PowerShell or `source .venv/bin/activate` in Bash. Install the development dependencies and run the same core checks as CI. The JavaScript tests require Node.js 22.

```sh
python -m pip install -r requirements-dev.txt -c constraints.txt
python -m pip check
python -m ruff check src tests run.py
python -m ruff format --check src tests run.py
python -m pytest tests/unit
node --test tests/oauth-client.test.cjs tests/provider-picker.test.cjs tests/ui-renderer.test.cjs
```

Automated tests isolate storage and provider traffic. The [CI workflow](.github/workflows/ci.yml) also checks startup, compiles the source, and builds a wheel on Windows and Linux.

## Help and contributions

Maintained by [gege010](https://github.com/gege010). For help or bug reports, open a [GitHub issue](https://github.com/gege010/Noevra/issues) with your operating system, Python version, steps to reproduce, and expected result. Remove credentials and private research content from logs. For code changes, open a pull request describing the behavior and the checks you ran.

## License

Noevra is distributed under the [MIT License](LICENSE). Bundled fonts and browser libraries include their own licenses in [src/static](src/static/).
