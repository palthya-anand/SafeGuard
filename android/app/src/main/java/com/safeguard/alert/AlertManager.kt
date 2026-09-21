package com.safeguard.alert

import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.media.AudioAttributes
import android.os.Build
import android.os.VibrationEffect
import android.os.Vibrator
import android.os.VibratorManager
import android.speech.tts.TextToSpeech
import android.util.Log
import androidx.core.app.NotificationCompat
import com.safeguard.MainActivity
import com.safeguard.R
import com.safeguard.data.models.PredictRiskResponse
import com.safeguard.data.models.RiskLevel
import java.util.Locale

/**
 * Centralises all driver alert logic: notification channels, risk state-machine,
 * vibration, and TTS voice output.
 *
 * ### Channels
 * | ID | Importance | Purpose |
 * |----|-----------|---------|
 * | OVERSPEED | HIGH | Local speed-limit breach |
 * | HOTSPOT   | HIGH | Approaching a known danger zone |
 * | HIGH_RISK | MAX  | Backend-detected HIGH / CRITICAL |
 * | WEATHER   | DEFAULT | Adverse weather advisory |
 * | MONITORING | LOW | Persistent foreground-service notice |
 *
 * ### Risk state-machine
 * Alerts only fire on upward transitions (LOW→MOD, MOD→HIGH, HIGH→CRITICAL).
 * Downward transitions silently reset the state so the next escalation re-fires.
 * Same-level re-alerts are suppressed by a 30-second per-type cooldown.
 */
class AlertManager(private val context: Context) {

    companion object {
        private const val TAG = "AlertManager"

        const val CHANNEL_OVERSPEED  = "safeguard_overspeed"
        const val CHANNEL_HOTSPOT    = "safeguard_hotspot"
        const val CHANNEL_HIGH_RISK  = "safeguard_high_risk"
        const val CHANNEL_WEATHER    = "safeguard_weather"
        const val CHANNEL_MONITORING = "safeguard_monitoring"

        private const val COOLDOWN_MS = 30_000L

        private const val NOTIF_OVERSPEED  = 100
        private const val NOTIF_HOTSPOT    = 101
        private const val NOTIF_HIGH_RISK  = 102
        private const val NOTIF_WEATHER    = 103
    }

    // -------------------------------------------------------------------------
    // State
    // -------------------------------------------------------------------------

    private var currentRiskLevel = RiskLevel.LOW
    private val cooldowns = mutableMapOf<String, Long>()
    private val notifManager = context.getSystemService(NotificationManager::class.java)

    private var tts: TextToSpeech? = null
    private var ttsReady = false

    init {
        tts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                tts?.language = Locale.getDefault()
                ttsReady = true
                Log.d(TAG, "TTS initialised")
            } else {
                Log.w(TAG, "TTS init failed with status $status")
            }
        }
    }

    // -------------------------------------------------------------------------
    // Channel creation (call once from Application.onCreate)
    // -------------------------------------------------------------------------

    fun createChannels() {
        val audioAttr = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_NOTIFICATION)
            .build()

        val channels = listOf(
            NotificationChannel(
                CHANNEL_OVERSPEED, "Overspeed Alert", NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts when you exceed the speed limit"
                enableVibration(true)
            },
            NotificationChannel(
                CHANNEL_HOTSPOT, "Hotspot Alert", NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts when you approach a known accident hotspot"
                enableVibration(true)
            },
            NotificationChannel(
                CHANNEL_HIGH_RISK, "High Risk Alert", NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Alerts for HIGH and CRITICAL risk conditions"
                enableVibration(true)
                setSound(null, audioAttr)   // TTS carries the audio for MAX
            },
            NotificationChannel(
                CHANNEL_WEATHER, "Weather Advisory", NotificationManager.IMPORTANCE_DEFAULT
            ).apply {
                description = "Weather-related safety advisories"
            },
            NotificationChannel(
                CHANNEL_MONITORING, "SafeGuard Monitoring", NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Persistent notice while drive monitoring is active"
            }
        )
        channels.forEach { notifManager.createNotificationChannel(it) }
        Log.d(TAG, "Notification channels created")
    }

    // -------------------------------------------------------------------------
    // Risk state-machine
    // -------------------------------------------------------------------------

    /**
     * Process a fresh risk response from the backend and fire alerts only when
     * the risk level escalates (or when the driver enters a hotspot zone).
     */
    fun handleRiskResponse(response: PredictRiskResponse) {
        val incoming = RiskLevel.fromString(response.risk_level)

        when {
            incoming > currentRiskLevel -> {
                // Escalation — always alert
                escalate(incoming, response)
            }
            incoming < currentRiskLevel -> {
                // De-escalation — silently reset so the next escalation re-fires
                Log.d(TAG, "Risk de-escalated: $currentRiskLevel → $incoming")
                currentRiskLevel = incoming
            }
            else -> {
                // Same level — respect cooldown
                if (!isCoolingDown("risk_${incoming.name}")) {
                    escalate(incoming, response)
                }
            }
        }

        // Independent hotspot check
        if (response.hotspot && response.distance_to_hotspot_m != null) {
            showHotspotAlert(response.distance_to_hotspot_m)
        }
    }

    private fun escalate(level: RiskLevel, response: PredictRiskResponse) {
        currentRiskLevel = level
        when (level) {
            RiskLevel.CRITICAL, RiskLevel.HIGH -> {
                showHighRiskAlert(response.risk_score, response.reasons)
                vibrate(longArrayOf(0, 300, 100, 300, 100, 600))
                speakAlert("Warning! ${level.name} risk detected. ${response.recommended_action}")
            }
            RiskLevel.MODERATE -> {
                showModerateRiskNotification(response.risk_score, response.message)
            }
            RiskLevel.LOW -> { /* in-app indicator only */ }
        }
        setCooldown("risk_${level.name}")
    }

    // -------------------------------------------------------------------------
    // Individual alert builders
    // -------------------------------------------------------------------------

    /** Display an overspeed notification (called by local service check). */
    fun showOverspeedAlert(currentSpeed: Float, limit: Float) {
        if (isCoolingDown("overspeed")) return
        setCooldown("overspeed")

        val msg = context.getString(R.string.alert_overspeed, currentSpeed.toInt(), limit.toInt())
        val notif = buildNotification(
            channelId = CHANNEL_OVERSPEED,
            title     = context.getString(R.string.alert_overspeed_title),
            text      = msg,
            priority  = NotificationCompat.PRIORITY_HIGH
        )
        notifManager.notify(NOTIF_OVERSPEED, notif)
        vibrate(longArrayOf(0, 200, 100, 200))
        speakAlert(msg)
    }

    /** Display a hotspot proximity notification. */
    fun showHotspotAlert(distanceM: Float) {
        if (isCoolingDown("hotspot")) return
        setCooldown("hotspot")

        val msg = context.getString(R.string.alert_hotspot, distanceM.toInt())
        val notif = buildNotification(
            channelId = CHANNEL_HOTSPOT,
            title     = context.getString(R.string.alert_hotspot_title),
            text      = msg,
            priority  = NotificationCompat.PRIORITY_HIGH
        )
        notifManager.notify(NOTIF_HOTSPOT, notif)
        vibrate(longArrayOf(0, 150, 80, 150))
        speakAlert(msg)
    }

    /** Display a HIGH / CRITICAL risk notification from the backend score. */
    fun showHighRiskAlert(score: Int, reasons: List<String>) {
        if (isCoolingDown("high_risk")) return
        setCooldown("high_risk")

        val reasonSummary = reasons.take(3).joinToString("; ")
        val msg = context.getString(R.string.alert_high_risk, score, reasonSummary)
        val notif = buildNotification(
            channelId = CHANNEL_HIGH_RISK,
            title     = context.getString(R.string.alert_high_risk_title),
            text      = msg,
            priority  = NotificationCompat.PRIORITY_MAX
        )
        notifManager.notify(NOTIF_HIGH_RISK, notif)
    }

    private fun showModerateRiskNotification(score: Int, message: String) {
        if (isCoolingDown("moderate_risk")) return
        setCooldown("moderate_risk")

        val notif = buildNotification(
            channelId = CHANNEL_HIGH_RISK,
            title     = context.getString(R.string.risk_moderate),
            text      = "Risk score $score – $message",
            priority  = NotificationCompat.PRIORITY_DEFAULT
        )
        notifManager.notify(NOTIF_HIGH_RISK, notif)
    }

    // -------------------------------------------------------------------------
    // TTS
    // -------------------------------------------------------------------------

    /** Speak [text] aloud via the Android TTS engine (if available). */
    fun speakAlert(text: String) {
        if (!ttsReady) {
            Log.w(TAG, "TTS not ready, skipping speech")
            return
        }
        tts?.speak(text, TextToSpeech.QUEUE_FLUSH, null, "sg_alert_${System.currentTimeMillis()}")
    }

    // -------------------------------------------------------------------------
    // Cleanup
    // -------------------------------------------------------------------------

    /** Cancel all active SafeGuard notifications. */
    fun dismissAll() {
        listOf(NOTIF_OVERSPEED, NOTIF_HOTSPOT, NOTIF_HIGH_RISK, NOTIF_WEATHER)
            .forEach { notifManager.cancel(it) }
    }

    /** Release TTS engine resources. Call from Activity/Application onDestroy. */
    fun release() {
        tts?.stop()
        tts?.shutdown()
        tts = null
        ttsReady = false
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    private fun buildNotification(
        channelId: String,
        title: String,
        text: String,
        priority: Int
    ): android.app.Notification {
        val pendingIntent = PendingIntent.getActivity(
            context, 0,
            Intent(context, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT
        )
        return NotificationCompat.Builder(context, channelId)
            .setSmallIcon(R.drawable.ic_shield_notification)
            .setContentTitle(title)
            .setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(text))
            .setPriority(priority)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent)
            .build()
    }

    private fun vibrate(pattern: LongArray) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            val manager = context.getSystemService(VibratorManager::class.java)
            manager?.defaultVibrator?.vibrate(VibrationEffect.createWaveform(pattern, -1))
        } else {
            @Suppress("DEPRECATION")
            val vibrator = context.getSystemService(Vibrator::class.java)
            vibrator?.vibrate(VibrationEffect.createWaveform(pattern, -1))
        }
    }

    private fun isCoolingDown(key: String): Boolean {
        val last = cooldowns[key] ?: return false
        return (System.currentTimeMillis() - last) < COOLDOWN_MS
    }

    private fun setCooldown(key: String) {
        cooldowns[key] = System.currentTimeMillis()
    }
}
