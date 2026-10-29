# Vault (offline password manager, Android)

- 100% offline. No account, no network calls, no analytics.
- Master password -> PBKDF2-SHA256 (600k iterations) -> AES-256-GCM. Only ciphertext is stored.
- Screenshots blocked (FLAG_SECURE), Android cloud backup disabled, auto-lock, clipboard cleared after 30 s.
- Arabic (RTL) and English.
- v2: profiles, secure notes, password-change timestamps and history, activity log, security check, encrypted backups with their own password. Vaults created with v1 open and upgrade automatically.

## Build the APK (no Android Studio needed)
1. Create a GitHub repo and upload this folder's contents (keep .github/workflows).
2. Actions tab -> "Build APK" -> Run workflow.
3. Download the `vault-apk` artifact, unzip, install app-debug.apk on the phone.

## Build locally
npm install && npx cap add android
(then apply the two edits shown in .github/workflows/build-apk.yml)
npx cap sync android && cd android && ./gradlew assembleDebug

## Important
- A forgotten master password cannot be recovered.
- Uninstalling the app or clearing its data deletes the vault. Use Settings -> Export encrypted backup regularly and keep the file somewhere safe.

## v2.1
- New vault-dial app icon (icons/res is copied into the Android project by the workflow).
- Vault tab: List (editable) / Overview (read-only tree: profile > app > accounts). Accounts have an optional label (main, secondary, 1, 2...).

## v3 - new look ("Abyss & Aurora")
- New icon (gradient dial + glowing keyhole), adaptive + themed (Android 13) + round + launch screen. Regenerate or recolor: `python3 tools/make_icons.py`.
- New UI: midnight base, teal>blue>violet accent, glass surfaces, screen transitions, animated lock dial (shakes red on a wrong password, flares open on success), colour-coded generator output.
- Fonts are bundled in `www/fonts` (Outfit + JetBrains Mono, OFL licence files included). Still zero network calls. Arabic uses the phone's built-in Noto Arabic.
- Respects the system "reduce motion" setting and light/dark mode.
- Existing vaults open unchanged; old profile colours are mapped to the new palette on display.
- v3.2: backup export now opens the Android share sheet (uses @capacitor/filesystem + @capacitor/share), so you choose where the file is saved.
