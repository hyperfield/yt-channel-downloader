"""Isolated prerequisite and NSIS integration tests; never install into Program Files."""

import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from functools import partial
import zipfile


ROOT = Path(__file__).resolve().parents[1]
NSIS = Path("C:/Program Files (x86)/NSIS/makensis.exe")
APP_EXE = "YT Channel Downloader.exe"


def ps_literal(value):
    return "'" + str(value).replace("'", "''") + "'"


@unittest.skipUnless(sys.platform == "win32" and NSIS.is_file(), "Windows and NSIS are required")
class WindowsInstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        parent = ROOT / "build/windows/nsis/tests"
        parent.mkdir(parents=True, exist_ok=True)
        cls.temporary = tempfile.TemporaryDirectory(prefix="run with spaces $-", dir=parent)
        cls.directory = Path(cls.temporary.name).resolve()
        cls.version = runpy.run_path(str(ROOT / "src/yt_channel_downloader/_release.py"))["__version__"]
        cls.tool = cls.compile_tool("current.exe", "2.9.8", "22.0.0", cls.version)
        cls.old_tool = cls.compile_tool("old.exe", "2.2.0", "21.0.0", cls.version)
        cls.old_app = cls.compile_tool("old-app.exe", "2.9.8", "22.0.0", "0.8.8")
        archives = cls.directory / "archives"
        archives.mkdir()
        with zipfile.ZipFile(archives / "ffmpeg.zip", "w") as archive:
            archive.write(cls.tool, "ffmpeg-test/bin/ffmpeg.exe")
            archive.write(cls.tool, "ffmpeg-test/bin/ffprobe.exe")
            archive.writestr("ffmpeg-test/LICENSE", "Fixture license")
        with zipfile.ZipFile(archives / "deno.zip", "w") as archive:
            archive.write(cls.tool, "deno.exe")
        with zipfile.ZipFile(archives / "invalid.zip", "w") as archive:
            archive.writestr("bin/ffmpeg.exe", "not an executable")
            archive.writestr("bin/ffprobe.exe", "not an executable")

        class Handler(SimpleHTTPRequestHandler):
            def log_message(self, *args):
                pass

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(archives)))
        cls.server_thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.server_thread.start()
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.hashes = {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in archives.iterdir()}

    @classmethod
    def compile_tool(cls, filename, deno, node, version):
        output = cls.directory / filename
        source = f'''
using System;
using System.IO;
using System.Reflection;
[assembly: AssemblyVersion("{version}.0")]
[assembly: AssemblyFileVersion("{version}.0")]
public class Tool {{
    public static int Main(string[] args) {{
        string name = Path.GetFileNameWithoutExtension(Assembly.GetExecutingAssembly().Location).ToLowerInvariant();
        if (name == "ffmpeg" || name == "ffprobe") Console.WriteLine(name + " version 6.1.1");
        else if (name == "deno") Console.WriteLine("deno {deno}");
        else if (name == "node") Console.WriteLine("v{node}");
        else Console.WriteLine("Installer test fixture");
        return 0;
    }}
}}
'''
        script = cls.directory / (filename + ".ps1")
        script.write_text("Add-Type -TypeDefinition @'\n" + source + "\n'@ -OutputType ConsoleApplication -OutputAssembly " + ps_literal(output), encoding="utf-8-sig")
        subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], check=True, capture_output=True)
        return output

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.server_thread.join(timeout=5)
        assert cls.directory.is_relative_to(ROOT / "build/windows/nsis/tests")
        cls.temporary.cleanup()

    def setUp(self):
        self.case = self.directory / self._testMethodName
        self.case.mkdir()
        self.tools = self.case / "tools"
        self.tools.mkdir()
        self.dependencies = self.case / "dependencies"
        self.registry_id = hashlib.sha256(str(self.case).encode()).hexdigest()[:16]
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            self.machine_path = winreg.QueryValueEx(key, "Path")[0]

    def tearDown(self):
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            self.assertEqual(winreg.QueryValueEx(key, "Path")[0], self.machine_path)
        key_name = "Software\\YTChannelDownloaderInstallerTests\\" + self.registry_id

        def delete_tree(name):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, name, 0, winreg.KEY_ALL_ACCESS) as key:
                    children = []
                    index = 0
                    while True:
                        try:
                            children.append(winreg.EnumKey(key, index))
                        except OSError:
                            break
                        index += 1
                for child in children:
                    delete_tree(name + "\\" + child)
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, name)
            except FileNotFoundError:
                pass

        self.assertTrue(key_name.startswith("Software\\YTChannelDownloaderInstallerTests\\"))
        delete_tree(key_name)

    def tool_at(self, directory, name, old=False):
        directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(self.old_tool if old else self.tool, directory / (name + ".exe"))

    def ffmpeg_pair(self):
        for name in ("ffmpeg", "ffprobe"):
            self.tool_at(self.dependencies / "FFmpeg/bin", name)

    def wrapper(self, *, ffmpeg="ffmpeg.zip", checksum=None, forbid_downloads=False, extra_tool_paths=()):
        helper = ROOT / "packaging/windows/install_dependencies.ps1"
        path = self.case / "dependency-wrapper.ps1"
        source = f'''
param([string]$InstallRoot, [string]$PathScope = 'Process', [version]$MinDenoVersion = '2.3.0', [version]$MinNodeVersion = '22.0.0', [switch]$InspectOnly)
$options = @{{ Root = $InstallRoot; Scope = $PathScope; DenoMinimum = $MinDenoVersion; NodeMinimum = $MinNodeVersion; InspectOnly = $InspectOnly }}
$env:Path = {ps_literal(';'.join(map(str, (self.tools, *extra_tool_paths))) + ';' + os.environ['SystemRoot'] + '/System32')}
. {ps_literal(helper)}
function Get-FfmpegRelease {{ return @{{ Url = '{self.base_url}/{ffmpeg}'; Sha256 = '{checksum or self.hashes[ffmpeg]}' }} }}
function Get-DenoRelease {{ return @{{ Url = '{self.base_url}/deno.zip'; Sha256 = '{self.hashes['deno.zip']}' }} }}
'''
        if forbid_downloads:
            source += "function Get-FfmpegRelease { throw 'Unexpected FFmpeg download' }\nfunction Get-DenoRelease { throw 'Unexpected Deno download' }\n"
        source += '''
try {
    $result = Invoke-DependencySetup @options
    Write-Output ('RESULT ' + ($result | ConvertTo-Json -Depth 4 -Compress))
    if ($result.Ready) { exit 0 } else { exit 1 }
} catch {
    Write-Output $_.Exception.Message
    exit 1
}
'''
        path.write_text(source, encoding="utf-8-sig")
        return path

    def dependencies_run(self, wrapper, inspect=False):
        command = ["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(wrapper), "-InstallRoot", str(self.dependencies)]
        if inspect:
            command.append("-InspectOnly")
        return subprocess.run(command, capture_output=True, text=True, errors="replace", timeout=60)

    def result(self, run):
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return json.loads(next(line[7:] for line in run.stdout.splitlines() if line.startswith("RESULT ")))

    def test_existing_supported_node_avoids_downloads(self):
        for name in ("ffmpeg", "ffprobe", "node"):
            self.tool_at(self.tools, name)
        state = self.result(self.dependencies_run(self.wrapper(forbid_downloads=True)))
        self.assertTrue(state["Ready"])
        self.assertEqual(state["Node"]["Version"], "22.0.0")
        self.assertIsNone(state["Deno"])

    def test_missing_ffprobe_repairs_both_ffmpeg_tools(self):
        self.tool_at(self.dependencies / "FFmpeg/bin", "ffmpeg")
        self.tool_at(self.tools, "node")
        wrapper = self.wrapper()
        self.assertNotEqual(self.dependencies_run(wrapper, inspect=True).returncode, 0)
        state = self.result(self.dependencies_run(wrapper))
        self.assertTrue((self.dependencies / "FFmpeg/bin/ffprobe.exe").is_file())
        self.assertEqual(Path(state["FFmpeg"]["Path"]).parent, self.dependencies / "FFmpeg/bin")
        self.assertEqual(state["Node"]["Version"], "22.0.0")

    def test_unsupported_js_runtimes_install_deno(self):
        self.ffmpeg_pair()
        self.tool_at(self.tools, "node", old=True)
        self.tool_at(self.tools, "deno", old=True)
        state = self.result(self.dependencies_run(self.wrapper()))
        self.assertEqual(state["Deno"]["Version"], "2.9.8")
        self.assertEqual(Path(state["Deno"]["Path"]), self.dependencies / "Deno/deno.exe")
        self.assertIsNone(state["Node"])

    def test_shadowed_unsupported_runtime_is_replaced(self):
        self.ffmpeg_pair()
        self.tool_at(self.tools, "deno", old=True)
        newer_tools = self.case / "newer-tools"
        self.tool_at(newer_tools, "deno")
        state = self.result(self.dependencies_run(self.wrapper(extra_tool_paths=(newer_tools,))))
        self.assertEqual(Path(state["Deno"]["Path"]), self.dependencies / "Deno/deno.exe")
        self.assertTrue(state["Ready"])

    def test_bad_checksum_preserves_existing_ffmpeg(self):
        self.tool_at(self.dependencies / "FFmpeg/bin", "ffmpeg", old=True)
        self.tool_at(self.tools, "node")
        before = (self.dependencies / "FFmpeg/bin/ffmpeg.exe").read_bytes()
        run = self.dependencies_run(self.wrapper(checksum="0" * 64))
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("checksum", run.stdout)
        self.assertEqual((self.dependencies / "FFmpeg/bin/ffmpeg.exe").read_bytes(), before)
        self.assertFalse((self.dependencies / "FFmpeg/bin/ffprobe.exe").exists())

    def test_invalid_download_is_not_installed(self):
        self.tool_at(self.tools, "node")
        run = self.dependencies_run(self.wrapper(ffmpeg="invalid.zip"))
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("did not run successfully", run.stdout)
        self.assertFalse((self.dependencies / "FFmpeg/bin/ffmpeg.exe").exists())

    def compile_installer(self, backend, wrapper):
        if backend == "pyinstaller":
            payload = self.case / "payload.exe"
            shutil.copy2(self.tool, payload)
        else:
            payload = self.case / "payload"
            (payload / "lib/nested").mkdir(parents=True)
            shutil.copy2(self.tool, payload / APP_EXE)
            (payload / "lib/nested/file$option.txt").write_text("nested fixture")
            (payload / "lib/test.dll").write_text("dependency fixture")
        run = subprocess.run([
            sys.executable, str(ROOT / "scripts/build_windows_installer.py"),
            "--backend", backend, "--payload", str(payload), "--test-root", str(self.case),
        ], capture_output=True, text=True, errors="replace", timeout=90)
        self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
        return self.case / (backend + "-setup.exe"), payload

    def installer_roundtrip(self, backend):
        self.ffmpeg_pair()
        self.tool_at(self.dependencies / "Deno", "deno")
        installer, payload = self.compile_installer(backend, self.wrapper(forbid_downloads=True))
        installed = self.case / "app"
        run = subprocess.run([str(installer), "/S"], timeout=60)
        self.assertEqual(run.returncode, 0)
        expected = payload if payload.is_file() else payload / APP_EXE
        self.assertEqual((installed / APP_EXE).read_bytes(), expected.read_bytes())
        if backend == "cxfreeze":
            self.assertEqual((installed / "lib/nested/file$option.txt").read_text(), "nested fixture")
        import winreg
        key_name = "Software\\YTChannelDownloaderInstallerTests\\" + self.registry_id + "\\Uninstall"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name) as key:
            self.assertEqual(winreg.QueryValueEx(key, "DisplayVersion")[0], self.version)
        (installed / "preserve-me.txt").write_text("user file")
        subprocess.run([str(installed / "uninstall.exe"), "/S"], timeout=30)
        deadline = time.monotonic() + 20
        while (installed / "uninstall.exe").exists() and time.monotonic() < deadline:
            time.sleep(0.1)
        self.assertFalse((installed / APP_EXE).exists())
        self.assertFalse((installed / "lib").exists())
        self.assertEqual((installed / "preserve-me.txt").read_text(), "user file")
        self.assertTrue((self.dependencies / "Deno/deno.exe").exists())
        with self.assertRaises(FileNotFoundError):
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_name)

    def test_pyinstaller_setup_and_uninstall(self):
        self.installer_roundtrip("pyinstaller")

    def test_cxfreeze_setup_and_uninstall(self):
        self.installer_roundtrip("cxfreeze")

    def test_dependency_failure_does_not_replace_application(self):
        wrapper = self.wrapper(checksum="0" * 64)
        installer, _ = self.compile_installer("pyinstaller", wrapper)
        installed = self.case / "app"
        installed.mkdir()
        (installed / APP_EXE).write_bytes(b"previous application")
        run = subprocess.run([str(installer), "/S"], timeout=60)
        self.assertNotEqual(run.returncode, 0)
        self.assertEqual((installed / APP_EXE).read_bytes(), b"previous application")
        self.assertFalse((installed / "uninstall.exe").exists())

    def test_old_application_version_is_rejected(self):
        self.wrapper()
        run = subprocess.run([
            sys.executable, str(ROOT / "scripts/build_windows_installer.py"),
            "--backend", "pyinstaller", "--payload", str(self.old_app), "--test-root", str(self.case),
        ], capture_output=True, text=True, errors="replace", timeout=15)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("payload version differs", run.stderr)


if __name__ == "__main__":
    unittest.main()
