# Package WoodShedStorage into the PZ Workshop upload folder.
# Set ZOMBOID_USERDIR if your cache is not the default (e.g. Steam -cachedir=...).
$ErrorActionPreference = "Stop"

$Zomboid = $env:ZOMBOID_USERDIR
if (-not $Zomboid) {
    $candidates = @(
        (Join-Path "F:\Users\$env:USERNAME" "Zomboid"),
        (Join-Path $env:USERPROFILE "Zomboid")
    )
    foreach ($c in $candidates) {
        if (Test-Path (Join-Path $c "mods")) { $Zomboid = $c; break }
    }
}
if (-not $Zomboid) { throw "Set ZOMBOID_USERDIR to your Project Zomboid user folder (mods/Workshop live there)." }

$src = Join-Path $Zomboid "mods\WoodShedStorage"
$ws  = Join-Path $Zomboid "Workshop\WoodShedStorage"
$dest = Join-Path $ws "Contents\mods\WoodShedStorage"

if (-not (Test-Path $src)) { throw "Missing mod source: $src" }

New-Item -ItemType Directory -Force -Path $dest | Out-Null

foreach ($folder in @("42", "common")) {
    $from = Join-Path $src $folder
    $to   = Join-Path $dest $folder
    if (Test-Path $to) { Remove-Item $to -Recurse -Force }
    robocopy $from $to /E /NFL /NDL /NJH /NJS /nc /ns /np | Out-Null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed for $folder (code $LASTEXITCODE)" }
}

$poster = Join-Path $src "42\poster.png"
if (Test-Path $poster) {
    Copy-Item $poster (Join-Path $ws "preview.png") -Force
}

$wt = Join-Path $ws "workshop.txt"
if (-not (Test-Path $wt)) {
    throw "Missing workshop.txt at $wt - create it before packaging."
}

Write-Host "Packaged -> $ws"
Write-Host "Upload from Project Zomboid Workshop UI using that folder."
Get-ChildItem $ws -Recurse -File |
    Select-Object @{N="Rel";E={$_.FullName.Substring($ws.Length+1)}}, Length |
    Format-Table -AutoSize
