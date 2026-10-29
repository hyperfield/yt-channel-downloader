"""Check a frozen executable or an extracted AppImage with a real Qt display."""

import argparse
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time


def check(executable, *, appimage=False):
    executable = Path(executable).resolve(strict=True)
    environment = os.environ.copy()
    with tempfile.TemporaryDirectory(prefix="ytcd-smoke-") as temporary:
        directory = Path(temporary)
        if appimage:
            subprocess.run([str(executable), "--appimage-extract"], cwd=directory, check=True, stdout=subprocess.DEVNULL)
            executable = directory / "squashfs-root/AppRun"
        server = None
        try:
            if sys.platform == "linux":
                # Let Xvfb choose an unused display; this also works on RPM distros
                # that do not ship the xvfb-run shell wrapper.
                with (directory / "display").open("w+b") as display:
                    server = subprocess.Popen([
                        "Xvfb", "-displayfd", str(display.fileno()), "-screen", "0", "1280x800x24",
                        "-nolisten", "tcp", "-ac",
                    ], pass_fds=(display.fileno(),), stdout=subprocess.DEVNULL)
                    deadline = time.monotonic() + 15
                    number = b""
                    while time.monotonic() < deadline:
                        display.seek(0)
                        number = display.read().strip()
                        if number or server.poll() is not None:
                            break
                        time.sleep(0.1)
                    if not number.isdigit():
                        raise RuntimeError("Xvfb did not start")
                environment.update(DISPLAY=":" + number.decode("ascii"), QT_QPA_PLATFORM="xcb")
            else:
                environment["QT_QPA_PLATFORM"] = "offscreen"
            subprocess.run([str(executable), "--verify-bundle"], env=environment, check=True, timeout=120)
        finally:
            if server is not None:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("executable", type=Path)
    parser.add_argument("--appimage", action="store_true")
    args = parser.parse_args()
    if sys.platform not in ("linux", "darwin"):
        parser.error("This smoke test runs on Linux or macOS")
    check(args.executable, appimage=args.appimage)
