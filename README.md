# 🔐 Offline Vault

A password manager that never goes online. No account, no server, no analytics,
no network permission. Your passwords live encrypted on your phone and nowhere else.

## Features
- **Fully offline:** the app makes zero network calls; fonts and assets ship inside the APK
- **Strong encryption:** AES-256-GCM, key derived from your master password with PBKDF2-SHA-256 (600,000 iterations)
- **Encrypted backups:** export to a password-protected file via the Android share sheet; import on a new phone
- **Accounts, notes and profiles**, with a password generator and a weak/reused/old password check
- **Auto-lock** when you leave the app, plus failed-attempt tracking and an activity log
- **Arabic and English** (RTL/LTR), with light and dark themes
- **"Abyss & Aurora" UI:** glass surfaces, animated lock dial, screen transitions; respects "reduce motion"

## Important
- Your master password **cannot be recovered**. If you forget it, the data is gone.
- Export a backup before changing phones. Reinstalling or switching devices does not carry the vault over.

## Build
The APK is built by GitHub Actions (`.github/workflows/build-apk.yml`).
Run the "Build APK" workflow and download the artifact.

## Credits
Fonts: Outfit and JetBrains Mono (SIL OFL, licenses in `www/fonts`).
