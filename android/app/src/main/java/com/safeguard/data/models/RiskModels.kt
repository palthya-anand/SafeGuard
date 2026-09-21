package com.safeguard.data.models

/**
 * Request body for the /predict-risk endpoint.
 */
data class PredictRiskRequest(
    val latitude: Double,
    val longitude: Double,
    val speed_kmh: Float,
    val speed_limit_kmh: Float?,
    val traffic_level: String,
    val weather: String,
    val timestamp: String,
    val device_id: String
)

/**
 * Response from the /predict-risk endpoint.
 */
data class PredictRiskResponse(
    val risk_score: Int,
    val risk_level: String,
    val hotspot: Boolean,
    val distance_to_hotspot_m: Float?,
    val speed_limit_kmh: Float?,
    val message: String,
    val reasons: List<String>,
    val recommended_action: String,
    val traffic_source: String? = null,
    val weather_source: String? = null,
    val provider_mode: String? = "mock"
)

/**
 * Request body for the /events/telemetry endpoint.
 */
data class TelemetryRequest(
    val device_id: String,
    val timestamp: String,
    val latitude: Double,
    val longitude: Double,
    val speed_kmh: Float,
    val traffic_level: String,
    val weather_code: String
)

/**
 * Enumeration of discrete risk levels returned by the backend.
 * Ordered from lowest to highest severity so ordinal comparisons are valid.
 */
enum class RiskLevel {
    LOW,
    MODERATE,
    HIGH,
    CRITICAL;

    companion object {
        /**
         * Safely parse a string (case-insensitive) to [RiskLevel], defaulting to [LOW].
         */
        fun fromString(value: String): RiskLevel =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: LOW
    }
}
