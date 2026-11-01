# Screenshots and demos

The README includes version 0.9.0 captures from Linux, Windows, and macOS.

## Linux captures

The current assets were captured from **version 0.9.0 on 2026-10-28**, using
Linux, X11, Xfwm4 window decorations, and Qt's Fusion widget style. They are
captures of the running application, including the window borders.

| File | Contents | Size |
| --- | --- | --- |
| `screenshot_lin.png` | Channel results and a download in progress | 1322 × 915 |
| `settings-video.png` | MP4 output, resolution cap, and fetch limits | 956 × 607 |
| `settings-audio.png` | Audio-only FLAC output with bitrate disabled | 956 × 607 |
| `yt-channel-downloader-demo.gif` | Fetch, filter, select, download, and completion | 1100 × 762 |

The example listings and thumbnail images come from
[Blender's public YouTube channel](https://www.youtube.com/@BlenderOfficial).
The recorded download is
[Blender Conference 2026 Recap](https://www.youtube.com/watch?v=sO_lhW8av3U).
Video titles and thumbnails belong to their respective creators.

### Recording and editing

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

For future Linux captures, use the matching release, include the whole app window,
keep text legible, and retain the native platform label. Recapture video and
audio Settings separately so their enabled controls are clear.

## macOS captures

Captured from **version 0.9.0 on 2026-11-01**, on macOS 26.6.2 (Apple Silicon),
using Qt 6.12.0's native macOS widget style in light mode. These images contain
the running application's window contents, without desktop backgrounds or
window frames. They replace the historical November 2025 macOS screenshot.

| File | Contents | Size |
| --- | --- | --- |
| `screenshot_mac.png` | Movie thumbnails, two selected items, and size estimates | 2560 × 1440 |
| `ytdl-settings_mac.png` | 1080p MP4 output, fetch limits, and proxy controls | 1908 × 1164 |
| `settings-audio_mac.png` | Audio-only FLAC output with bitrate disabled | 1908 × 1164 |
| `yt-chan-dl-mac.gif` | Title filtering, item selection, and Select All | 1280 × 720 |
| `yt-channel-downloader-demo-mac.gif` | Live fetch, filter, select, download, and completion | 1100 × 773 |

The stills retain Retina resolution. The shorter `yt-chan-dl-mac.gif` loops for
approximately **8.2 seconds**, recording interactions with offline demonstration
listings and estimates, using the same Blender movie thumbnails as the Windows
captures. It does not include a media transfer.
Video Settings show 500/100 channel/playlist fetch limits; these are example
values, rather than the default 500/50 limits. Audio Settings demonstrate FLAC
with the bitrate control disabled.

### Workflow animation

The README's `yt-channel-downloader-demo-mac.gif` records a real fetch of eight
entries from [Blender's public channel](https://www.youtube.com/@BlenderOfficial),
typing a title filter, selecting
[Blender Conference 2026 Recap](https://www.youtube.com/watch?v=sO_lhW8av3U),
clearing the filter, and downloading the video as 480p MP4 through completion.
FFprobe verified the completed file's 480p video and audio streams.

The animation has **124 frames at 8 fps**, lasts **15.51 seconds**, and loops.
Waiting time and repetitive transfer frames were cut from the approximately
52-second recording. The transfer was limited to 512 KiB/s to keep progress
visible. FFmpeg used a shared palette and encoded changes between frames; the
GIF is **345,590 bytes**. The fetch dialog's real widget capture is composited at
its position over the main window. No progress or provider results are simulated.

Regenerate on macOS with the capture helper described below. It uses an isolated
temporary profile and leaves the user's settings untouched.

## Windows captures

The README shows the actual version 0.9.0 Qt interface captured on Windows.
Images contain window contents, without desktop backgrounds or window frames.
The GIF demonstrates typing a title filter, selecting a matching item, clearing
the filter, and using Select All. No media transfer is simulated or recorded.

The movie listing and file-size estimates are offline demonstration fixtures.
Cached thumbnails make captures repeatable without fetching YouTube data.
The capture process uses a temporary profile, disables login prompts, update
checks and background network workers, and leaves the user's settings untouched.

## Regenerating Windows and macOS captures

From an activated project environment, run:

```bash
python -m pip install -e . Pillow
python scripts/capture_readme.py
```

For a preview that does not replace the README assets:

```bash
python scripts/capture_readme.py --output-dir build/readme-capture
```

On Windows, these commands produce `screenshot_win.png`,
`ytdl-settings_win.png`, `settings-audio_win.png`, and `yt-chan-dl-win.gif`.
On macOS they produce the three stills and the shorter
`yt-chan-dl-mac.gif` listed above.
Pillow is only needed by the capture helper, not by the application.

Windows captures use Qt's WindowsVista style for consistent rendering and
readable button labels. Use `--style NAME` to choose another installed Qt style.
The script hides its windows from the desktop while capturing their widgets.
On macOS it uses Qt's Cocoa platform plugin and native macOS widget style.

Capture on the operating system being documented. The helper names Linux
outputs with `lin` and macOS outputs with `mac`; it does not emulate platform
appearance. The Linux gallery above has its own recordings.

To record the full workflow animation, install the external requirements from
the main README, then run on macOS:

```bash
python scripts/capture_readme_workflow.py
```

This recorder contacts YouTube and downloads one video into a temporary folder.
It writes `yt-channel-downloader-demo-mac.gif` under `docs/images/`, and retains
raw frames and capture metadata under `build/readme-workflow/`. Normal app
settings are untouched. Use `--output-dir build/readme-workflow-preview` for a
preview. `--url` and `--filter` can select another source and a title with exactly
one match if the example video moves out of the channel's first eight entries.

## Thumbnail attribution

The JPEG files under `fixtures/` were copied without modification from the
official Blender YouTube uploads. The application scales these thumbnails
when rendering the captures. Movie artwork retains its original license;
it is not covered by the application's MIT license.

| Thumbnail fixture | Movie and attribution | License information |
| --- | --- | --- |
| [YE7VzlLtp-4.jpg](fixtures/YE7VzlLtp-4.jpg) | [Big Buck Bunny](https://www.youtube.com/watch?v=YE7VzlLtp-4), copyright 2008 Blender Foundation / www.bigbuckbunny.org | [Project attribution](https://peach.blender.org/about/), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| [eRsGyueVLvQ.jpg](fixtures/eRsGyueVLvQ.jpg) | [Sintel](https://www.youtube.com/watch?v=eRsGyueVLvQ), copyright Blender Foundation / www.sintel.org | [Project attribution](https://durian.blender.org/sharing/), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| [R6MlUcmOul8.jpg](fixtures/R6MlUcmOul8.jpg) | [Tears of Steel](https://www.youtube.com/watch?v=R6MlUcmOul8), copyright Blender Foundation / mango.blender.org | [Project attribution](https://mango.blender.org/sharing/), [CC BY 3.0](https://creativecommons.org/licenses/by/3.0/) |
| [TLkA0RELQ1g.jpg](fixtures/TLkA0RELQ1g.jpg) | [Elephants Dream](https://www.youtube.com/watch?v=TLkA0RELQ1g), copyright 2006 Blender Foundation / Netherlands Media Art Institute / www.elephantsdream.org | [Project attribution](https://orange.blender.org/page/2/), [CC BY 2.5](https://creativecommons.org/licenses/by/2.5/) |

Each original thumbnail URL has the form
`https://i.ytimg.com/vi/VIDEO_ID/mqdefault.jpg`, using the corresponding fixture
filename as `VIDEO_ID`.
