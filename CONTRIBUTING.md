# Contributing Guidelines

First of all, thank you for your interest in contributing!  
This project welcomes bug reports, feature requests, documentation improvements, and code contributions of all sizes.

---

## How to Contribute

1. **Fork & Branch**
   - Fork the repository on GitHub.
   - Create a new branch for your change:

     ```bash
     git checkout -b fix/name-of-the-fix
     ```

2. **Make Your Changes**
   - Follow existing code style and conventions.
   - For documentation, please keep formatting consistent with surrounding text.

3. **Commit Messages**
   - Use clear, descriptive commit messages.
   - Examples:

     ```
     feat(core): add download support for vimeo
     feat(ui): implement dark mode toggle
     fix(ui): ...
     refactor(core): simplify config parser
     test(ui): snapshot tests for dark mode
     ```

     To read more, check out [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).

4. **Pull Requests**
   - Open a pull request (PR) against the `main` branch.
   - Provide a short description of what your change does and why it’s useful.
   - Be ready to discuss and make adjustments based on reviewer feedback.

---

## Development setup

Use **Python 3.11 or newer**. Install the external dependencies listed in the
[README requirements](README.md#requirements) to run the app or try real downloads.
From the repository root, create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

For Windows PowerShell, use `py -3 -m venv .venv` and
`.\.venv\Scripts\Activate.ps1`, then run the same pip commands. An existing
Python 3.11+ environment can be used instead.

Run the app with `python -m yt_channel_downloader`. Installing the project in
editable mode also provides the `yt-channel-downloader` command and makes source
edits available without reinstalling. Reinstall after changing dependencies or
release metadata.

## Tests and UI changes

Run the test suite from the repository root:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest -q
python -m pip check
```

In PowerShell, set `$env:QT_QPA_PLATFORM = "offscreen"` before running
`python -m pytest -q`. The tests use mocked providers and do not require live
YouTube access. GitHub Actions runs the suite and builds the Python distributions
on Python 3.11, 3.12, 3.13, and 3.14 on pushes and pull requests.

Edit Qt Designer files under `src/yt_channel_downloader/ui/` and regenerate the
matching Python file, for example:

```bash
pyuic6 src/yt_channel_downloader/ui/about.ui -o src/yt_channel_downloader/ui/ui_about.py
```

Commit both files. Keep `{version}` and `{release_date}` in the About template;
the application fills them from the shared release metadata.

## Preparing a release

Update the version and ISO release date in
[`src/yt_channel_downloader/_release.py`](src/yt_channel_downloader/_release.py).
Setuptools reads the package version from this module, and the About dialog reads
both values at runtime. Update the release notes and dates in `CHANGELOG.md` and
`README.md`, then reinstall the editable project and run the checks above.

Build a wheel and source distribution with:

```bash
python -m pip install --upgrade build
python -m build
```

To create a bundled executable, install PyInstaller in the same environment and
run the following command from the repository root on each target operating
system:

```bash
python -m pip install --upgrade pyinstaller
python -m PyInstaller --noconsole --onefile --clean --noupx --name yt-channel-downloader --paths src --icon packaging/icons/icon.ico --collect-all yt_channel_downloader --collect-all yt_dlp_ejs --recursive-copy-metadata yt-dlp src/yt_channel_downloader/__main__.py
```

The executable is written to `dist/yt-channel-downloader` (`.exe` on Windows).
On macOS, use `--icon packaging/icons/icon.icns` in the command above.
FFmpeg and a supported JavaScript runtime remain external requirements. The
command generates an ignored `.spec` file. Local packaging shell scripts and
spec files remain ignored and are not part of a fresh clone; keep any local
customizations separately. The local scripts accept `YT_DL_PYTHON` to select a
Python 3.11+ interpreter explicitly.

### Automated Linux and macOS releases

The **Linux desktop packages** and **macOS desktop packages** GitHub Actions
workflows can be started from **Actions → Run workflow**. Manual runs save
downloadable artifacts for 30 days. Publishing a GitHub release also starts both
workflows; validated packages, build information, and SHA-256 checksums are then
attached to that release. These workflows do not commit or push source changes.

Set an `X.Y.Z` version in `_release.py` and publish the corresponding `vX.Y.Z`
release from a commit containing the workflows and packaging scripts. A mismatched
release tag fails before the application is built. Existing Python CI continues
to test and build wheels and source distributions separately.

The Linux workflow builds a frozen Python 3.13/cx_Freeze application on Ubuntu
22.04 x86_64, then packages that same folder into **AppImage, DEB, and RPM**.
DEB and RPM metadata are generated directly; no RPM-to-DEB conversion is used.
It checks the real Qt X11 platform plugin under Xvfb, extracts and checks the
AppImage, and installs, launches, and removes the native packages in fresh
Ubuntu 22.04, Ubuntu 24.04, Debian 12, and Fedora 44 containers. All Linux checks
must pass before release assets are uploaded. The compatibility baseline is
glibc 2.35; other distributions and display stacks require separate testing.

The macOS workflow builds separate **Apple Silicon (`arm64`)** and **Intel
(`x86_64`)** application bundles and DMGs on macOS 15. The declared minimum is
macOS 15. Each DMG is mounted and the executable inside it is checked before the
artifact is uploaded. Both architectures must succeed before release uploads.

To enable Developer ID signing and notarization, set all six repository Actions
secrets:

- `MACOS_CERTIFICATE_P12_BASE64`: base64-encoded Developer ID Application
  certificate and its private key, exported as a `.p12` file.
- `MACOS_CERTIFICATE_PASSWORD`: password protecting that `.p12` file.
- `MACOS_SIGNING_IDENTITY`: full Developer ID Application signing identity.
- `APPLE_ID`: Apple Developer account email.
- `APPLE_APP_SPECIFIC_PASSWORD`: app-specific password for notarization.
- `APPLE_TEAM_ID`: Apple Developer team identifier.

With these secrets, the workflow signs bundled native code and the DMG, submits
the DMG to Apple, staples and validates its ticket, and checks Gatekeeper
acceptance. Temporary certificate files and keychains are cleaned up. Supplying
only some of the secrets fails the build. With no signing secrets, it builds an
ad-hoc-signed app in a clearly named `-unsigned.dmg`; this is useful for testing
but does not provide Developer ID or notarization for public distribution.

All bundles contain Python, Qt, yt-dlp, EJS, and the app's Python dependencies.
DEB/RPM packages require system FFmpeg/ffprobe and recommend a supported
JavaScript runtime where available. AppImage and macOS users install FFmpeg,
ffprobe, and Deno 2.3+ or Node.js 22+ separately. The macOS launcher also searches
the usual Homebrew binary directories; Unix launchers include `~/.deno/bin`
when it exists. These packages do not establish APT/DNF repositories or automatic
package-manager updates.

For local builds, install the project and `cx-Freeze==8.7.4` in a virtual
environment on the target OS. Use the system tools listed in the relevant
workflow, then run:

```bash
# Linux x86_64
python scripts/build_unix_cxfreeze.py build_exe
python scripts/smoke_unix_bundle.py build/linux/cxfreeze/x86_64/app/yt-channel-downloader
python scripts/package_linux.py

# macOS (builds for the architecture of the current Python interpreter)
python scripts/build_unix_cxfreeze.py bdist_mac
python scripts/package_macos.py
```

Outputs are under `dist/linux/` and `dist/macos/`. Build information records the
actual bundled dependency versions. Rebuild releases when yt-dlp needs fixes for
website changes. The `--verify-bundle` diagnostic exercises package metadata,
TLS certificates, extractor and EJS resources, a local HTTP download, Qt resources,
and threading with temporary settings. It does not contact YouTube or test live
challenge solving, browser cookies, or FFmpeg conversions.

### Windows builds

The Windows build helper adds executable version information from
`src/yt_channel_downloader/_release.py`, disables UPX, and prints the executable's
SHA-256 hash. Install PyInstaller in `.venv`, then run:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows.py --layout onefile
```

The executable is written to `dist/windows/onefile/YT Channel Downloader.exe`.
To build a folder bundle for an installer or to compare antivirus detections:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows.py --layout onedir
```

This writes `dist/windows/onedir/YT Channel Downloader/`. Distribute the entire
folder, including `_internal`, in an installer or ZIP archive. Folder bundles
load their dependencies from that folder instead of extracting them on launch.
The helper keeps build files under `build/windows/` and does not replace the
output of the generic command above.

Antivirus detections can persist with either layout. Version metadata and
`--noupx` do not guarantee a clean scan; `--noupx` has no effect if UPX was not
installed. Sign release executables and installers with your publisher's
Authenticode certificate when available. Report suspected false positives on
the final artifact to [Microsoft Security Intelligence](https://www.microsoft.com/en-us/wdsi/filesubmission)
and the other detecting vendors, such as [Bkav support](https://www.bkav.com/en/support).
[VirusTotal's guidance](https://docs.virustotal.com/docs/false-positive) explains
that each vendor controls its own verdict. Reanalyse the final artifact after
the vendor has reviewed it.

### Windows builds with cx_Freeze

cx_Freeze provides an alternative folder bundle and a per-user MSI installer.
The build reads the version from `src/yt_channel_downloader/_release.py` and
includes the app's resources, yt-dlp extractors, EJS scripts, package metadata,
and the Visual C++ runtime. With the project installed in `.venv`, run:

```powershell
.\.venv\Scripts\python.exe -m pip install cx-Freeze==8.7.4
.\.venv\Scripts\python.exe scripts\build_windows_cxfreeze.py bdist_msi
```

The installer is written to `dist/windows/cxfreeze/` and the folder bundle to
`dist/windows/cxfreeze/YT Channel Downloader/`. To build only the folder bundle,
use `build_exe` instead of `bdist_msi`. Distribute the entire folder, including
`lib` and the accompanying DLLs. FFmpeg, ffprobe, and a supported JavaScript
runtime remain external requirements.

To verify the frozen dependencies in a separate diagnostic build:

```powershell
.\.venv\Scripts\python.exe scripts\build_windows_cxfreeze.py --probe build_exe
.\build\windows\cxfreeze\probe\verify-bundle.exe
```

The diagnostic checks package metadata, TLS certificates, dynamic extractors,
EJS resources, Qt window creation, icons, and Qt thread signals. It also downloads
a generated WAV file from a temporary local HTTP server. Settings and logs use
a temporary directory, and browser-cookie access and automatic update checks are
disabled for the diagnostic. Live YouTube challenge solving and FFmpeg
conversions require separate testing. The diagnostic executable is kept under
`build/` and is not included in the MSI.

### NSIS installers with prerequisite setup

Install NSIS 3, then use the appropriate entry point for the application bundle:

```powershell
# PyInstaller one-file payload
.\.venv\Scripts\python.exe scripts\build_windows.py --layout onefile
.\.venv\Scripts\python.exe scripts\build_windows_installer.py --backend pyinstaller

# cx_Freeze complete folder payload
.\.venv\Scripts\python.exe scripts\build_windows_cxfreeze.py build_exe
.\.venv\Scripts\python.exe scripts\build_windows_installer.py --backend cxfreeze
```

Skip rebuilding the application if the existing payload already matches the
version in `_release.py`. The installer helper rejects missing or mismatched
Windows version metadata. Pass `--makensis PATH` if the compiler is not in
`PATH` or either standard NSIS installation directory.

The setup executables are written to `dist/windows/installers/` with the version
and backend in their filenames. Both install the app under Program Files, request
administrator access, and use the shared prerequisite helper to:

- Verify that both `ffmpeg` and `ffprobe` execute successfully, downloading and
  installing a new pair if either is missing or broken.
- Accept Deno 2.3.0+ or Node.js 22.0.0+; install Deno if neither is supported.
- Verify archive SHA-256 checksums, check the downloaded executables, and add
  managed tool directories to the machine `PATH`.
- Abort before replacing application files if prerequisite setup fails.

Missing tools require internet access. Existing supported tools are reused.
FFmpeg and Deno installed by this helper are shared installations under Program
Files and are retained when the app is uninstalled. Uninstall removes the bundled
application files and empty directories while preserving unrelated user files.
Uninstall a previous build before changing between the one-file and folder
formats so obsolete files from the other format are removed.

The tracked sources are `packaging/windows/installer_pyinstaller.nsi`,
`installer_cxfreeze.nsi`, `installer_common.nsh`, and `install_dependencies.ps1`.
Compiler inputs and exact install/uninstall file lists are generated under
`build/windows/nsis/`. Direct compilation of either tracked `.nsi` also runs the
preparation helper using `.venv`. The historical `dist/mk_installer_ffmpeg.nsi`
and the new `dist/mk_installer_cxfreeze.nsi` are generated compatibility entry
points; edit the tracked sources rather than these ignored aliases.

The plain cx_Freeze MSI and portable ZIP do not run prerequisite setup. Use the
NSIS setup executable for automatic installation of external tools.

Run the Windows installer integration tests with:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_windows_installer.py -v
```

These tests compile small fixture installers and run setup/uninstall under
`build/windows/nsis/tests/`, use a temporary HKCU registry namespace and local
HTTP downloads, and leave the machine `PATH` unchanged. Other platforms and
Windows machines without NSIS skip these tests.

---

## Credits and Attribution

This project uses **two different ways** of recognizing contributions:

1. **GitHub Contributors**  
   GitHub automatically tracks everyone who has commits merged into the main branch. All changes, however small or big, will appear in GitHub’s [Contributors](https://github.com/hyperfield/yt-channel-downloader/graphs/contributors) tab. This is automatic and requires no action on your part.

2. **Project Credits (e.g. the About dialog)**  
   The credits displayed inside the app or project documentation are curated manually.  
   - Typically included: core maintainers, major feature authors, long-term or repeated contributors.  
   - Typically not included: very small changes such as typo fixes, whitespace cleanups, or single-line edits.
   - This helps keep the in-app/project credits meaningful and fair to all contributors.

---

## Questions?

Feel free to open a GitHub Issue or start a Discussion if you’d like to ask a question before contributing.
