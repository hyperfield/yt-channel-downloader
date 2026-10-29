!ifndef APP_BUILD_CONFIG
    !ifndef APP_SOURCE_ROOT
        !define APP_SOURCE_ROOT "..\.."
    !endif
    !system '"${APP_SOURCE_ROOT}\.venv\Scripts\python.exe" "${APP_SOURCE_ROOT}\scripts\build_windows_installer.py" --backend ${APP_BACKEND} --prepare-only' = 0
    !define APP_BUILD_CONFIG "${APP_SOURCE_ROOT}\build\windows\nsis\${APP_BACKEND}\config.nsh"
!endif
!include "${APP_BUILD_CONFIG}"
