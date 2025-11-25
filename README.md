# YT Channel Downloader

[![Version](https://img.shields.io/badge/Version-0.7.0-green)](#) [![Codacy Badge](https://app.codacy.com/project/badge/Grade/d941f316b7ba45a4aa9114f029ca4a0b)](https://app.codacy.com/gh/hyperfield/yt-channel-downloader/dashboard?utm_source=gh&utm_medium=referral&utm_content=&utm_campaign=Badge_grade) [![Donate via Ko-Fi](https://img.shields.io/badge/Donate-Ko--Fi-FF5E5B?logo=kofi&logoColor=white)](https://ko-fi.com/hyperfield) [![Download YT Channel Downloader](https://img.shields.io/sourceforge/dt/yt-channel-downloader.svg)](https://sourceforge.net/projects/yt-channel-downloader/files/latest/download) [![Download YT Channel Downloader](https://img.shields.io/sourceforge/dw/yt-channel-downloader.svg)](https://sourceforge.net/projects/yt-channel-downloader/files/latest/download)

[![Download YT Channel Downloader](https://a.fsdn.com/con/app/sf-download-button)](https://sourceforge.net/projects/yt-channel-downloader/files/latest/download)

**YT Channel Downloader** is an intuitive desktop application built to simplify the process of downloading YouTube media content. Leveraging the robustness of [yt-dlp](https://github.com/yt-dlp/yt-dlp) and enriched with a modern PyQt 6 GUI, this tool offers a seamless experience to download your favorite content.

![YT Channel Downloader Screenshot (Windows)](docs/images/screenshot_win.png)
![YT Channel Downloader Screenshot (Linux)](docs/images/screenshot_lin.png)
![YT Channel Downloader Screenshot (MacOS)](docs/images/screenshot_mac.png)

---

- [Change Log](#change-log)
- [Binaries](#binaries)
- [Features](#features)
- [Installation](#installation)
  - [Install from PyPI](#install-from-pypi)
  - [MacOS or Linux (from source)](#macos-or-linux-from-source)
  - [Windows](#windows)
- [How to Use](#how-to-use)
- [Contributing](#contributing)
- [License](#license)
- [Authors](#authors)
- [Donation](#donation)

## Change Log

### What's New in version 0.6.0



### What's New in version 0.5.5

- Added a download speed indicator column.
- Added a column showing the duration of videos or audios.
- Added a check for updates.
- Removed `pytube`; playlists are now retrieved much faster via `yt_dlp`.
- Published on PyPI for easy installation with `pip`.
- First release to include binaries for macOS and Linux (Debian-compatible only for now).
- Reorganized the source into a `src/` layout for cleaner imports and packaging.
- Bug fixes and stability improvements.

### What's New in version 0.5.0

- **More sites!** You can now fetch single tracks or videos from other `yt-dlp`-supported platforms — including Vimeo (requires login), Twitch, SoundCloud, Facebook, Instagram, Twitter/X, TikTok, Udemy*, and Reddit — directly from the main URL field. (Bulk channel / playlist fetches remain YouTube-only. *Udemy still requires the appropriate credentials/cookies for premium content.)
- **YouTube Login and Logout**: Configure the browser profile whose cookies yt-dlp reuses for private, premium, or age-restricted downloads - no heavy-weight embedded browser anymore. Use `File -> YouTube login` to pick the browser and profile, and clear the configuration from the same menu when you no longer need it.
- **Download cancellation**: Downloads in progress can now be cancelled with the "Cancel downloads" button.

### What's New in version 0.4.12

- **Only the Windows installer changed**: updated `yt-dlp` to the latest version to fix a problem with unretrievable URLs.

### What's New in version 0.4.11

- **Fixed URL fetching bug**: short YouTube URLs are now fetched.
- **Cleanup**: a minor cleanup in some source files.

### What's New in version 0.4.10

- **Improved stability**: Bug fixes and improved exception handling.
- **Smoother UI**: The interface also got a small facelift with more consistent layouts and widget styles.

(Contributed by [djfm](https://github.com/djfm))

### What's New in version 0.4.8

- **FFmpeg installation verification**: Implemented a check for FFmpeg’s presence on the system, as it is required for media downloads. While the Windows installer already handled this by installing FFmpeg if missing, the source code version lacked this verification. (Contributed by [arvinnick](https://github.com/arvinnick)).

### What's New in version 0.4.6

- **Thumbnail downloads**: Added checkbox in Settings to enable thumbnail downloads for each video link. (Contributed by [dsasmblr](https://github.com/dsasmblr)).

### What's New in version 0.4.5

- **Fetch progress dialog**: Added an indefinite progress bar dialog window that displays the elapsed time in seconds and has a Cancel button.
- **Some refactoring**: Added numerous Python docstrings, introduced a new class, and reformatted the code for improved cleanliness and readability.

### What's New in version 0.4.2

- **Shorts support**: Downloading YouTube shorts now works.
- **Improved exception handling**: Improved handling of network and download errors, timeouts.

### What's New in version 0.4.1

- **Bug Fixes**: Due to some updates on YouTube, certain functionality didn't work. The "Any" format selection didn't work. These have been fixed.
- **Improved exception handling**: Some parts of the code needed exception handling.
- **Improved interface**: Better and bigger fonts and buttons.
- **Added the "Donate" item to the Help menu**: In the hope that some will support the author, which motivates faster improvement of the app.

### What's New in version 0.4.0

- **YouTube Login and Logout**: Configure the browser profile whose cookies yt-dlp should reuse for private or age-restricted downloads. Use `File -> YouTube login` to select the browser/profile, and choose “Clear YouTube login” to forget the configuration.
- **Minor Improvements and Bug Fixes**.

### What's New in version 0.3.3

- **Improved default audio track downloading**: the program will now always attempt to download the best available quality audio track. Previously, the associated audio track was not always downloaded, for 4k quality videos in particular.

### What's New in version 0.3.2

- **Fixed the handling of video resolutions and formats specified in Settings**: the program will correctly find the closest available video resolution and format based on user settings, for horizontal and vertical videos.

### What's New in version 0.3.1

- **Limiting of simultaneous download threads**: this improves the responsiveness of the application and optimizes its handling of large download lists.
- **Improved file name sanitation method**: this prevents some completed downloads not being marked as such.

### What's New in version 0.3.0

- **Download playlists**, in addition to channels or single videos
- **Select All** check box: allows to select all non-downloaded videos in a list at once
- **Bug fixes**: improved URL validation, partial download completion
- **Interface improvements**
- **Other improvements**: code cleanup, updated README

## Binaries

[Download the latest binary releases here.](https://github.com/hyperfield/yt-channel-downloader/releases)

## Features

- **Fetch Video Listings**: Just input a YouTube video, playlist or channel URL and get a list of the videos.
- **Selective Download**: Choose exactly which videos you want to download, or select all at once.
- **Quality Control**: Specify video/audio quality or opt to download only the associated audio track.
- **Download Marking**: Keeps track of downloaded files for easier management.
- **Playlist Downloads**: Download all or some videos from a playlist URL.
- **Channel Downloads**: Download all or some videos from a channel URL.
- **Single Video or Audio Downloads**: Paste any supported link (YouTube, Vimeo, Twitch, SoundCloud, Facebook, Instagram, Twitter/X, TikTok, Udemy*, Reddit, and more via yt-dlp) and download it.
- **Thumbnail Downloads**: Download thumbnails for each of your videos.
- **Private and Age-Restricted Videos**: Download media on behalf of your Youtube account.

\*Some providers (for example, Udemy or other premium services) still require valid account cookies/credentials. Configure them via `File -> YouTube login` (cookies-from-browser) before attempting restricted downloads.

### Coming Soon

- Search field to search within a retrieved list of videos
- Download history tracking
- Pre-download summary
- Interface improvements
- [Suggest a feature!](https://github.com/hyperfield/yt-channel-downloader/issues)

## Installation

### Install from PyPI

The easiest way to get the desktop app is straight from PyPI. Make sure FFmpeg is installed (see below), then run:

```bash
pip install yt-channel-downloader
```

If you don't have `pip`, you can use `python -m pip` instead.

To update the app to the latest version from PyPI:

```bash
pip install --upgrade yt-channel-downloader
yt-channel-downloader
```

### MacOS or Linux (from source)

`ffmpeg` is needed for the app to work correctly, so make sure you have it on your system. Check in your terminal emulator if `ffmpeg` is installed:

    ffmpeg -version

#### How to install `ffmpeg` on MacOS or Linux

You can download it from [FFmpeg's official site](https://ffmpeg.org/download.html) or install it from a repository according to your OS distribution.

On MacOS with [Homebew](https://brew.sh/):

    brew install ffmpeg

On Debian/Ubuntu:

    sudo apt update
    sudo apt install ffmpeg

On Fedora:

    sudo dnf install ffmpeg

On Arch Linux:

    sudo pacman -S ffmpeg

#### Recommended: JavaScript runtime (improves YouTube format coverage)

yt-dlp can use a JavaScript runtime to parse YouTube player code; having one installed reduces missing formats and silences runtime warnings. Install any of:

- **Node.js** via your package manager:
  - Debian/Ubuntu: `sudo apt update && sudo apt install nodejs npm`
  - Fedora: `sudo dnf install nodejs npm`
  - Arch Linux: `sudo pacman -S nodejs npm`
  - macOS (Homebrew): `brew install node`
- **Deno** (alternative runtime): see install instructions at [deno.com](https://deno.com/)

#### Install YT Channel Downloader

##### Clone the repository

    git clone https://github.com/hyperfield/yt-channel-downloader.git

##### Navigate into the directory

    cd yt-channel-downloader

##### Create a virtual environment

    python3 -m venv .venv

##### Activate the virtual environment

    .venv/bin/activate

##### Install the project in editable mode

    pip install -e .

##### Run the program

    yt-channel-downloader

To deactivate the virtual environment after usage, type

    deactivate

### Windows

`ffmpeg` is needed for the app to work correctly, so make sure you have it on your system. Open the command line (`CMD`) and type

    ffmpeg -version

to check if it's on your system.

#### How to install `ffmpeg` on Windows

1. **Download `ffmpeg`**:
   - Visit the official [FFmpeg download page](https://ffmpeg.org/download.html).
   - Alternatively, you can use this direct link: [Download FFmpeg for Windows](https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip).

2. **Extract the files**:
   - Extract the downloaded archive to a directory, such as `C:\ffmpeg`.

3. **Add `ffmpeg` to your system PATH**:
   - Open the Start menu and search for "Environment Variables".
   - Select "Edit the system environment variables".
   - In the "System Properties" window, click on the "Environment Variables" button.
   - Under "System variables", find the `Path` variable and select it. Then click "Edit".
   - Click "New" and add `C:\ffmpeg\bin` to the list. Click "OK" to close all the windows.

4. **Verify the installation**:
   - Open Command Prompt (`CMD`).
   - Run the following command:

     ```sh
     ffmpeg -version
     ```

   - You should see the version information for `ffmpeg` if it is correctly installed.

#### Recommended: Node.js runtime (improves YouTube format coverage)

yt-dlp can use a JavaScript runtime to parse YouTube player code; having Node.js installed reduces missing formats and silences runtime warnings.

- Download and install the LTS version from [nodejs.org](https://nodejs.org/)
- Or with Chocolatey: `choco install nodejs-lts`
- Or with Scoop: `scoop install nodejs-lts`
- Alternative runtime: [Deno](https://deno.com/) (install instructions on the homepage)

#### How to install YT Channel Downloader

Install or upgrade the app with pip (PowerShell or Command Prompt):

```powershell
python -m pip install --upgrade yt-channel-downloader
yt-channel-downloader
```

#### Optional: run from a cloned repository

1. Clone the repo and open PowerShell in the project root.
2. Create and activate a virtual environment:

    ```powershell
    python -m venv .venv
    .venv\Scripts\activate
    ```

3. Install the project in editable mode:

    ```powershell
    pip install -e .
    ```

4. Launch the app:

    ```powershell
    yt-channel-downloader
    ```

5. Deactivate the environment when finished with `deactivate`.

## How to Use

1. Open the application and input a YouTube channel URL.
2. Go to "File" -> "Settings" and set your download preferences.
3. Press the **Get list** button to list available videos.
4. Select the videos you wish to download.
5. Hit the **Download** button.

## Contributing

Feel free to open issues and pull requests. I appreciate your feedback and contributions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Authors

- **hyperfield** - *Initial work* and *Documentation* - [hyperfield](https://github.com/hyperfield)

See also the list of [contributors](https://github.com/hyperfield/yt-channel-downloader/contributors) who participated in this project.

## Donation

If you like this application and want to support future development, I'll appreciate your donation via Ko-Fi or crypto. :)

[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support%20this%20project-FF5E5B?logo=kofi&logoColor=white&style=flat)](https://ko-fi.com/hyperfield) ![Visa](https://img.shields.io/badge/Visa-accepted-blue?logo=visa&logoColor=white&style=flat) ![Mastercard](https://img.shields.io/badge/Mastercard-accepted-orange?logo=mastercard&logoColor=white&style=flat)

**Bitcoin**: bc1pglp2m26kqatgm6z8vtuhk66jd74ghv948wtyhtgtj6wh30nzz6csjajv00

**Ethereum**: 0x9CEf6B928BF9fFd894ca83db1B822820917ca89a

**Tron**: TGq2z17jq8UruCNyyD5GU3weuyJSyM2zBp

**Binance Smart Chain**: 0x863F8f3fC38b7540110462884809621e2B9EE399
