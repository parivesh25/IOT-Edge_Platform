# Commands run from the Git root or any subfolder, without copying local files.
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('Setup', 'Check', 'Start', 'Stop', 'Test')]
    [string]$Action
)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$appRoot = Join-Path $repoRoot 'edge-lab-platform-starter\edge-lab-platform'
$venvPython = Join-Path $repoRoot '.venv\Scripts\python.exe'
$composeFile = Join-Path $appRoot 'docker-compose.yml'

# Every checkout gets its own Compose project, so Stop cannot stop another worktree.
# Ports are separate: use $env:MQTT_PORT = '1884' for a second running checkout.
$pathHasher = [System.Security.Cryptography.SHA256]::Create()
try {
    $pathBytes = [System.Text.Encoding]::UTF8.GetBytes($repoRoot.ToLowerInvariant())
    $pathHash = [BitConverter]::ToString($pathHasher.ComputeHash($pathBytes)).Replace('-', '').ToLowerInvariant()
} finally {
    $pathHasher.Dispose()
}
$composeProject = 'iot-edge-' + $pathHash.Substring(0, 8)

# Windows PowerShell does not throw automatically when a native command fails.
function Assert-CommandSucceeded([string]$Step) {
    if ($LASTEXITCODE -ne 0) {
        throw "$Step failed (exit code $LASTEXITCODE)."
    }
}

Push-Location $repoRoot
try {
    switch ($Action) {
        'Setup' {
            # Reuse an existing environment; create one only in a fresh checkout.
            if (-not (Test-Path -LiteralPath $venvPython)) {
                & python -m venv (Join-Path $repoRoot '.venv')
                Assert-CommandSucceeded 'Create Python environment'
            }
            & $venvPython -m pip install -r (Join-Path $appRoot 'requirements.txt')
            Assert-CommandSucceeded 'Install project requirements'
            & docker compose --project-name $composeProject --file $composeFile config --quiet
            Assert-CommandSucceeded 'Validate Compose configuration'
        }
        'Check' {
            & docker compose --project-name $composeProject --file $composeFile config
            Assert-CommandSucceeded 'Validate Compose configuration'
        }
        'Start' {
            & docker compose --project-name $composeProject --file $composeFile up -d --build
            Assert-CommandSucceeded 'Start platform'
        }
        'Stop' {
            # Keep volumes and host files. Remove only this checkout's containers/network.
            & docker compose --project-name $composeProject --file $composeFile down --remove-orphans
            Assert-CommandSucceeded 'Stop platform'
        }
        'Test' {
            if (-not (Test-Path -LiteralPath $venvPython)) {
                throw 'The repository .venv is missing. Restore your existing environment before running tests.'
            }
            $testsPath = Join-Path $appRoot 'tests'
            if (-not (Test-Path -LiteralPath $testsPath)) {
                throw 'No tests directory exists yet. Tests are scheduled for Phase 2.'
            }
            Push-Location $appRoot
            try {
                & $venvPython -m unittest discover -s tests
                Assert-CommandSucceeded 'Run unit tests'
            } finally {
                Pop-Location
            }
        }
    }
} finally {
    Pop-Location
}
