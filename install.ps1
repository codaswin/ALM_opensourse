# One-line installer for AI LinkedIn Manager (Windows).
#
#   irm https://raw.githubusercontent.com/codaswin/ALM_opensourse/main/install.ps1 | iex
#
# Downloads the latest GitHub Release's .msi and launches the standard
# Windows installer wizard. No cloning, no build tools, no Node/Rust/Python
# required on your machine.

$ErrorActionPreference = "Stop"

$Repo = "codaswin/ALM_opensourse"
$ApiUrl = "https://api.github.com/repos/$Repo/releases/latest"

Write-Host "Looking up the latest release of AI LinkedIn Manager..."
$Release = Invoke-RestMethod -Uri $ApiUrl -Headers @{ "User-Agent" = "ai-linkedin-manager-installer" }

$Asset = $Release.assets | Where-Object { $_.name -like "*.msi" } | Select-Object -First 1
if (-not $Asset) {
    Write-Error "No .msi asset found in the latest release."
    exit 1
}

$Dest = Join-Path $env:TEMP $Asset.name
Write-Host "Downloading $($Asset.browser_download_url)"
Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $Dest

Write-Host "Launching the installer..."
Write-Host "Windows may warn that this is from an unrecognized publisher (it's unsigned) -- choose 'More info' then 'Run anyway' if you trust the source."
Start-Process msiexec.exe -ArgumentList "/i", "`"$Dest`"" -Wait
