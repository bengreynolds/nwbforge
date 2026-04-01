param(
    [string]$EnvName = "nwbforge-dev",
    [ValidateSet("minimal", "selected", "full")]
    [string]$InstallMode = "selected",
    [ValidateSet("minimal", "common", "full", "custom")]
    [string]$Preset = "common",
    [string[]]$Routes = @(),
    [string]$SelectionPath = ".nwbforge/install-selection.json"
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"

$setupArgs = @(
    "-ExecutionPolicy", "Bypass",
    "-File", "scripts/setup-conda-dev.ps1",
    "-EnvName", $EnvName,
    "-InstallMode", $InstallMode,
    "-Preset", $Preset,
    "-SelectionPath", $SelectionPath,
    "-PersistSelection"
)

foreach ($route in $Routes) {
    $setupArgs += @("-Routes", $route)
}

powershell @setupArgs

conda run -n $EnvName pytest
