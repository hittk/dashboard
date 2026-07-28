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

**Not built or run yet.** It was written in an environment with no Android SDK, so
it has never been compiled. XML resources are validated; the Kotlin and Gradle
scripts are not. Expect to fix something on first build.

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
