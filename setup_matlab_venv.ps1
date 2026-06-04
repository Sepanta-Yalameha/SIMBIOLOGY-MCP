# ===== Save original workspace directory =====
$ORIGINAL_DIR = Get-Location

# ===== RESOLVE SCRIPT DIRECTORY (WORKSPACE = SCRIPT FOLDER) =====
$WORKSPACE = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "`nWorkspace: $WORKSPACE`n"

# ===== CONFIG PATHS =====
$VENV_DIR = Join-Path $WORKSPACE ".venv"
$MATLAB_BUILD_TEMP = Join-Path $env:TEMP "matlab_engine_build"

# ===== GET INSTALLED MATLAB VERSIONS =====
$matlabVersions = Get-ChildItem "HKLM:\SOFTWARE\MathWorks\MATLAB" |
    Sort-Object Name -Descending

if ($matlabVersions.Count -eq 0) {
    throw "No MATLAB installations found in registry."
}

Write-Host "Detected MATLAB versions:`n"

for ($i = 0; $i -lt $matlabVersions.Count; $i++) {
    $root = (Get-ItemProperty $matlabVersions[$i].PSPath).MATLABROOT
    Write-Host "[$i] $($matlabVersions[$i].PSChildName) -> $root"
}

# ===== MATLAB SELECTION =====
$defaultIndex = 0

Write-Host "`nPress ENTER for latest ($($matlabVersions[$defaultIndex].PSChildName)), or type index: " -NoNewline
$inputChoice = Read-Host

if ($inputChoice -eq "") {
    $selected = $matlabVersions[$defaultIndex]
}
elseif ($inputChoice -match '^\d+$' -and [int]$inputChoice -lt $matlabVersions.Count) {
    $selected = $matlabVersions[[int]$inputChoice]
}
else {
    throw "Invalid MATLAB selection."
}

$MATLAB_ROOT = (Get-ItemProperty $selected.PSPath).MATLABROOT
$MATLAB_PATH = Join-Path $MATLAB_ROOT "extern\engines\python"

Write-Host "`nUsing MATLAB: $MATLAB_ROOT`n"

if (!(Test-Path $MATLAB_PATH)) {
    throw "MATLAB engine path not found: $MATLAB_PATH"
}

# ===== DETECT PYTHON =====
Write-Host "`nDetecting Python installations..."

$pyCandidates = @()

# 1. PY LAUNCHER (PRIMARY SOURCE)
try {
    $pyList = py -0p 2>$null
    foreach ($line in $pyList) {
        if ($line -match "(\d+\.\d+).*?(\S:\\.*python\.exe)") {
            $pyCandidates += [PSCustomObject]@{
                Name = "Python $($matches[1])"
                Path = $matches[2]
            }
        }
    }
} catch {}

# 2. PATH PYTHON (FALLBACK)
try {
    $pathPy = (Get-Command python -ErrorAction Stop).Source
    $version = & $pathPy --version 2>&1
    $pyCandidates += [PSCustomObject]@{
        Name = "PATH Python ($version)"
        Path = $pathPy
    }
} catch {}

# CLEAN UP DUPLICATES
$pyCandidates = $pyCandidates |
    Where-Object { $_.Path } |
    Sort-Object Path -Unique

if ($pyCandidates.Count -eq 0) {
    throw "No Python installations found."
}

Write-Host "`nDetected Python interpreters:`n"

for ($i = 0; $i -lt $pyCandidates.Count; $i++) {
    Write-Host "[$i] $($pyCandidates[$i].Name) -> $($pyCandidates[$i].Path)"
}

# ===== PYTHON SELECTION =====
$defaultPy = 0

Write-Host "`nPress ENTER for default ($($pyCandidates[$defaultPy].Name)), or type index: " -NoNewline
$pyChoice = Read-Host

if ($pyChoice -eq "") {
    $PYTHON = $pyCandidates[$defaultPy].Path
}
elseif ($pyChoice -match '^\d+$' -and [int]$pyChoice -lt $pyCandidates.Count) {
    $PYTHON = $pyCandidates[[int]$pyChoice].Path
}
else {
    throw "Invalid Python selection."
}

Write-Host "`nUsing Python: $PYTHON`n"

# ===== CREATE VENV =====
Write-Host "Creating virtual environment..."
& $PYTHON -m venv $VENV_DIR

# Activate venv
& "$VENV_DIR\Scripts\Activate.ps1"

# ===== UPGRADE BUILD TOOLS =====
Write-Host "Upgrading pip/setuptools/wheel..."
python -m pip install --upgrade pip setuptools wheel

# ===== INSTALL MATLAB ENGINE =====
# pip install from Program Files fails due to write permissions on the build dir.
# Workaround: use setup.py directly, redirecting all build/egg-info/record
# artifacts to TEMP so nothing tries to write into Program Files.
Write-Host "`nInstalling MATLAB engine (build artifacts -> $MATLAB_BUILD_TEMP)..."

# Clean any previous build artifacts to avoid stale state
if (Test-Path $MATLAB_BUILD_TEMP) {
    Remove-Item $MATLAB_BUILD_TEMP -Recurse -Force
}
New-Item -ItemType Directory -Force $MATLAB_BUILD_TEMP | Out-Null

Set-Location $MATLAB_PATH

python setup.py `
    build   --build-base "$MATLAB_BUILD_TEMP" `
    egg_info --egg-base  "$MATLAB_BUILD_TEMP" `
    install  --record    "$MATLAB_BUILD_TEMP\install_record.txt"

if ($LASTEXITCODE -ne 0) {
    throw "MATLAB engine installation failed (exit code $LASTEXITCODE)."
}

# ===== VERIFY =====
Write-Host "`nVerifying installation..."
$installed = pip show matlabengine 2>$null
if ($installed) {
    Write-Host "matlabengine verified in venv."
} else {
    throw "matlabengine not found in venv after install"
}

# ===== DONE =====
Set-Location $ORIGINAL_DIR
Write-Host "`n===== DONE ====="
Write-Host "Workspace  : $WORKSPACE"
Write-Host "MATLAB Root: $MATLAB_ROOT"
Write-Host "Python     : $PYTHON"
Write-Host "Venv       : $VENV_DIR"
Write-Host "Engine     : matlabengine installed successfully"
