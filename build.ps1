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
