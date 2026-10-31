"""Build NSIS installers for PyInstaller one-file and cx_Freeze folder bundles."""

import argparse
import ctypes
from ctypes import wintypes
import hashlib
from pathlib import Path
import runpy
import shutil
import struct
import subprocess
import sys


def nsi_escape(value: str, *, runtime: bool = True) -> str:
    if "\n" in value or "\r" in value:
        raise ValueError("NSIS paths and values must not contain newlines")
    if "${" in value:
        raise ValueError("NSIS input paths must not contain preprocessor placeholders")
    if runtime:
        value = value.replace("$", "$$")
    return value.replace('"', '$\\"')


def executable_version(path: Path) -> tuple[int, ...]:
    api = ctypes.WinDLL("version", use_last_error=True)
    api.GetFileVersionInfoSizeW.argtypes = [wintypes.LPCWSTR, ctypes.POINTER(wintypes.DWORD)]
    api.GetFileVersionInfoSizeW.restype = wintypes.DWORD
    api.GetFileVersionInfoW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p]
    api.VerQueryValueW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR, ctypes.POINTER(ctypes.c_void_p), ctypes.POINTER(wintypes.UINT)]
    size = api.GetFileVersionInfoSizeW(str(path), None)
    if not size:
        raise ValueError(f"{path} needs Windows version metadata; rebuild it with the project build helper")
    buffer = ctypes.create_string_buffer(size)
    if not api.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise ctypes.WinError(ctypes.get_last_error())
    pointer = ctypes.c_void_p()
    length = wintypes.UINT()
    if not api.VerQueryValueW(buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    fields = struct.unpack("<13I", ctypes.string_at(pointer, 52))
    return fields[2] >> 16, fields[2] & 65535, fields[3] >> 16, fields[3] & 65535


def find_compiler(explicit: str | None) -> Path:
    if explicit:
        candidates = [Path(explicit)]
    else:
        discovered = shutil.which("makensis")
        candidates = ([Path(discovered)] if discovered else []) + [
            Path("C:/Program Files (x86)/NSIS/makensis.exe"),
            Path("C:/Program Files/NSIS/makensis.exe"),
        ]
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    raise ValueError("Install NSIS 3 and add makensis to PATH, or pass --makensis PATH")


def write_payload(path: Path, files: list[tuple[Path, Path]]) -> None:
    install = ["!macro InstallPayload"]
    for source, relative in files:
        parent = str(relative.parent).replace("/", "\\")
        target = "$INSTDIR" if parent == "." else "$INSTDIR\\" + nsi_escape(parent)
        install += [
            f'    SetOutPath "{target}"',
            f'    File "/oname={nsi_escape(relative.name)}" "{nsi_escape(str(source), runtime=False)}"',
        ]
    uninstall = ["!macroend", "", "!macro UninstallPayload"]
    uninstall += [f'    Delete "$INSTDIR\\{nsi_escape(str(relative))}"' for _, relative in files]
    directories = {parent for _, relative in files for parent in relative.parents if parent != Path(".")}
    for directory in sorted(directories, key=lambda item: (len(item.parts), str(item)), reverse=True):
        uninstall.append(f'    RMDir "$INSTDIR\\{nsi_escape(str(directory))}"')
    path.write_text("\n".join(install + uninstall + ["!macroend", ""]), encoding="utf-8")


def write_legacy_aliases(root: Path) -> None:
    for backend, name in (("pyinstaller", "mk_installer_ffmpeg.nsi"), ("cxfreeze", "mk_installer_cxfreeze.nsi")):
        (root / "dist" / name).write_text(
            '; Generated alias; edit the tracked sources under packaging/windows.\n'
            '!define APP_SOURCE_ROOT ".."\n'
            '!addincludedir "${APP_SOURCE_ROOT}\\packaging\\windows"\n'
            f'!include "installer_{backend}.nsi"\n',
            encoding="utf-8",
        )
    helpers = root / "dist/scripts"
    helpers.mkdir(exist_ok=True)
    (helpers / "install_ffmpeg.bat").write_text(
        '@echo off\n'
        'powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass '
        '-File "%~dp0..\\..\\packaging\\windows\\install_dependencies.ps1" %*\n'
        'exit /b %errorlevel%\n', encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend", choices=("pyinstaller", "cxfreeze"), required=True)
    parser.add_argument("--payload", type=Path, help="Override the input EXE or bundle directory")
    parser.add_argument("--makensis", help="Path to the NSIS compiler")
    parser.add_argument("--prepare-only", action="store_true", help="Generate compiler inputs without compiling")
    parser.add_argument("--test-root", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if sys.platform != "win32":
        parser.error("Build these installers on Windows")
    root = Path(__file__).resolve().parent.parent
    release = runpy.run_path(str(root / "src/yt_channel_downloader/_release.py"))
    from packaging.version import Version
    version = release["__version__"]
    numbers = Version(version).release
    if len(numbers) > 4 or any(number > 65535 for number in numbers):
        parser.error("The release version must fit four 16-bit Windows fields")
    windows_version = numbers + (0,) * (4 - len(numbers))
    minima = runpy.run_path(str(root / "src/yt_channel_downloader/classes/yt_dlp_options.py"))["MIN_JS_RUNTIME_VERSIONS"]
    default = root / ("dist/windows/onefile/YT Channel Downloader.exe" if args.backend == "pyinstaller" else "dist/windows/cxfreeze/YT Channel Downloader")
    payload = (args.payload or default).resolve()
    executable = payload if args.backend == "pyinstaller" else payload / "YT Channel Downloader.exe"
    if not executable.is_file() or (args.backend == "cxfreeze" and not (payload / "lib").is_dir()):
        parser.error(f"Build the {args.backend} application first; the payload is missing: {payload}")
    try:
        if executable_version(executable) != windows_version:
            parser.error("The payload version differs from _release.py; rebuild the application first")
    except ValueError as error:
        parser.error(str(error))
    if args.backend == "pyinstaller":
        files = [(executable, Path("YT Channel Downloader.exe"))]
    else:
        files = [(path.resolve(), path.relative_to(payload)) for path in sorted(payload.rglob("*")) if path.is_file()]
        if any(not path.is_relative_to(payload) for path, _ in files):
            parser.error("The bundle contains a link outside its directory")
    build_dir = root / "build/windows/nsis" / args.backend
    output = root / "dist/windows/installers" / f"YT-Channel-Downloader-{version}-{args.backend}-setup.exe"
    helper = root / "packaging/windows/install_dependencies.ps1"
    definitions = {}
    if args.test_root:
        test_root = args.test_root.resolve()
        if not test_root.is_relative_to(root / "build/windows/nsis/tests"):
            parser.error("Test installers must stay under build/windows/nsis/tests")
        build_dir = test_root / "generated"
        output = test_root / f"{args.backend}-setup.exe"
        helper = test_root / "dependency-wrapper.ps1"
        if not helper.is_file():
            parser.error("The isolated test dependency wrapper is missing")
        definitions.update(APP_TEST_ROOT=str(test_root), APP_TEST_ID=hashlib.sha256(str(test_root).encode()).hexdigest()[:16])
    build_dir.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload_include = build_dir / "payload.nsh"
    write_payload(payload_include, files)
    definitions.update(
        APP_VERSION=version,
        APP_WINDOWS_VERSION=".".join(map(str, windows_version)),
        APP_DENO_MIN_VERSION=".".join(map(str, minima["deno"])),
        APP_NODE_MIN_VERSION=".".join(map(str, minima["node"])),
        APP_ICON=str(root / "packaging/icons/icon.ico"),
        APP_PAYLOAD_INCLUDE=str(payload_include),
        APP_DEPENDENCY_HELPER=str(helper),
        APP_INSTALLER_OUTPUT=str(output),
        APP_ESTIMATED_SIZE=str((sum(path.stat().st_size for path, _ in files) + 1023) // 1024),
    )
    config = build_dir / "config.nsh"
    config.write_text("".join(f'!define {key} "{nsi_escape(value, runtime=key == "APP_TEST_ROOT")}"\n' for key, value in definitions.items()), encoding="utf-8")
    if args.prepare_only:
        print(f"Prepared: {config}")
        return
    if not args.test_root:
        write_legacy_aliases(root)
    try:
        compiler = find_compiler(args.makensis)
    except ValueError as error:
        parser.error(str(error))
    subprocess.run([
        str(compiler), "/V2", "/WX", "/DAPP_BUILD_CONFIG=" + str(config),
        str(root / "packaging/windows" / f"installer_{args.backend}.nsi"),
    ], check=True)
    with output.open("rb") as stream:
        checksum = hashlib.file_digest(stream, "sha256").hexdigest()
    print(f"Built: {output}")
    print(f"SHA256: {checksum}")


if __name__ == "__main__":
    main()
