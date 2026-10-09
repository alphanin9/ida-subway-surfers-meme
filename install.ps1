# Installs the Subway Surfers plugin into IDA, Binary Ninja and/or Ghidra.
# Usage: .\install.ps1 [-Video path\to\clip.mp4|.gif] [-Ida] [-Binja] [-Ghidra]   (no switches = all)
# The ASCII game needs no video; -Video is only for SUBWAY_MODE=video (Ghidra plays GIFs only).
param([string]$Video, [switch]$Ida, [switch]$Binja, [switch]$Ghidra)

if (-not ($Ida -or $Binja -or $Ghidra)) { $Ida = $Binja = $Ghidra = $true }
$src = $PSScriptRoot

$targets = @()
if ($Ida) { $targets += @{ Dir = "$env:APPDATA\Hex-Rays\IDA Pro\plugins\subway_surfers"; Files = "ida\subway_surfers.py", "ida\ida-plugin.json", "subway_player.py" } }
if ($Binja) { $targets += @{ Dir = "$env:APPDATA\Binary Ninja\plugins\subway_surfers"; Files = "binja\__init__.py", "subway_player.py" } }
if ($Ghidra) { $targets += @{ Dir = "$env:USERPROFILE\ghidra_scripts"; Files = @("ghidra\SubwaySurfers.java"); GifOnly = $true } }

foreach ($t in $targets) {
    New-Item -ItemType Directory -Force $t.Dir | Out-Null
    foreach ($f in @($t.Files) + "subway_ascii.py") { Copy-Item (Join-Path $src $f) $t.Dir -Force }
    $ext = if ($Video) { [IO.Path]::GetExtension($Video).ToLower() }
    if ($Video -and (-not $t.GifOnly -or $ext -eq ".gif")) {
        Copy-Item $Video (Join-Path $t.Dir "subway_surfers$ext") -Force
    }
    Write-Host "Installed to $($t.Dir)"
}
