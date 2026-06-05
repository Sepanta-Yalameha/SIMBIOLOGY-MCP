param(
    [string]$MatlabRoot,
    [string]$PythonPath,
    [int]$MatlabIndex = -1,
    [int]$PythonIndex = -1
)

function Select-InteractiveOption {
    param(
        [Parameter(Mandatory = $true)]
        [array]$Items,
        [Parameter(Mandatory = $true)]
        [string]$Prompt
    )

    if ($Items.Count -eq 1) {
        Write-Host "$Prompt Using the only detected option: $($Items[0].Name)"
        return $Items[0]
    }

    while ($true) {
        $choice = Read-Host $Prompt
        if ([string]::IsNullOrWhiteSpace($choice)) {
            Write-Host "Please enter a number from 0 to $($Items.Count - 1)."
            continue
        }

        if ($choice -match '^\d+$') {
            $index = [int]$choice
            if ($index -ge 0 -and $index -lt $Items.Count) {
                return $Items[$index]
            }
        }

        Write-Host "Invalid selection. Enter a number from 0 to $($Items.Count - 1)."
    }
}

# ===== Save original workspace directory =====
$ORIGINAL_DIR = Get-Location

# ===== RESOLVE SCRIPT DIRECTORY (WORKSPACE = SCRIPT FOLDER) =====
$WORKSPACE = Split-Path -Parent $MyInvocation.MyCommand.Path
Write-Host "`nWorkspace: $WORKSPACE`n"

# ===== CONFIG PATHS =====
$VENV_DIR = Join-Path $WORKSPACE ".venv"
$MATLAB_BUILD_TEMP = Join-Path $env:TEMP "matlab_engine_build"

# ===== GET INSTALLED MATLAB VERSIONS =====
if ([string]::IsNullOrWhiteSpace($MatlabRoot)) {
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

    $selected = $null
    if ($MatlabIndex -ge 0) {
        if ($MatlabIndex -ge $matlabVersions.Count) {
            throw "Invalid MATLAB selection index."
        }
        $selected = $matlabVersions[$MatlabIndex]
    } else {
        $selected = Select-InteractiveOption `
            -Items $matlabVersions `
            -Prompt "Select a MATLAB installation index"
    }

    $MATLAB_ROOT = (Get-ItemProperty $selected.PSPath).MATLABROOT
} else {
    $MATLAB_ROOT = $MatlabRoot
}
$MATLAB_PATH = Join-Path $MATLAB_ROOT "extern\engines\python"

Write-Host "`nUsing MATLAB: $MATLAB_ROOT`n"

if (!(Test-Path $MATLAB_PATH)) {
    throw "MATLAB engine path not found: $MATLAB_PATH"
}

if ([string]::IsNullOrWhiteSpace($PythonPath)) {
    # ===== DETECT PYTHON =====
    Write-Host "`nDetecting Python installations..."

    $pyCandidates = @()

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

    try {
        $pathPy = (Get-Command python -ErrorAction Stop).Source
        $version = & $pathPy --version 2>&1
        $pyCandidates += [PSCustomObject]@{
            Name = "PATH Python ($version)"
            Path = $pathPy
        }
    } catch {}

    $pyCandidates = $pyCandidates | Where-Object { $_.Path } | Sort-Object Path -Unique

    if ($pyCandidates.Count -eq 0) {
        throw "No Python installations found."
    }

    Write-Host "`nDetected Python interpreters:`n"

    for ($i = 0; $i -lt $pyCandidates.Count; $i++) {
        Write-Host "[$i] $($pyCandidates[$i].Name) -> $($pyCandidates[$i].Path)"
    }

    if ($PythonIndex -ge 0) {
        if ($PythonIndex -ge $pyCandidates.Count) {
            throw "Invalid Python selection index."
        }
        $PYTHON = $pyCandidates[$PythonIndex].Path
    } else {
        $selectedPy = Select-InteractiveOption `
            -Items $pyCandidates `
            -Prompt "Select a Python interpreter index"
        $PYTHON = $selectedPy.Path
    }
} else {
    $PYTHON = $PythonPath
}

Write-Host "`nUsing Python: $PYTHON`n"

# ===== CREATE VENV =====
Write-Host "Creating virtual environment..."
& $PYTHON -m venv $VENV_DIR

$VENV_PYTHON = Join-Path $VENV_DIR "Scripts\python.exe"
if (!(Test-Path $VENV_PYTHON)) {
    $VENV_PYTHON = Join-Path $VENV_DIR "bin\python.exe"
}
if (!(Test-Path $VENV_PYTHON)) {
    throw "Could not locate python executable inside venv: $VENV_DIR"
}

# ===== UPGRADE BUILD TOOLS =====
Write-Host "Upgrading pip/setuptools/wheel..."
& $VENV_PYTHON -m pip install --upgrade pip setuptools wheel

# ===== INSTALL REQUIREMENTS =====
if (Test-Path (Join-Path $WORKSPACE "requirements.txt")) {
    Write-Host "`nInstalling requirements from requirements.txt..."
    & $VENV_PYTHON -m pip install -r (Join-Path $WORKSPACE "requirements.txt")
}

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

& $VENV_PYTHON setup.py `
    build   --build-base "$MATLAB_BUILD_TEMP" `
    egg_info --egg-base  "$MATLAB_BUILD_TEMP" `
    install  --record    "$MATLAB_BUILD_TEMP\install_record.txt"

if ($LASTEXITCODE -ne 0) {
    throw "MATLAB engine installation failed (exit code $LASTEXITCODE)."
}

# ===== VERIFY =====
Write-Host "`nVerifying installation..."
$installed = & $VENV_PYTHON -m pip show matlabengine 2>$null
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
