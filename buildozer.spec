[app]

# (str) Title of your application
title = My Application

# (str) Package name (one word, ASCII only)
package.name = myapp

# (str) Package domain (needed for android/ios packaging)
package.domain = org.example

# (str) Source code directory where main.py resides
source.dir = .

# (list) Source files to include
source.include_exts = py,png,jpg,kv,atlas,json

# (list) Exclusions
source.exclude_dirs = tests, bin, venv, .git, .github

# (str) Application versioning
version = 0.1

# (list) Application requirements
requirements = python3,kivy==2.3.0

# (str) Supported orientations (landscape, sensorLandscape, portrait, or all)
orientation = portrait

# (bool) Fullscreen mode
fullscreen = 0

#
# Android specific
#

# (int) Target Android API level
android.api = 34

# (int) Minimum API supported by your APK
android.minapi = 24

# (str) Android NDK version
android.ndk = 25b

# (bool) Auto-accept SDK licenses
android.accept_sdk_license = True

# (list) Android application permissions
android.permissions = INTERNET

# (bool) Enable AndroidX support
android.enable_androidx = True

# (str) Android logcat output filters
android.logcat_filters = *:S python:D

# (str) Android build architecture
android.archs = arm64-v8a, armeabi-v7a

# (bool) Allow backup of application data
android.allow_backup = True

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug)
log_level = 2

# (int) Display warning if buildozer is run as root
warn_on_root = 1