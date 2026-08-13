# Installe le Python 3.11 embarqué dans python\ (1er démarrage, avant que Python existe).
# Appelé par run.bat via PowerShell (natif Windows).
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$pydir = Join-Path $root 'python'

Write-Host "Telechargement de Python 3.11.9 embarque..."
$zip = Join-Path $env:TEMP 'dcsclaude-py-embed.zip'
Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-embed-amd64.zip' -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $pydir -Force
Remove-Item $zip -Force

# python311._pth : dossier projet + libs (+ sous-dossiers pywin32) + import site
$pth = @"
python311.zip
.
..
..\libs
..\libs\win32
..\libs\win32\lib
..\libs\Pythonwin

import site
"@
Set-Content -Path (Join-Path $pydir 'python311._pth') -Value $pth -Encoding ascii

Write-Host "Installation de pip..."
$getpip = Join-Path $pydir 'get-pip.py'
Invoke-WebRequest -Uri 'https://bootstrap.pypa.io/get-pip.py' -OutFile $getpip -UseBasicParsing
& (Join-Path $pydir 'python.exe') $getpip --no-warn-script-location
Remove-Item $getpip -Force

Write-Host "Python embarque pret."
