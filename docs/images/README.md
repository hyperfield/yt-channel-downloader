# Screenshots and demo

The current assets were captured from **version 0.9.0 on 2026-10-28**, using
Linux, X11, Xfwm4 window decorations, and Qt's Fusion widget style. They are
captures of the running application, including the window borders.

| File | Contents | Size |
| --- | --- | --- |
| `screenshot_lin.png` | Channel results and a download in progress | 1322 × 915 |
| `settings-video.png` | MP4 output, resolution cap, and fetch limits | 956 × 607 |
| `settings-audio.png` | Audio-only FLAC output with bitrate disabled | 956 × 607 |
| `about.png` | Version and release date | 491 × 353 |
| `yt-channel-downloader-demo.gif` | Fetch, filter, select, download, and completion | 1100 × 762 |

The example listings and thumbnail images come from
[Blender's public YouTube channel](https://www.youtube.com/@BlenderOfficial).
The recorded download is
[Blender Conference 2026 Recap](https://www.youtube.com/watch?v=sO_lhW8av3U).
Video titles and thumbnails belong to their respective creators.

## Recording and editing

The app fetched eight real channel entries and downloaded the selected video as
480p MP4. An isolated configuration and temporary download directory kept the
capture separate from normal app settings. The capture process limited the
transfer to 512 KiB/s so the progress bar remained visible; application source
code was unchanged. The Settings stills show separate examples: 1080p MP4 output
and audio-only FLAC, with the default 500/50 fetch limits.

The GIF contains **103 frames at 8 fps**, runs for **12.87 seconds**, and loops.
Waiting and repetitive progress frames were cut from the approximately
69-second recording. FFmpeg scaled the window capture and used a shared palette
with changes encoded between frames. The result is 443,392 bytes, compared with
964,010 bytes and 26.33 seconds for the earlier Windows GIF.

For future captures, use the matching release, include the whole app window,
keep text legible, and retain the native platform label. Recapture video and
audio Settings separately so their enabled controls are clear.

## Earlier platform images

`screenshot_win.png`, `screenshot_mac.png`, `ytdl-settings_win.png`, and
`yt-chan-dl-win.gif` were last updated in November 2025. They remain available in
the README's historical gallery. Current Windows and macOS captures should be
made on those operating systems when they are available.
