# Builds dist\Pixbot.exe from this source with PyInstaller.
#   python -m pip install -r requirements.txt pyinstaller
#   .\build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$modules = "pixbot_acts", "pixbot_catalog", "pixbot_common", "pixbot_movies", "pixbot_outfits",
           "pixbot_paint", "pixbot_paths", "pixbot_vision"
# pixbot_pet.pyw / pixbot_app.pyw are started as scripts, so list everything they import
$hidden = $modules + @("numpy", "PIL", "PIL.Image", "PIL.ImageGrab", "PIL.ImageDraw",
                       "comtypes", "comtypes.client", "comtypes.stream", "pycaw", "pycaw.pycaw",
                       "tkinter", "tkinter.ttk", "tkinter.colorchooser", "winreg", "webbrowser",
                       "subprocess", "threading", "collections", "ctypes", "ctypes.wintypes",
                       "traceback", "shutil", "json", "math", "random", "runpy")

$pyiArgs = @("--noconfirm", "--clean", "--onefile", "--windowed", "--name", "Pixbot",
          "--icon", "pixbot.ico",
          "--add-data", "pixbot_pet.pyw;.", "--add-data", "pixbot_app.pyw;.",
          "--add-data", "pixbot.ico;.", "--add-data", "pixbot_links.json;.",
          "--paths", ".")
foreach ($h in $hidden) { $pyiArgs += @("--hidden-import", $h) }

$ErrorActionPreference = "Continue"      # PyInstaller logs to stderr; judge by exit code instead
python -m PyInstaller @pyiArgs pixbot.pyw 2>&1 | ForEach-Object { "$_" }
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed ($LASTEXITCODE)" }
Write-Host "Built: $PSScriptRoot\dist\Pixbot.exe"

# installer (needs the free Inno Setup 6: https://jrsoftware.org/isinfo.php)
$version = if ($env:PIXBOT_VERSION) { $env:PIXBOT_VERSION } else { "1.1.0" }
$iscc = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
          "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if ($iscc) {
    & $iscc "/DAppVersion=$version" "installer\pixbot.iss" 2>&1 | ForEach-Object { "$_" }
    if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed ($LASTEXITCODE)" }
    Write-Host "Built: $PSScriptRoot\dist\PixbotSetup.exe"
} else {
    Write-Host "Inno Setup not found - skipped PixbotSetup.exe (Pixbot.exe is still built)."
}
