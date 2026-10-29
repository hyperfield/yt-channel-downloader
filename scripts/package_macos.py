"""Create and verify a DMG, optionally signing and notarizing with Apple."""

import base64
import json
import os
from pathlib import Path
import plistlib
import secrets
import shlex
import subprocess
import sys
import tempfile

from desktop_release import APP_NAME, PACKAGE, ROOT, architecture, release_version, write_build_info, write_checksums
from smoke_unix_bundle import check


SIGNING_SECRETS = (
    "MACOS_CERTIFICATE_P12_BASE64", "MACOS_CERTIFICATE_PASSWORD", "MACOS_SIGNING_IDENTITY",
    "APPLE_ID", "APPLE_APP_SPECIFIC_PASSWORD", "APPLE_TEAM_ID",
)
MACHO_MAGIC = {bytes.fromhex(value) for value in (
    "feedface", "feedfacf", "cefaedfe", "cffaedfe", "cafebabe", "bebafeca", "cafebabf", "bfbafeca",
)}


def signing_credentials(environment):
    values = {name: environment.get(name, "") for name in SIGNING_SECRETS}
    if any(values.values()) and not all(values.values()):
        raise ValueError("Partial macOS signing configuration; supply all six documented signing secrets")
    return values if all(values.values()) else None


def run(command, label):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        detail = result.stdout + result.stderr
        for name in SIGNING_SECRETS:
            value = os.environ.get(name, "")
            if value:
                detail = detail.replace(value, "***")
        raise RuntimeError(f"{label} failed: {detail}")
    return result.stdout


def sign_app(app, identity, keychain):
    flags = [
        "codesign", "--force", "--sign", identity, "--keychain", str(keychain),
        "--timestamp", "--options", "runtime", "--entitlements", str(ROOT / "packaging/macos/entitlements.plist"),
    ]
    binaries = []
    for path in app.rglob("*"):
        if path.is_file() and not path.is_symlink():
            with path.open("rb") as stream:
                if stream.read(4) in MACHO_MAGIC:
                    binaries.append(path)
    for path in sorted(binaries, key=lambda path: len(path.parts), reverse=True):
        run([*flags, str(path)], "Signing bundled binary")
    bundles = [path for path in app.rglob("*") if path.is_dir() and not path.is_symlink() and path.suffix in (".framework", ".app", ".xpc")]
    for path in [*sorted(bundles, key=lambda path: len(path.parts), reverse=True), app]:
        run([*flags, str(path)], "Signing bundle")
    run(["codesign", "--verify", "--deep", "--strict", str(app)], "Verifying app signature")


def build_dmg(app, destination, credentials, directory):
    stage = directory / "image"
    stage.mkdir()
    run(["ditto", str(app), str(stage / app.name)], "Staging macOS app")
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    command = ["hdiutil", "create", "-volname", APP_NAME, "-srcfolder", str(stage), "-format", "UDZO", "-ov", str(destination)]
    if not credentials:
        run(command, "Creating unsigned DMG")
        return
    keychain = directory / "signing.keychain-db"
    certificate = directory / "certificate.p12"
    certificate.write_bytes(base64.b64decode("".join(credentials["MACOS_CERTIFICATE_P12_BASE64"].split()), validate=True))
    certificate.chmod(0o600)
    password = secrets.token_urlsafe(32)
    previous = shlex.split(run(["security", "list-keychains", "-d", "user"], "Reading keychain search list"))
    try:
        run(["security", "create-keychain", "-p", password, str(keychain)], "Creating temporary signing keychain")
        run(["security", "set-keychain-settings", "-lut", "21600", str(keychain)], "Setting keychain timeout")
        run(["security", "unlock-keychain", "-p", password, str(keychain)], "Unlocking temporary keychain")
        run(["security", "import", str(certificate), "-k", str(keychain), "-P", credentials["MACOS_CERTIFICATE_PASSWORD"], "-T", "/usr/bin/codesign"], "Importing signing certificate")
        run(["security", "set-key-partition-list", "-S", "apple-tool:,apple:,codesign:", "-s", "-k", password, str(keychain)], "Allowing codesign access")
        sign_app(stage / app.name, credentials["MACOS_SIGNING_IDENTITY"], keychain)
        run(command, "Creating signed DMG")
        run(["codesign", "--force", "--sign", credentials["MACOS_SIGNING_IDENTITY"], "--keychain", str(keychain), "--timestamp", str(destination)], "Signing DMG")
        authentication = ["--apple-id", credentials["APPLE_ID"], "--password", credentials["APPLE_APP_SPECIFIC_PASSWORD"], "--team-id", credentials["APPLE_TEAM_ID"]]
        result = json.loads(run(["xcrun", "notarytool", "submit", str(destination), *authentication, "--wait", "--timeout", "30m", "--output-format", "json"], "Submitting DMG for notarization"))
        if result.get("status") != "Accepted":
            log = run(["xcrun", "notarytool", "log", result["id"], *authentication], "Reading notarization log")
            raise RuntimeError("Apple rejected notarization: " + log)
        run(["xcrun", "stapler", "staple", str(destination)], "Stapling notarization ticket")
        run(["xcrun", "stapler", "validate", str(destination)], "Validating notarization ticket")
    finally:
        try:
            subprocess.run(["security", "list-keychains", "-d", "user", "-s", *previous], check=True)
        finally:
            try:
                if keychain.exists():
                    subprocess.run(["security", "delete-keychain", str(keychain)], check=True)
            finally:
                certificate.unlink(missing_ok=True)


def main():
    if sys.platform != "darwin":
        raise SystemExit("Build the DMG on macOS")
    version, arch = release_version(), architecture()
    credentials = signing_credentials(os.environ)
    app = ROOT / "build/macos/cxfreeze" / arch / (APP_NAME + ".app")
    with (app / "Contents/Info.plist").open("rb") as stream:
        info = plistlib.load(stream)
    if info["CFBundleShortVersionString"] != version:
        raise ValueError("The macOS app version does not match _release.py")
    executable = app / "Contents/MacOS" / PACKAGE
    binary_arch = run(["lipo", "-archs", str(executable)], "Checking executable architecture").split()
    if arch not in binary_arch:
        raise ValueError(f"The executable does not contain {arch}")
    check(executable)
    output = ROOT / "dist/macos"
    output.mkdir(parents=True, exist_ok=True)
    label = "" if credentials else "-unsigned"
    dmg = output / f"YT-Channel-Downloader-{version}-macos-{arch}{label}.dmg"
    with tempfile.TemporaryDirectory(prefix="ytcd-dmg-") as temporary:
        directory = Path(temporary)
        build_dmg(app, dmg, credentials, directory)
        mount = directory / "mounted"
        mount.mkdir()
        run(["hdiutil", "attach", str(dmg), "-nobrowse", "-readonly", "-mountpoint", str(mount)], "Mounting final DMG")
        try:
            mounted_app = mount / app.name
            if credentials:
                run(["codesign", "--verify", "--deep", "--strict", str(mounted_app)], "Verifying installed app signature")
                run(["spctl", "--assess", "--type", "execute", str(mounted_app)], "Checking Gatekeeper acceptance")
            check(mounted_app / "Contents/MacOS" / PACKAGE)
        finally:
            run(["hdiutil", "detach", str(mount)], "Unmounting DMG")
    manifest = output / f"BUILD-INFO-macos-{arch}-{version}.json"
    write_build_info(manifest, developer_id_signed=bool(credentials), notarized=bool(credentials), minimum_macos="15.0")
    write_checksums([dmg, manifest], output / f"SHA256SUMS-macos-{arch}.txt")
    print(dmg)


if __name__ == "__main__":
    main()
