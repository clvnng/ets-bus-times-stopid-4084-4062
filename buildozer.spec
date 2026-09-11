[app]

# (str) Title of your application
title = My Application

# (str) Package name (one word, ASCII only)
package.name = myapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.example

# (str) Source code directory where main.py resides
source.dir = .

# (list) Source files to include (comma-separated, no spaces)
source.include_exts = py,png,jpg,kv,atlas,json

# (list) List of exclusions using pattern matching
source.exclude_dirs = tests, bin, venv, .git, .github

# (str) Application versioning
version = 0.1

# (list) Application requirements
# Pure Python packages or python-for-android recipes
requirements = python3,kivy==2.3.0

# (str) Supported orientations (landscape, sensorLandscape, portrait, or all)
orientation = portrait

# (bool) Fullscreen mode (1 = True, 0 = False)
fullscreen = 0

# (str) Icon of the application (512x512 PNG)
# icon.filename = %(source.dir)s/icon.png

#
# Android specific
#

# (int) Target Android API level (Modern Google Play target is API 34+)
android.api = 34

# (int) Minimum API supported by your APK
android.minapi = 24

# (str) Android NDK version (blank uses default supported by python-for-android)
android.ndk = 25b

# (bool) Auto-accept SDK licenses (Critical for CI/CD pipelines)
android.accept_sdk_license = True

# (list) Android application permissions
android.permissions = INTERNET

# (bool) Enable AndroidX support
android.enable_androidx = True

# (str) Android logcat output filters
android.logcat_filters = *:S python:D

# (str) Android build architecture (arm64-v8a is required for modern 64-bit devices)
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow backup of application data
android.allow_backup = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1