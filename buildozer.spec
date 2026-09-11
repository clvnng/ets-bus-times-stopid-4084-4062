[app]
title = ETS Bus Times
package.name = etsbustimes
package.domain = org.etsbustimes
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

# gtfs-realtime-bindings is optional - the app falls back to scheduled-only
# times if it's missing or fails to build for Android. Remove it from this
# list if the build fails because of it.
requirements = python3,kivy,protobuf,gtfs-realtime-bindings

orientation = portrait
fullscreen = 0

android.permissions = INTERNET
android.api = 33
android.minapi = 21
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
