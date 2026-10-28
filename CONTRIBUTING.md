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

Use **Python 3.14 or newer**. Install the external dependencies listed in the
[README requirements](README.md#requirements) to run the app or try real downloads.
From the repository root, create and activate a virtual environment:

```bash
python3.14 -m venv .venv314
source .venv314/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test]'
```

For Windows PowerShell, use `py -3.14 -m venv .venv314` and
`.\.venv314\Scripts\Activate.ps1`, then run the same pip commands. An existing
Python 3.14+ environment can be used instead.

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
YouTube access. GitHub Actions runs the suite on Python 3.14 and builds the Python
distributions on pushes and pull requests.

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
python -m PyInstaller --noconsole --onefile --clean --name yt-channel-downloader --paths src --icon packaging/icons/icon.ico --collect-all yt_channel_downloader --collect-all yt_dlp_ejs --recursive-copy-metadata yt-dlp src/yt_channel_downloader/__main__.py
```

The executable is written to `dist/yt-channel-downloader` (`.exe` on Windows).
On macOS, use `--icon packaging/icons/icon.icns` in the command above.
FFmpeg and a supported JavaScript runtime remain external requirements. The
command generates an ignored `.spec` file. Local packaging shell scripts and
spec files remain ignored and are not part of a fresh clone; keep any local
customizations separately. The local scripts accept `YT_DL_PYTHON` to select a
Python 3.14+ interpreter explicitly.

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
