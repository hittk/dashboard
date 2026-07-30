# Dashboard — Android

The same dashboard as <https://hittk.github.io/dashboard/>, on the home screen.

This is a shell around the published page, not a reimplementation of it. The page
already carries the accessibility work — status by shape and written label rather
than hue alone, a 320px floor, system light/dark — and a native rewrite would drift
from it the first time either side changed. One dashboard, two ways in.

## Build

```bash
cd android
./gradlew assembleDebug        # app/build/outputs/apk/debug/app-debug.apk
./gradlew installDebug         # straight onto a connected device
```

Needs the Android SDK (API 35) and JDK 17+. Open `android/` in Android Studio and
it will resolve everything itself.

Built and verified: `BUILD SUCCESSFUL`, a 3.4 MB debug APK, `minSdk 26` / `targetSdk 35`,
requesting only `INTERNET` and `ACCESS_NETWORK_STATE`. Lint is clean — 0 errors, and the
only remaining warnings are `GradleDependency` notices that newer library versions exist.

Dependencies are pinned to the versions the build was verified against rather than the
newest available. Recent AndroidX releases often require a higher `compileSdk`, so
bumping them is a change to make deliberately and re-verify, not a lint box to tick.

**Not yet run on a device.** There was no emulator available, so the WebView behaviour,
the dark-mode path and the offline fallback are unconfirmed against a real screen.

If you rename a resource folder, run `./gradlew clean` first — the incremental resource
cache keeps the old path and fails with a misleading "resource not found".

## What it does

| | |
|---|---|
| Loads | `https://hittk.github.io/dashboard/` |
| Refresh | Pull down |
| Offline | Serves the last cached render; falls back to a retry screen if there is none |
| Back | Navigates the page's history, then exits |
| Theme | Follows the system, via `DayNight` plus algorithmic darkening |

JavaScript and DOM storage are on because `app.js` fetches `data.json` and renders
it client-side; without them the page is blank.

## What it deliberately does not do

No notifications, no offline-first cache, no local data. Those need the app to hold
the data rather than borrow a rendered page, which is a different piece of work —
see the separate design note. This is parity with the web page and nothing more.

## Changing the URL

`MainActivity.DASHBOARD_URL`. Point it at `http://<your-machine>:8000` alongside
`make serve` to preview local changes on a device.
