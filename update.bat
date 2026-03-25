@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
set "NO_PAUSE=0"

if /i "%~1"=="--no-pause" (
    set "NO_PAUSE=1"
    shift
)

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "REPO_DIR=%SCRIPT_DIR%"
set "TAGS="
set "CONFIG_PATH=%SCRIPT_DIR%\ao3_config.json"

if exist "%CONFIG_PATH%" (
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$cfg = Get-Content -Raw '%CONFIG_PATH%' | ConvertFrom-Json; if ($cfg.output_dir) { $cfg.output_dir }"`) do (
        set "REPO_DIR=%%I"
    )
    for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$cfg = Get-Content -Raw '%CONFIG_PATH%' | ConvertFrom-Json; if ($cfg.tag_inputs) { ($cfg.tag_inputs | ForEach-Object { '\"' + $_ + '\"' }) -join ' ' }"`) do (
        set "TAGS=%%I"
    )
)

if exist "%SCRIPT_DIR%\update.local.bat" (
    call "%SCRIPT_DIR%\update.local.bat"
)

if not "%~1"=="" (
    set "TAGS=%*"
)

echo ====================================================
echo   AO3 Sorter Update
echo ====================================================
echo.

if not exist "%SCRIPT_DIR%\ao3_sorter.py" (
    echo Missing file: %SCRIPT_DIR%\ao3_sorter.py
    goto :exit_error
)

if not exist "%SCRIPT_DIR%\gen_tags.py" (
    echo Missing file: %SCRIPT_DIR%\gen_tags.py
    goto :exit_error
)

if "%TAGS%"=="" (
    echo No tags configured.
    echo.
    echo Use one of these options:
    echo   1. Add tag_inputs to ao3_config.json
    echo   2. Run: update.bat "tag one" "tag two"
    echo   3. Copy update.local.example.bat to update.local.bat and edit TAGS there
    goto :exit_error
)

if not exist "%REPO_DIR%" (
    echo Output directory does not exist: %REPO_DIR%
    goto :exit_error
)

for %%T in (%TAGS%) do (
    echo ----------------------------------------
    echo Fetching: %%~T
    echo ----------------------------------------
    python "%SCRIPT_DIR%\ao3_sorter.py" "%%~T" "%REPO_DIR%"
    if errorlevel 1 (
        echo Failed while processing tag: %%~T
        goto :exit_error
    )
    echo.
)

echo ----------------------------------------
echo Rebuilding tags.json
echo ----------------------------------------
python "%SCRIPT_DIR%\gen_tags.py" "%REPO_DIR%"
if errorlevel 1 (
    echo Failed to rebuild tags.json
    goto :exit_error
)
echo.

pushd "%REPO_DIR%" >nul
git rev-parse --is-inside-work-tree >nul 2>&1
if errorlevel 1 (
    echo Not a git repository. Generated files were updated locally only.
    popd >nul
    goto :exit_ok
)

echo ----------------------------------------
echo Preparing git changes
echo ----------------------------------------
git add tags.json index.html ao3_sorted_*.html
git diff --cached --quiet
if not errorlevel 1 (
    echo No staged changes detected. Nothing to commit.
    popd >nul
    goto :exit_ok
)

set "COMMIT_MSG=Update AO3 data %date% %time:~0,8%"
git commit -m "%COMMIT_MSG%"
if errorlevel 1 (
    echo Git commit failed.
    popd >nul
    goto :exit_error
)

git push
if errorlevel 1 (
    echo Git push failed.
    popd >nul
    goto :exit_error
)

popd >nul
echo.
echo ====================================================
echo   Update complete
echo ====================================================
goto :exit_ok

:exit_error
echo.
echo Update failed.
if "%NO_PAUSE%"=="0" pause
exit /b 1

:exit_ok
if "%NO_PAUSE%"=="0" pause
exit /b 0
