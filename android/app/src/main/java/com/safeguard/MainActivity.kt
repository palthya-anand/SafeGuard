package com.safeguard

import android.Manifest
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.provider.Settings
import android.view.View
import androidx.activity.result.contract.ActivityResultContracts
import androidx.activity.viewModels
import androidx.appcompat.app.AlertDialog
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.repeatOnLifecycle
import com.google.android.material.color.MaterialColors
import com.safeguard.alert.AlertManager
import com.safeguard.data.models.RiskLevel
import com.safeguard.databinding.ActivityMainBinding
import com.safeguard.service.LocationMonitoringService
import com.safeguard.viewmodel.MonitoringViewModel
import kotlinx.coroutines.launch

/**
 * Single-screen entry point for SafeGuard.
 *
 * Responsibilities:
 *  - Permission request flow: ACCESS_FINE_LOCATION → POST_NOTIFICATIONS
 *  - Start/stop [LocationMonitoringService] based on user toggle
 *  - Receive [LocationMonitoringService.ACTION_LOCATION_UPDATE] broadcasts
 *    and forward them to [MonitoringViewModel]
 *  - Observe [MonitoringViewModel] state flows and update the card UI
 *  - Route backend risk responses through [AlertManager]
 */
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private val viewModel: MonitoringViewModel by viewModels()
    private lateinit var alertManager: AlertManager

    // -------------------------------------------------------------------------
    // Permission launchers
    // -------------------------------------------------------------------------

    private val locationPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { results ->
        val granted = results[Manifest.permission.ACCESS_FINE_LOCATION] == true
        if (granted) {
            requestNotificationPermission()
        } else {
            showPermissionRationale(
                getString(R.string.permission_location_rationale)
            ) { requestLocationPermission() }
        }
    }

    private val notifPermLauncher = registerForActivityResult(
        ActivityResultContracts.RequestPermission()
    ) { granted ->
        if (!granted) {
            showPermissionRationale(getString(R.string.permission_notification_rationale)) {}
        }
    }

    // -------------------------------------------------------------------------
    // Broadcast receiver for location updates
    // -------------------------------------------------------------------------

    private val locationReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            if (intent.action != LocationMonitoringService.ACTION_LOCATION_UPDATE) return
            val lat      = intent.getDoubleExtra(LocationMonitoringService.EXTRA_LATITUDE, 0.0)
            val lon      = intent.getDoubleExtra(LocationMonitoringService.EXTRA_LONGITUDE, 0.0)
            val speedKmh = intent.getFloatExtra(LocationMonitoringService.EXTRA_SPEED_KMH, 0f)
            viewModel.onLocationUpdate(lat, lon, speedKmh)
        }
    }

    /** Intercepts the local overspeed broadcast from the service. */
    private val overspeedReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            val speed = intent.getFloatExtra("speed_kmh", 0f)
            val limit = intent.getFloatExtra("limit_kmh", 50f)
            alertManager.showOverspeedAlert(speed, limit)
        }
    }

    // -------------------------------------------------------------------------
    // Lifecycle
    // -------------------------------------------------------------------------

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        setSupportActionBar(binding.toolbar)

        alertManager = AlertManager(this)

        // Initialise device ID for telemetry
        val androidId = Settings.Secure.getString(contentResolver, Settings.Secure.ANDROID_ID)
        viewModel.initDeviceId("android-$androidId")

        setupUi()
        observeViewModel()
        requestLocationPermission()
    }

    override fun onResume() {
        super.onResume()
        val locationFilter = IntentFilter(LocationMonitoringService.ACTION_LOCATION_UPDATE)
        val overspeedFilter = IntentFilter("com.safeguard.ACTION_OVERSPEED_LOCAL")
        ContextCompat.registerReceiver(
            this,
            locationReceiver,
            locationFilter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
        ContextCompat.registerReceiver(
            this,
            overspeedReceiver,
            overspeedFilter,
            ContextCompat.RECEIVER_NOT_EXPORTED
        )
    }

    override fun onPause() {
        super.onPause()
        unregisterReceiver(locationReceiver)
        unregisterReceiver(overspeedReceiver)
    }

    override fun onDestroy() {
        alertManager.release()
        super.onDestroy()
    }

    // -------------------------------------------------------------------------
    // UI setup
    // -------------------------------------------------------------------------

    private fun setupUi() {
        binding.btnToggleMonitoring.setOnClickListener {
            if (viewModel.isMonitoring.value) {
                stopMonitoring()
            } else {
                startMonitoring()
            }
        }
    }

    private fun observeViewModel() {
        lifecycleScope.launch {
            repeatOnLifecycle(Lifecycle.State.STARTED) {

                launch {
                    viewModel.currentSpeed.collect { speed ->
                        binding.tvSpeed.text = speed.toInt().toString()
                    }
                }

                launch {
                    viewModel.currentLocation.collect { loc ->
                        if (loc != null) {
                            binding.tvLatLon.text = getString(
                                R.string.location_format,
                                loc.first, loc.second
                            )
                        } else {
                            binding.tvLatLon.text = getString(R.string.location_unknown)
                        }
                    }
                }

                launch {
                    viewModel.riskResponse.collect { response ->
                        response ?: return@collect
                        val level = RiskLevel.fromString(response.risk_level)

                        // Update badge color
                        val colorRes = when (level) {
                            RiskLevel.LOW      -> R.color.risk_low
                            RiskLevel.MODERATE -> R.color.risk_moderate
                            RiskLevel.HIGH     -> R.color.risk_high
                            RiskLevel.CRITICAL -> R.color.risk_critical
                        }
                        binding.tvRiskLevel.setBackgroundColor(
                            ContextCompat.getColor(this@MainActivity, colorRes)
                        )
                        binding.tvRiskLevel.text = level.name
                        binding.tvRiskScore.text = getString(R.string.risk_score_format, response.risk_score)
                        binding.tvReasons.text   = response.reasons.joinToString("\n• ", "• ")
                        binding.tvHotspotDistance.text = if (response.hotspot && response.distance_to_hotspot_m != null) {
                            getString(R.string.hotspot_distance_format, response.distance_to_hotspot_m.toInt())
                        } else {
                            getString(R.string.no_hotspot_nearby)
                        }

                        // Route through alert manager
                        alertManager.handleRiskResponse(response)
                    }
                }

                launch {
                    viewModel.isMonitoring.collect { monitoring ->
                        binding.btnToggleMonitoring.text = if (monitoring) {
                            getString(R.string.stop_monitoring)
                        } else {
                            getString(R.string.start_monitoring)
                        }
                        binding.tvMonitoringStatus.text = if (monitoring) {
                            getString(R.string.status_monitoring_on)
                        } else {
                            getString(R.string.status_monitoring_off)
                        }
                    }
                }

                launch {
                    viewModel.errorMessage.collect { msg ->
                        msg ?: return@collect
                        binding.tvError.visibility = View.VISIBLE
                        binding.tvError.text = msg
                        // Auto-clear after 4 seconds
                        kotlinx.coroutines.delay(4_000)
                        binding.tvError.visibility = View.GONE
                        viewModel.clearError()
                    }
                }
            }
        }
    }

    // -------------------------------------------------------------------------
    // Service control
    // -------------------------------------------------------------------------

    private fun startMonitoring() {
        if (!hasLocationPermission()) {
            requestLocationPermission()
            return
        }
        viewModel.startMonitoring()
        val intent = Intent(this, LocationMonitoringService::class.java)
        ContextCompat.startForegroundService(this, intent)
    }

    private fun stopMonitoring() {
        viewModel.stopMonitoring()
        stopService(Intent(this, LocationMonitoringService::class.java))
    }

    // -------------------------------------------------------------------------
    // Permissions
    // -------------------------------------------------------------------------

    private fun requestLocationPermission() {
        locationPermLauncher.launch(
            arrayOf(
                Manifest.permission.ACCESS_FINE_LOCATION,
                Manifest.permission.ACCESS_COARSE_LOCATION
            )
        )
    }

    private fun requestNotificationPermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                notifPermLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
            }
        }
    }

    private fun hasLocationPermission() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) ==
                PackageManager.PERMISSION_GRANTED

    private fun showPermissionRationale(message: String, retry: () -> Unit) {
        AlertDialog.Builder(this)
            .setTitle(getString(R.string.app_name))
            .setMessage(message)
            .setPositiveButton(android.R.string.ok) { _, _ -> retry() }
            .setNegativeButton(android.R.string.cancel, null)
            .show()
    }
}
