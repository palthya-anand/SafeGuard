package com.safeguard.viewmodel

import android.provider.Settings
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.safeguard.BuildConfig
import com.safeguard.data.models.PredictRiskRequest
import com.safeguard.data.models.PredictRiskResponse
import com.safeguard.data.models.TelemetryRequest
import com.safeguard.network.RetrofitClient
import com.safeguard.service.LocationMonitoringService
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.Instant
import java.time.format.DateTimeFormatter

/**
 * ViewModel that bridges location updates from [LocationMonitoringService] with
 * the backend risk-prediction and telemetry APIs.
 *
 * ### Timing policy
 * - Risk prediction:  every **5 seconds** of monitoring time (throttled via a
 *   per-call timestamp guard, not a fixed timer, so bursts of location updates
 *   don't cause parallel network calls).
 * - Telemetry upload: every **10 seconds**.
 */
class MonitoringViewModel : ViewModel() {

    // -------------------------------------------------------------------------
    // Exposed state
    // -------------------------------------------------------------------------

    private val _currentSpeed    = MutableStateFlow(0f)
    val currentSpeed: StateFlow<Float> = _currentSpeed.asStateFlow()

    private val _currentLocation = MutableStateFlow<Pair<Double, Double>?>(null)
    val currentLocation: StateFlow<Pair<Double, Double>?> = _currentLocation.asStateFlow()

    private val _riskResponse    = MutableStateFlow<PredictRiskResponse?>(null)
    val riskResponse: StateFlow<PredictRiskResponse?> = _riskResponse.asStateFlow()

    private val _isMonitoring    = MutableStateFlow(false)
    val isMonitoring: StateFlow<Boolean> = _isMonitoring.asStateFlow()

    private val _errorMessage    = MutableStateFlow<String?>(null)
    val errorMessage: StateFlow<String?> = _errorMessage.asStateFlow()

    // -------------------------------------------------------------------------
    // Private fields
    // -------------------------------------------------------------------------

    private val api = RetrofitClient.create(BuildConfig.API_BASE_URL)

    /** Device identifier for telemetry – use Android ID in production. */
    private var deviceId: String = "android-device"

    private var lastRiskCallMs      = 0L
    private var lastTelemetryCallMs = 0L

    private val RISK_INTERVAL_MS      = 5_000L
    private val TELEMETRY_INTERVAL_MS = 10_000L

    // Current traffic/weather context (could be updated from UI selectors)
    var trafficLevel: String = "MODERATE"
    var weatherCode: String  = "CLEAR"
    private var speedLimit: Float? = null   // null = let backend infer

    // -------------------------------------------------------------------------
    // Lifecycle helpers called by the Activity
    // -------------------------------------------------------------------------

    /** Initialise the device ID from Android Settings (requires a Context). */
    fun initDeviceId(id: String) {
        deviceId = id
    }

    fun startMonitoring() {
        _isMonitoring.value = true
        lastRiskCallMs      = 0L
        lastTelemetryCallMs = 0L
    }

    fun stopMonitoring() {
        _isMonitoring.value = false
    }

    // -------------------------------------------------------------------------
    // Core update handler
    // -------------------------------------------------------------------------

    /**
     * Called every time a location fix arrives from the service broadcast.
     * Throttles backend calls to [RISK_INTERVAL_MS] and [TELEMETRY_INTERVAL_MS].
     */
    fun onLocationUpdate(lat: Double, lon: Double, speedKmh: Float) {
        _currentSpeed.value    = speedKmh
        _currentLocation.value = Pair(lat, lon)

        if (!_isMonitoring.value) return

        val now = System.currentTimeMillis()

        if (now - lastRiskCallMs >= RISK_INTERVAL_MS) {
            lastRiskCallMs = now
            fetchRiskPrediction(lat, lon, speedKmh, now)
        }

        if (now - lastTelemetryCallMs >= TELEMETRY_INTERVAL_MS) {
            lastTelemetryCallMs = now
            postTelemetry(lat, lon, speedKmh, now)
        }
    }

    // -------------------------------------------------------------------------
    // Network calls
    // -------------------------------------------------------------------------

    private fun fetchRiskPrediction(
        lat: Double, lon: Double, speedKmh: Float, epochMs: Long
    ) = viewModelScope.launch {
        runCatching {
            val request = PredictRiskRequest(
                latitude        = lat,
                longitude       = lon,
                speed_kmh       = speedKmh,
                speed_limit_kmh = speedLimit,
                traffic_level   = trafficLevel,
                weather         = weatherCode,
                timestamp       = isoTimestamp(epochMs),
                device_id       = deviceId
            )
            api.predictRisk(request)
        }.onSuccess { response ->
            if (response.isSuccessful) {
                response.body()?.let { _riskResponse.value = it }
            } else {
                _errorMessage.value = "Risk API error ${response.code()}"
            }
        }.onFailure { err ->
            _errorMessage.value = "Network error: ${err.localizedMessage}"
        }
    }

    private fun postTelemetry(
        lat: Double, lon: Double, speedKmh: Float, epochMs: Long
    ) = viewModelScope.launch {
        runCatching {
            val request = TelemetryRequest(
                device_id     = deviceId,
                timestamp     = isoTimestamp(epochMs),
                latitude      = lat,
                longitude     = lon,
                speed_kmh     = speedKmh,
                traffic_level = trafficLevel,
                weather_code  = weatherCode
            )
            api.postTelemetry(request)
        }.onFailure { err ->
            // Telemetry failures are soft – log but don't surface to UI
            android.util.Log.w("MonitoringViewModel", "Telemetry upload failed: ${err.message}")
        }
    }

    // -------------------------------------------------------------------------
    // Speed-limit passthrough
    // -------------------------------------------------------------------------

    /**
     * Update the speed limit used by both the local service guard and the
     * risk-prediction request payload.
     */
    fun updateSpeedLimit(limit: Float) {
        speedLimit = limit
        LocationMonitoringService.updateSpeedLimit(limit)
    }

    /** Clear a transient error banner after the UI has consumed it. */
    fun clearError() {
        _errorMessage.value = null
    }

    // -------------------------------------------------------------------------
    // Utility
    // -------------------------------------------------------------------------

    private fun isoTimestamp(epochMs: Long): String =
        DateTimeFormatter.ISO_INSTANT.format(Instant.ofEpochMilli(epochMs))
}
