# Build the Windows app: dist\LeafLandmarks_v<N>.exe, one file with Python and everything it needs inside.
# Needs Python with numpy, opencv-python-headless, pillow, pillow-heif and pyinstaller installed.
# Usage (PowerShell, in this folder):  .\build_exe.ps1 1      (the number is the version; an existing exe is never overwritten)
param([Parameter(Mandatory = $true)][int]$Version)
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$name = "LeafLandmarks_v$Version"
$exe = Join-Path $here "dist\$name.exe"
if (Test-Path $exe) { throw "$exe already exists - not overwriting (use the next version number)" }
$work = Join-Path $env:TEMP "leaf_app_build_$Version"
python -m PyInstaller --noconfirm --onefile --windowed --name $name `
    --icon (Join-Path $here "leaf_icon.ico") `
    --add-data "$(Join-Path $here 'leaf_icon.ico');." `
    --paths (Join-Path $here "..\scripts") `
    --exclude-module matplotlib --exclude-module scipy --exclude-module pandas `
    --distpath (Join-Path $here "dist") --workpath $work --specpath $work `
    (Join-Path $here "leaf_app.py") 2>&1 | ForEach-Object { "$_" }      # PyInstaller logs to stderr: show it as text
if ($LASTEXITCODE -ne 0 -or -not (Test-Path $exe)) { throw "build failed: $exe not made" }
"built $exe ($([math]::Round((Get-Item $exe).Length / 1MB)) MB)"
