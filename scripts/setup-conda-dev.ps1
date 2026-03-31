param(
    [string]$EnvName = "nwbforge-dev"
)

$ErrorActionPreference = "Stop"
$env:PYTHONNOUSERSITE = "1"

$existing = conda env list | Select-String -Pattern "^\s*$EnvName\s"
if ($existing) {
    conda env update -n $EnvName --file environment.yml --prune
} else {
    conda env create -n $EnvName --file environment.yml
}

conda run -n $EnvName python -m pip install -e .
