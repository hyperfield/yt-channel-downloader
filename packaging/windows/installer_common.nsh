Unicode true
!include "MUI2.nsh"
!include "nsDialogs.nsh"
!include "LogicLib.nsh"
!include "WinMessages.nsh"
!include "x64.nsh"
!include "WinVer.nsh"
!include "${APP_PAYLOAD_INCLUDE}"

Name "YT Channel Downloader"
OutFile "${APP_INSTALLER_OUTPUT}"
!ifdef APP_TEST_ROOT
    RequestExecutionLevel user
    InstallDir "${APP_TEST_ROOT}\app"
    !define APP_REG_ROOT HKCU
    !define APP_REG_KEY "Software\YTChannelDownloaderInstallerTests\${APP_TEST_ID}"
    !define APP_UNINSTALL_KEY "Software\YTChannelDownloaderInstallerTests\${APP_TEST_ID}\Uninstall"
    !define APP_DEP_ROOT "${APP_TEST_ROOT}\dependencies"
    !define APP_PATH_SCOPE "Process"
    !define APP_DESKTOP_DIR "${APP_TEST_ROOT}\shortcuts\desktop"
    !define APP_STARTMENU_DIR "${APP_TEST_ROOT}\shortcuts\startmenu"
!else
    RequestExecutionLevel admin
    InstallDir "$PROGRAMFILES64\YT Channel Downloader"
    !define APP_REG_ROOT HKLM
    !define APP_REG_KEY "Software\YT Channel Downloader"
    !define APP_UNINSTALL_KEY "Software\Microsoft\Windows\CurrentVersion\Uninstall\YT Channel Downloader"
    !define APP_DEP_ROOT "$PROGRAMFILES64"
    !define APP_PATH_SCOPE "Machine"
    !define APP_DESKTOP_DIR "$DESKTOP"
    !define APP_STARTMENU_DIR "$SMPROGRAMS"
!endif
InstallDirRegKey ${APP_REG_ROOT} "${APP_REG_KEY}" "InstallDir"
ShowInstDetails show
ShowUninstDetails show
BrandingText "Quicknode"
SetCompressor /SOLID lzma

Var DesktopShortcutCheckbox
Var StartMenuShortcutCheckbox
Var CreateDesktopShortcut
Var CreateStartMenuShortcut

!define MUI_ABORTWARNING
!define MUI_ICON "${APP_ICON}"
!define MUI_UNICON "${APP_ICON}"
!define MUI_WELCOMEPAGE_TEXT "Setup installs YT Channel Downloader and checks FFmpeg, ffprobe, and Deno or Node.js.$\r$\n$\r$\nMissing FFmpeg tools and Deno will be downloaded during setup. An internet connection is needed for these downloads."
!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_DIRECTORY
Page custom ShortcutPageCreate ShortcutPageLeave
!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH
!insertmacro MUI_LANGUAGE "English"

VIProductVersion "${APP_WINDOWS_VERSION}"
VIAddVersionKey /LANG=1033 "ProductName" "YT Channel Downloader"
VIAddVersionKey /LANG=1033 "CompanyName" "Quicknode.net"
VIAddVersionKey /LANG=1033 "FileDescription" "YT Channel Downloader Installer"
VIAddVersionKey /LANG=1033 "FileVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "ProductVersion" "${APP_VERSION}"
VIAddVersionKey /LANG=1033 "LegalCopyright" "Copyright (c) hyperfield. Licensed under the MIT License."

Function .onInit
    ${IfNot} ${AtLeastWin10}
        MessageBox MB_ICONSTOP|MB_OK "Windows 10 or newer is required." /SD IDOK
        SetErrorLevel 1
        Abort
    ${EndIf}
    ${IfNot} ${RunningX64}
        MessageBox MB_ICONSTOP|MB_OK "64-bit Windows is required." /SD IDOK
        SetErrorLevel 1
        Abort
    ${EndIf}
    !ifdef APP_TEST_ROOT
        StrCpy $INSTDIR "${APP_TEST_ROOT}\app"
    !endif
FunctionEnd

Section "Install"
    ; Check all external dependencies before replacing application files.
    InitPluginsDir
    SetOutPath "$PLUGINSDIR"
    File /oname=install_dependencies.ps1 "${APP_DEPENDENCY_HELPER}"
    nsExec::ExecToLog '"$SYSDIR\WindowsPowerShell\v1.0\powershell.exe" -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "$PLUGINSDIR\install_dependencies.ps1" -InstallRoot "${APP_DEP_ROOT}" -PathScope ${APP_PATH_SCOPE} -MinDenoVersion ${APP_DENO_MIN_VERSION} -MinNodeVersion ${APP_NODE_MIN_VERSION}'
    Pop $0
    StrCmp $0 "0" dependencies_ready
    MessageBox MB_ICONSTOP|MB_OK "Dependency setup failed. See the setup details above. Your application files have not been replaced." /SD IDOK
    SetErrorLevel 1
    Abort
dependencies_ready:
    !insertmacro InstallPayload
    SetOutPath "$INSTDIR"
    WriteUninstaller "$INSTDIR\uninstall.exe"
    WriteRegStr ${APP_REG_ROOT} "${APP_REG_KEY}" "InstallDir" "$INSTDIR"
    WriteRegStr ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "DisplayName" "YT Channel Downloader"
    WriteRegStr ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "UninstallString" '$\"$INSTDIR\uninstall.exe$\"'
    WriteRegStr ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "DisplayIcon" "$INSTDIR\YT Channel Downloader.exe"
    WriteRegStr ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "DisplayVersion" "${APP_VERSION}"
    WriteRegStr ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "Publisher" "Quicknode.net"
    WriteRegDWORD ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "EstimatedSize" ${APP_ESTIMATED_SIZE}
    WriteRegDWORD ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "NoModify" 1
    WriteRegDWORD ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}" "NoRepair" 1
    ${If} $CreateDesktopShortcut == "true"
        CreateDirectory "${APP_DESKTOP_DIR}"
        CreateShortcut "${APP_DESKTOP_DIR}\YT Channel Downloader.lnk" "$INSTDIR\YT Channel Downloader.exe"
    ${EndIf}
    ${If} $CreateStartMenuShortcut == "true"
        CreateDirectory "${APP_STARTMENU_DIR}"
        CreateShortcut "${APP_STARTMENU_DIR}\YT Channel Downloader.lnk" "$INSTDIR\YT Channel Downloader.exe"
    ${EndIf}
    SendMessage ${HWND_BROADCAST} ${WM_SETTINGCHANGE} 0 "STR:Environment" /TIMEOUT=5000
SectionEnd

Section "Uninstall"
    Delete "${APP_DESKTOP_DIR}\YT Channel Downloader.lnk"
    Delete "${APP_STARTMENU_DIR}\YT Channel Downloader.lnk"
    ; Delete only files belonging to this bundle, preserving unrelated files.
    !insertmacro UninstallPayload
    Delete "$INSTDIR\uninstall.exe"
    DeleteRegKey ${APP_REG_ROOT} "${APP_UNINSTALL_KEY}"
    DeleteRegKey ${APP_REG_ROOT} "${APP_REG_KEY}"
    RMDir "$INSTDIR"
    ; Shared FFmpeg/Deno installations and their PATH entries are retained.
SectionEnd

Function ShortcutPageCreate
    nsDialogs::Create 1018
    Pop $0
    StrCpy $CreateDesktopShortcut "false"
    StrCpy $CreateStartMenuShortcut "false"
    ${NSD_CreateCheckBox} 0 0 100% 10u "Create a Desktop shortcut"
    Pop $DesktopShortcutCheckbox
    ${NSD_CreateCheckBox} 0 12u 100% 10u "Create a Start Menu shortcut"
    Pop $StartMenuShortcutCheckbox
    nsDialogs::Show
FunctionEnd

Function ShortcutPageLeave
    ${NSD_GetState} $DesktopShortcutCheckbox $0
    StrCmp $0 ${BST_CHECKED} 0 +2
    StrCpy $CreateDesktopShortcut "true"
    ${NSD_GetState} $StartMenuShortcutCheckbox $0
    StrCmp $0 ${BST_CHECKED} 0 +2
    StrCpy $CreateStartMenuShortcut "true"
FunctionEnd
