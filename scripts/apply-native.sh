#!/usr/bin/env bash
# Adds the fingerprint-unlock native code + hardening to the generated Capacitor android/ project.
# Run after `npx cap add android`. Safe to run more than once.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APP="$ROOT/android/app"
PKG="$APP/src/main/java/com/vault/offline"
MANIFEST="$APP/src/main/AndroidManifest.xml"

mkdir -p "$PKG"
cp "$ROOT/native/MainActivity.java" "$ROOT/native/BiometricVaultPlugin.java" "$PKG/"

grep -q 'androidx.biometric' "$APP/build.gradle" || \
  sed -i '0,/^dependencies {/s||dependencies {\n    implementation "androidx.biometric:biometric:1.1.0"|' "$APP/build.gradle"

grep -q 'USE_BIOMETRIC' "$MANIFEST" || \
  sed -i 's|</manifest>|    <uses-permission android:name="android.permission.USE_BIOMETRIC" />\n</manifest>|' "$MANIFEST"

# no system backup: the encrypted vault and the fingerprint key never leave this phone
sed -i 's/android:allowBackup="true"/android:allowBackup="false"/' "$MANIFEST"
echo "Vault native code applied."
