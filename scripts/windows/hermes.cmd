@echo off
setlocal

rem Stable Windows launcher. The generated hermes.exe console-script shim may
rem be denied by Windows Application Control even though the managed Python
rem runtime is allowed. Invoke the module through that runtime directly.
if defined HERMES_CLI_PYTHON (
  set "_HERMES_PYTHON=%HERMES_CLI_PYTHON%"
) else (
  set "_HERMES_PYTHON=%~dp0..\venv\Scripts\python.exe"
)

if not exist "%_HERMES_PYTHON%" (
  echo Hermes Python runtime not found: "%_HERMES_PYTHON%" 1>&2
  exit /b 127
)

call "%_HERMES_PYTHON%" -m hermes_cli.main %*
exit /b %ERRORLEVEL%
