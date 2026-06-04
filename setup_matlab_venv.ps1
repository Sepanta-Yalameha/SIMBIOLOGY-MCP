# ===== RESOLVE SCRIPT DIRECTORY =====
$SCRIPT_DIR = Split-Path -Parent $MyInvocation.MyCommand.Path
$WORKSPACE = Split-Path -Parent $SCRIPT_DIR

# ===== CONFIG =====
$MATLAB_PATH = "C:\Program Files\MATLAB\R2025b\extern\engines\python"
$WORK_DIR = Join-Path $WORKSPACE "matlab_engine_build"
$VENV_DIR = Join-Path $WORKSPACE "venv"

# ===== 1. CREATE VENV =====
python -m venv $VENV_DIR

# Activate venv
& "$VENV_DIR\Scripts\Activate.ps1"

# ===== 2. UPGRADE BUILD TOOLS =====
python -m pip install --upgrade pip setuptools wheel

# ===== 3. COPY MATLAB ENGINE SOURCE =====
if (Test-Path $WORK_DIR) {
    Remove-Item $WORK_DIR -Recurse -Force
}

Copy-Item $MATLAB_PATH $WORK_DIR -Recurse

# ===== 4. INSTALL ENGINE =====
Set-Location $WORK_DIR
pip install .

# ===== DONE =====
Write-Host "MATLAB Engine installed successfully"
Write-Host "Workspace: $WORKSPACE"
Write-Host "Venv: $VENV_DIR"
