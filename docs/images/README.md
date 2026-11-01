# Screenshots and demos

The README includes version 0.9.0 captures from Linux and Windows.

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

## Windows captures

The README shows the actual version 0.9.0 Qt interface captured on Windows.
Images contain window contents, without desktop backgrounds or window frames.
The GIF demonstrates typing a title filter, selecting a matching item, clearing
the filter, and using Select All. No media transfer is simulated or recorded.

The movie listing and file-size estimates are offline demonstration fixtures.
Cached thumbnails make captures repeatable without fetching YouTube data.
The capture process uses a temporary profile, disables login prompts, update
checks and background network workers, and leaves the user's settings untouched.

### Regenerating

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
`ytdl-settings_win.png`, and `yt-chan-dl-win.gif`. Pillow is only needed by the
capture helper, not by the application.

Windows captures use Qt's WindowsVista style for consistent rendering and
readable button labels. Use `--style NAME` to choose another installed Qt style.
The script hides its windows from the desktop while capturing their widgets.

Capture on the operating system being documented. The helper names Linux
outputs with `lin` and macOS outputs with `mac`; it does not emulate platform
appearance. The Linux gallery above has its own recordings. Updated native
macOS captures can replace the historical image after review.

### Thumbnail attribution

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

## Earlier platform images

`screenshot_mac.png` was last updated in November 2025 and remains in the
README's historical gallery. Capture an updated image on macOS before replacing
it or labeling it as the current interface.
