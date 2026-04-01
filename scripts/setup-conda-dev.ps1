param(
    [string]$EnvName = "nwbforge-dev",
    [ValidateSet("minimal", "selected", "full")]
    [string]$InstallMode = "selected",
    [ValidateSet("minimal", "common", "full", "custom")]
    [string]$Preset = "common",
    [string[]]$Routes = @(),
    [string]$SelectionPath = ".nwbforge/install-selection.json",
    [switch]$UseSavedSelection,
    [switch]$PersistSelection
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"

$existing = conda env list | Select-String -Pattern "^\s*$EnvName\s"
if ($existing) {
    conda env update -n $EnvName --file environment.yml --prune
} else {
    conda env create -n $EnvName --file environment.yml
}

$resolveArgs = @(
    "scripts/resolve_dev_install.py",
    "--mode", $InstallMode,
    "--preset", $Preset,
    "--state-path", $SelectionPath
)

foreach ($route in $Routes) {
    $resolveArgs += @("--route", $route)
}

if ($UseSavedSelection) {
    $resolveArgs += "--use-persisted"
}

if ($PersistSelection) {
    $resolveArgs += "--persist"
}

$planJson = conda run -n $EnvName python @resolveArgs
$plan = $planJson | ConvertFrom-Json

conda run -n $EnvName python -m pip install -e "$($plan.editable_requirement)"
