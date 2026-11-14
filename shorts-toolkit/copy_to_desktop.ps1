# Copies the Shorts toolkit to the Desktop folder, then checks every file arrived whole:
# same size and same SHA-256 hash as the source. Run it from anywhere:
#
#   powershell -ExecutionPolicy Bypass -File copy_to_desktop.ps1
#
# The whole toolkit is copied, not just lesson 6, because lesson 6 uses lesson 1's font,
# lesson 3's freeze-rewind and the bridge folder next to it.

param(
    [string]$Dest = "C:\Users\reydi\OneDrive\Desktop\Shorts homework"
)

$Source = $PSScriptRoot
$files = Get-ChildItem -Path $Source -Recurse -File |
    Where-Object { $_.FullName -notmatch '\\__pycache__\\' -and $_.Extension -ne '.pyc' }

New-Item -ItemType Directory -Force -Path $Dest | Out-Null
$ok = 0; $bad = @()
foreach ($f in $files) {
    $rel = $f.FullName.Substring($Source.Length).TrimStart('\')
    $target = Join-Path $Dest $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
    Copy-Item -LiteralPath $f.FullName -Destination $target -Force

    $copy = Get-Item -LiteralPath $target
    $h1 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
    $h2 = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash
    if ($copy.Length -eq $f.Length -and $h1 -eq $h2) { $ok++ }
    else { $bad += "$rel (size $($f.Length) -> $($copy.Length))" }
}

Write-Host "Copied to $Dest"
Write-Host "$ok of $($files.Count) files match the source by size and SHA-256."
if ($bad.Count) {
    Write-Host "These did NOT match. OneDrive may still be syncing; run the script again:" -ForegroundColor Red
    $bad | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
    exit 1
}
Write-Host "All files verified." -ForegroundColor Green
