package com.vault.offline;

import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyPermanentlyInvalidatedException;
import android.security.keystore.KeyProperties;
import android.util.Base64;

import androidx.biometric.BiometricManager;
import androidx.biometric.BiometricManager.Authenticators;
import androidx.biometric.BiometricPrompt;
import androidx.core.content.ContextCompat;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import java.nio.charset.StandardCharsets;
import java.security.KeyStore;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * Fingerprint unlock for Offline Vault.
 *
 * The master password is encrypted with an AES-256-GCM key that lives in the Android Keystore
 * and can only be used right after a successful STRONG biometric check (CryptoObject).
 * The key is invalidated if fingerprints are added/removed on the phone.
 * Only the ciphertext is stored (private SharedPreferences); the key never leaves the secure hardware.
 *
 * JS: Capacitor.Plugins.BiometricVault.{status, enroll, unlock, clear}
 */
@CapacitorPlugin(name = "BiometricVault")
public class BiometricVaultPlugin extends Plugin {

    private static final String ALIAS = "offline_vault_bio_key_v1";
    private static final String PREFS = "vault_bio";
    private static final String P_IV = "iv";
    private static final String P_CT = "ct";
    private static final String TRANSFORM = "AES/GCM/NoPadding";

    private boolean busy = false;

    private interface OnAuth { void run(Cipher c) throws Exception; }

    private SharedPreferences prefs() {
        return getContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private KeyStore keyStore() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        return ks;
    }

    private void wipeAll() {
        try { keyStore().deleteEntry(ALIAS); } catch (Exception ignored) { }
        prefs().edit().clear().apply();
    }

    private SecretKey createKey() throws Exception {
        KeyGenerator kg = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        KeyGenParameterSpec.Builder b = new KeyGenParameterSpec.Builder(
                ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .setUserAuthenticationRequired(true);
        if (Build.VERSION.SDK_INT >= 24) b.setInvalidatedByBiometricEnrollment(true);
        if (Build.VERSION.SDK_INT >= 30) b.setUserAuthenticationParameters(0, KeyProperties.AUTH_BIOMETRIC_STRONG);
        kg.init(b.build());
        return kg.generateKey();
    }

    @PluginMethod
    public void status(PluginCall call) {
        int code = BiometricManager.from(getContext()).canAuthenticate(Authenticators.BIOMETRIC_STRONG);
        boolean available = Build.VERSION.SDK_INT >= 23 && code == BiometricManager.BIOMETRIC_SUCCESS;
        boolean enrolled = false;
        try {
            enrolled = prefs().contains(P_CT) && keyStore().containsAlias(ALIAS);
        } catch (Exception ignored) { }
        JSObject ret = new JSObject();
        ret.put("available", available);
        ret.put("enrolled", enrolled);
        ret.put("code", code);
        call.resolve(ret);
    }

    @PluginMethod
    public void clear(PluginCall call) {
        wipeAll();
        call.resolve();
    }

    /** Encrypts {secret} behind the fingerprint. Needs one successful fingerprint scan. */
    @PluginMethod
    public void enroll(final PluginCall call) {
        final String secret = call.getString("secret", "");
        if (secret.isEmpty()) { call.reject("No secret", "error"); return; }
        if (Build.VERSION.SDK_INT < 23) { call.reject("Unsupported", "unavailable"); return; }
        final Cipher cipher;
        try {
            wipeAll();
            cipher = Cipher.getInstance(TRANSFORM);
            cipher.init(Cipher.ENCRYPT_MODE, createKey());
        } catch (Exception e) {
            wipeAll();
            call.reject(String.valueOf(e.getMessage()), "error");
            return;
        }
        prompt(call, cipher, c -> {
            byte[] ct = c.doFinal(secret.getBytes(StandardCharsets.UTF_8));
            prefs().edit()
                    .putString(P_IV, Base64.encodeToString(c.getIV(), Base64.NO_WRAP))
                    .putString(P_CT, Base64.encodeToString(ct, Base64.NO_WRAP))
                    .apply();
            call.resolve();
        });
    }

    /** Fingerprint scan, then returns the stored secret. */
    @PluginMethod
    public void unlock(final PluginCall call) {
        String ivS = prefs().getString(P_IV, null), ctS = prefs().getString(P_CT, null);
        if (ivS == null || ctS == null) { call.reject("Not enrolled", "not_enrolled"); return; }
        final byte[] ct = Base64.decode(ctS, Base64.NO_WRAP);
        final Cipher cipher;
        try {
            SecretKey key = (SecretKey) keyStore().getKey(ALIAS, null);
            if (key == null) { wipeAll(); call.reject("Key gone", "invalidated"); return; }
            cipher = Cipher.getInstance(TRANSFORM);
            cipher.init(Cipher.DECRYPT_MODE, key, new GCMParameterSpec(128, Base64.decode(ivS, Base64.NO_WRAP)));
        } catch (KeyPermanentlyInvalidatedException e) {
            wipeAll();
            call.reject("Fingerprints changed", "invalidated");
            return;
        } catch (Exception e) {
            call.reject(String.valueOf(e.getMessage()), "error");
            return;
        }
        prompt(call, cipher, c -> {
            JSObject ret = new JSObject();
            ret.put("secret", new String(c.doFinal(ct), StandardCharsets.UTF_8));
            call.resolve(ret);
        });
    }

    private void prompt(final PluginCall call, final Cipher cipher, final OnAuth ok) {
        if (busy) { call.reject("Busy", "busy"); return; }
        final String title = call.getString("title", "Vault");
        final String subtitle = call.getString("subtitle", "");
        final String cancel = call.getString("cancel", "Cancel");
        busy = true;
        getActivity().runOnUiThread(() -> {
            try {
                BiometricPrompt.PromptInfo.Builder b = new BiometricPrompt.PromptInfo.Builder()
                        .setTitle(title)
                        .setConfirmationRequired(false)
                        .setAllowedAuthenticators(Authenticators.BIOMETRIC_STRONG)
                        .setNegativeButtonText(cancel);
                if (!subtitle.isEmpty()) b.setSubtitle(subtitle);

                BiometricPrompt bp = new BiometricPrompt(getActivity(),
                        ContextCompat.getMainExecutor(getContext()),
                        new BiometricPrompt.AuthenticationCallback() {
                            @Override
                            public void onAuthenticationSucceeded(BiometricPrompt.AuthenticationResult r) {
                                busy = false;
                                try {
                                    ok.run(r.getCryptoObject().getCipher());
                                } catch (Exception e) {
                                    call.reject(String.valueOf(e.getMessage()), "error");
                                }
                            }

                            @Override
                            public void onAuthenticationError(int code, CharSequence msg) {
                                busy = false;
                                call.reject(String.valueOf(msg), String.valueOf(code));
                            }
                        });
                bp.authenticate(b.build(), new BiometricPrompt.CryptoObject(cipher));
            } catch (Exception e) {
                busy = false;
                call.reject(String.valueOf(e.getMessage()), "error");
            }
        });
    }
}
