param(
    [string]$EnvName = "nwbforge-dev"
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"
conda run -n $EnvName pytest
