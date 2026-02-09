
[app]
title = MC Server Status
version = 1.0
package.name = mcstatusapp
package.domain = org.partha

source.dir = .
source.include_exts = py,ttf

requirements = python3,kivy,mcstatus,plyer

orientation = portrait
fullscreen = 0

android.permissions = INTERNET,POST_NOTIFICATIONS,FOREGROUND_SERVICE

# Foreground service
android.foreground_service = True

[buildozer]
log_level = 2
warn_on_root = 1
