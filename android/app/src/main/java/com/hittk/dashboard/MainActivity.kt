package com.hittk.dashboard

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.os.Bundle
import android.view.View
import android.webkit.WebResourceRequest
import android.webkit.WebResourceError
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity
import androidx.swiperefreshlayout.widget.SwipeRefreshLayout
import androidx.webkit.WebSettingsCompat
import androidx.webkit.WebViewFeature
import com.hittk.dashboard.databinding.ActivityMainBinding

/**
 * The dashboard, unchanged. This is a shell around the published page rather than a
 * reimplementation of it: the page already carries the accessibility work — status by
 * shape and label rather than hue alone, a 320px floor, system light/dark — and a native
 * rewrite would drift from it the first time either side changed.
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private var loadFailed = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        binding.webView.apply {
            // app.js fetches data.json and renders it, so both of these are required.
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true

            // Serve from cache when offline so a dropped connection shows the last
            // known state instead of an error page.
            settings.cacheMode = android.webkit.WebSettings.LOAD_DEFAULT

            // Without this the page's prefers-color-scheme query never reports dark,
            // and the site would be stuck in light mode regardless of system setting.
            if (WebViewFeature.isFeatureSupported(WebViewFeature.ALGORITHMIC_DARKENING)) {
                WebSettingsCompat.setAlgorithmicDarkeningAllowed(settings, true)
            }

            webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                    loadFailed = false
                }

                override fun onPageFinished(view: WebView?, url: String?) {
                    binding.swipeRefresh.isRefreshing = false
                    binding.errorView.visibility = if (loadFailed) View.VISIBLE else View.GONE
                    binding.webView.visibility = if (loadFailed) View.GONE else View.VISIBLE
                }

                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    // Only a failure of the page itself matters; a missing sub-resource
                    // should not blank a dashboard that otherwise rendered.
                    if (request?.isForMainFrame == true) loadFailed = true
                }
            }

            loadUrl(DASHBOARD_URL)
        }

        binding.swipeRefresh.setOnRefreshListener { binding.webView.reload() }
        binding.retryButton.setOnClickListener { binding.webView.loadUrl(DASHBOARD_URL) }

        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (binding.webView.canGoBack()) {
                    binding.webView.goBack()
                } else {
                    isEnabled = false
                    onBackPressedDispatcher.onBackPressed()
                }
            }
        })
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        binding.webView.saveState(outState)
    }

    companion object {
        const val DASHBOARD_URL = "https://hittk.github.io/dashboard/"
    }
}
