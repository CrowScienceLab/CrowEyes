param(
    [Parameter(Mandatory = $true)]
    [string]$MakeAppxPath,
    [string]$DistributionPath,
    [string]$PythonPath
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$layout = Join-Path $root "store\layout"
$assets = Join-Path $layout "Assets"
$package = Join-Path $root "release\CrowEyes_1.9.1.0_x64.msix"
$python = if ($PythonPath) { $PythonPath } else { Join-Path $root ".publish-venv\Scripts\python.exe" }
$distribution = if ($DistributionPath) { $DistributionPath } else { Join-Path $root 'dist\CrowEyes' }

if (-not (Test-Path -LiteralPath $MakeAppxPath)) { throw "MakeAppx.exe를 찾을 수 없습니다: $MakeAppxPath" }
if (-not (Test-Path -LiteralPath (Join-Path $distribution "CrowEyes.exe"))) { throw "먼저 PyInstaller 빌드를 실행하세요." }

if (Test-Path -LiteralPath $layout) {
    $resolvedLayout = (Resolve-Path -LiteralPath $layout).Path
    $expectedLayout = [IO.Path]::GetFullPath((Join-Path $root 'store\layout'))
    if ($resolvedLayout -ne $expectedLayout) { throw 'Unexpected Store layout path' }
    $archiveRoot = 'D:\App coding\_archive'
    New-Item -ItemType Directory -Path $archiveRoot -Force | Out-Null
    $archiveLayout = Join-Path $archiveRoot ("CrowEyes-store-layout-" + (Get-Date -Format 'yyyyMMdd-HHmmss') + '-' + [guid]::NewGuid().ToString('N'))
    Move-Item -LiteralPath $resolvedLayout -Destination $archiveLayout
}
New-Item -ItemType Directory -Path $layout, $assets | Out-Null
Copy-Item -LiteralPath (Join-Path $root "store\AppxManifest.xml") -Destination $layout
Copy-Item -Path (Join-Path $distribution '*') -Destination $layout -Recurse
& $python (Join-Path $root "tools\prepare_store_assets.py") $assets
if ($LASTEXITCODE -ne 0) { throw "Store 로고 생성에 실패했습니다." }

& $MakeAppxPath pack /d $layout /p $package /o
if ($LASTEXITCODE -ne 0) { throw "MSIX 패키징에 실패했습니다." }
Write-Output $package
