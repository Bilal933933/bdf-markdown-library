$ErrorActionPreference = "Stop"
$env:PYTHONDONTWRITEBYTECODE = "1"

$backend = Join-Path $PSScriptRoot "backend"
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    throw "uv is required. Install it from https://docs.astral.sh/uv/"
}

Push-Location $backend
try {
    function Invoke-ValidationStep {
        param([scriptblock]$Command)

        & $Command
        if ($LASTEXITCODE -ne 0) {
            throw "Validation command failed with exit code $LASTEXITCODE"
        }
    }

    Invoke-ValidationStep { uv sync --locked }
    Invoke-ValidationStep { uv run pytest }
    Invoke-ValidationStep { uv run ruff format --check app tests }
    Invoke-ValidationStep { uv run ruff check app tests }
    Invoke-ValidationStep { uv run mypy app }
} finally {
    Pop-Location
}
