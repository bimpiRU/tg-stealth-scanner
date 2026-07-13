# Starts tg-stealth-scanner after Windows logon.
# Waits for Docker Desktop daemon, then runs docker compose up -d.

$ProjectPath = Split-Path -Parent $PSScriptRoot
$LogFile = Join-Path $ProjectPath "logs" "autostart.log"

function Write-Log($Message) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $line = "$ts | $Message"
    Add-Content -Path $LogFile -Value $line -ErrorAction SilentlyContinue
    Write-Host $line
}

New-Item -ItemType Directory -Path (Split-Path $LogFile) -Force | Out-Null

Write-Log "Autostart script started. Project: $ProjectPath"

# Wait for Docker daemon (up to 2 minutes)
$maxWait = 24
$waited = 0
while ($waited -lt $maxWait) {
    try {
        $info = docker info 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Log "Docker daemon is ready."
            break
        }
    } catch {
        # not ready yet
    }
    Write-Log "Waiting for Docker daemon... ($waited/$maxWait)"
    Start-Sleep -Seconds 5
    $waited++
}

if ($waited -ge $maxWait) {
    Write-Log "ERROR: Docker daemon did not become ready in time."
    exit 1
}

Set-Location $ProjectPath
Write-Log "Running docker compose up -d..."
$output = docker compose up -d 2>&1
$exitCode = $LASTEXITCODE
Write-Log $output

if ($exitCode -ne 0) {
    Write-Log "ERROR: docker compose up failed with exit code $exitCode"
    exit $exitCode
}

Write-Log "Container started successfully."

# Optional: start external monitor in background
$monitorJob = Start-Job -ScriptBlock {
    param($Path)
    Set-Location $Path
    while ($true) {
        python scripts/monitor.py 2>&1 | Out-File -Append -FilePath (Join-Path $Path "logs" "monitor.log")
        Start-Sleep -Seconds 300
    }
} -ArgumentList $ProjectPath

Write-Log "External monitor job started (ID: $($monitorJob.Id))."
