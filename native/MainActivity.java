package com.vault.offline;
import android.content.res.Configuration;
import android.graphics.Color;
import android.os.Bundle;
import android.view.WindowManager;
import androidx.core.view.WindowCompat;
import androidx.core.view.WindowInsetsControllerCompat;
import com.getcapacitor.BridgeActivity;
public class MainActivity extends BridgeActivity {
  @Override public void onCreate(Bundle b) {
    registerPlugin(BiometricVaultPlugin.class);
    super.onCreate(b);
    getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
    // system bars + WebView background match the app theme (no white flash, no mismatched bars)
    boolean night = (getResources().getConfiguration().uiMode & Configuration.UI_MODE_NIGHT_MASK) == Configuration.UI_MODE_NIGHT_YES;
    int c = Color.parseColor(night ? "#060A16" : "#E7EDF9");
    getWindow().setStatusBarColor(c);
    getWindow().setNavigationBarColor(c);
    WindowInsetsControllerCompat ic = WindowCompat.getInsetsController(getWindow(), getWindow().getDecorView());
    ic.setAppearanceLightStatusBars(!night);
    ic.setAppearanceLightNavigationBars(!night);
    getBridge().getWebView().setBackgroundColor(c);
  }
}
