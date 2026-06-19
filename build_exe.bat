@echo off
echo Building AI Assistant .exe...
echo.

cd /d "%~dp0"

backend\venv\Scripts\pyinstaller.exe ^
  --onefile ^
  --windowed ^
  --name "AI Assistant" ^
  --icon NONE ^
  --add-data "backend\venv\Lib\site-packages\customtkinter;customtkinter" ^
  --hidden-import customtkinter ^
  --hidden-import duckduckgo_search ^
  --hidden-import bs4 ^
  --hidden-import httpx ^
  app_gui.py

echo.
if exist "dist\AI Assistant.exe" (
  echo Build successful!
  echo Output: dist\AI Assistant.exe
) else (
  echo Build failed — check output above.
)
pause
