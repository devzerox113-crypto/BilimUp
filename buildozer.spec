[app]
title = BilimUp
package.name = bilimup
package.domain = kz.bilimup
source.dir = .
source.include_exts = py,json,png,jpg,kv
version = 12.0.0
requirements = python3,kivy==2.3.0
orientation = portrait
fullscreen = 0
android.permissions = INTERNET
android.api = 35
android.minapi = 24
android.archs = arm64-v8a, armeabi-v7a
android.accept_sdk_license = True

[buildozer]
log_level = 2
warn_on_root = 1
