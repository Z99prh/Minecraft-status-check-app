[app]

# Application info
title = MC Server Status
package.name = mcserverstatus
package.domain = org.mcstatus
version = 1.0

# Source configuration
source.dir = .
source.include_exts = py,ttf

# Requirements - minimal and tested
requirements = python3==3.11.6,kivy==2.3.0,pyjnius,plyer

# App configuration
orientation = portrait
fullscreen = 0

# Android permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,POST_NOTIFICATIONS,WAKE_LOCK

# Android configuration
android.archs = arm64-v8a,armeabi-v7a
android.api = 33
android.minapi = 21
android.sdk = 33
android.ndk = 25b
android.accept_sdk_license = True
android.enable_androidx = True

# Storage and bootstrap
android.private_storage = True
android.bootstrap = sdl2

# Background service
android.allow_backup = True
android.manifest.launch_mode = standard

[buildozer]

# Build configuration
log_level = 2
warn_on_root = 1
