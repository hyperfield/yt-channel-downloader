# Changelog

All notable changes to this project are documented here.

## 0.8.0

- Display estimated download size before downloads begin.
- Display estimated download time / ETA.
- Detect missing JavaScript runtime with a helpful dialog.
- Add pagination for channels and playlists to keep large lists responsive.
- Improve settings/progress UX, including cancelable size/ETA calculation.
- Show thumbnail previews immediately after fetching data.
- Miscellaneous UI polish and indicator tweaks.

## 0.5.5

- Added a download speed indicator column.
- Added a column showing the duration of videos or audios.
- Added a check for updates.
- Removed `pytube`; playlists are now retrieved much faster via `yt_dlp`.
- Published on PyPI for easy installation with `pip`.
- First release to include binaries for macOS and Linux (Debian-compatible only for now).
- Reorganized the source into a `src/` layout for cleaner imports and packaging.
- Bug fixes and stability improvements.

## 0.5.0

- More sites: fetch single tracks or videos from other `yt-dlp`-supported platforms (Vimeo, Twitch, SoundCloud, Facebook, Instagram, Twitter/X, TikTok, Udemy*, Reddit). Bulk channel/playlist fetches remain YouTube-only. (*Udemy still requires the appropriate credentials/cookies for premium content.)
- YouTube login/logout: choose the browser profile whose cookies yt-dlp reuses for private, premium, or age-restricted downloads; clear the configuration from the same menu when no longer needed.
- Download cancellation for in-progress downloads.

## 0.4.12

- Only the Windows installer changed: updated `yt-dlp` to the latest version to fix a problem with unretrievable URLs.

## 0.4.11

- Fixed URL fetching bug: short YouTube URLs are now fetched.
- Cleanup: a minor cleanup in some source files.

## 0.4.10

- Improved stability: bug fixes and improved exception handling.
- Smoother UI: small facelift with more consistent layouts and widget styles.

## 0.4.8

- FFmpeg installation verification: added a check for FFmpeg's presence on the system, as it is required for media downloads. (Contributed by [arvinnick](https://github.com/arvinnick)).

## 0.4.6

- Thumbnail downloads: added checkbox in Settings to enable thumbnail downloads for each video link. (Contributed by [dsasmblr](https://github.com/dsasmblr)).

## 0.4.5

- Fetch progress dialog: added an indefinite progress bar dialog window that displays the elapsed time in seconds and has a Cancel button.
- Refactoring: added numerous Python docstrings, introduced a new class, and reformatted the code for improved cleanliness and readability.

## 0.4.2

- Shorts support: downloading YouTube shorts now works.
- Improved exception handling: improved handling of network and download errors, timeouts.

## 0.4.1

- Bug fixes: due to some updates on YouTube, certain functionality didn't work. The "Any" format selection didn't work. These have been fixed.
- Improved exception handling: some parts of the code needed exception handling.
- Improved interface: better and bigger fonts and buttons.
- Added the "Donate" item to the Help menu.

## 0.4.0

- YouTube login and logout: configure the browser profile whose cookies yt-dlp should reuse for private or age-restricted downloads. Use `File -> YouTube login` to select the browser/profile, and choose “Clear YouTube login” to forget the configuration.
- Minor improvements and bug fixes.

## 0.3.3

- Improved default audio track downloading: the program will now always attempt to download the best available quality audio track. Previously, the associated audio track was not always downloaded, for 4k quality videos in particular.

## 0.3.2

- Fixed the handling of video resolutions and formats specified in Settings: the program will correctly find the closest available video resolution and format based on user settings, for horizontal and vertical videos.

## 0.3.1

- Limiting of simultaneous download threads: this improves the responsiveness of the application and optimizes its handling of large download lists.
- Improved file name sanitation method: this prevents some completed downloads not being marked as such.

## 0.3.0

- Download playlists, in addition to channels or single videos.
- Select All check box: allows selecting all non-downloaded videos in a list at once.
- Bug fixes: improved URL validation, partial download completion.
- Interface improvements.
- Other improvements: code cleanup, updated README.
