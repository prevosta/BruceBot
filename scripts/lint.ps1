# Run ruff and pyright for linting and type checking
Write-Host "Running ruff..." -ForegroundColor Cyan
poetry run ruff check . --fix

Write-Host "`nRunning pyright..." -ForegroundColor Cyan
poetry run pyright
