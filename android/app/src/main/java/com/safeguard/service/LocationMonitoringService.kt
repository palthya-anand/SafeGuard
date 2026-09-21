package com.safeguard.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import android.os.Looper
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.android.gms.location.*
import com.safeguard.MainActivity
import com.safeguard.R
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

/**
 * Foreground service that continuously acquires high-accuracy location fixes and
 * publishes them via [locationFlow].  An optional local overspeed check is applied
 * each time a fix arrives.
 *
 * Speed limit can be updated at runtime by calling [updateSpeedLimit].
 * The service enforces a 30-second cooldown per alert type to avoid buzzing the
 * driver with repeated notifications.
 */
class LocationMonitoringService : Service() {

    // -------------------------------------------------------------------------
    // Public shared state
    // -------------------------------------------------------------------------

    companion object {
        /** Broadcast action emitted for every location fix. */
        const val ACTION_LOCATION_UPDATE = "com.safeguard.ACTION_LOCATION_UPDATE"
        const val EXTRA_LATITUDE       = "latitude"
        const val EXTRA_LONGITUDE      = "longitude"
        const val EXTRA_SPEED_KMH      = "speed_kmh"

        private const val CHANNEL_ID            = "safeguard_monitoring"
        private const val NOTIFICATION_ID       = 1
        private const val OVERSPEED_COOLDOWN_MS = 30_000L

        /** Default urban speed limit in km/h. */
        private const val DEFAULT_SPEED_LIMIT_KMH = 50f

        /** Hot SharedFlow so any collector sees the latest fix immediately. */
        private val _locationFlow = MutableSharedFlow<Triple<Double, Double, Float>>(
            replay = 1,
            extraBufferCapacity = 8
        )
        val locationFlow = _locationFlow.asSharedFlow()

        /** Allow the ViewModel / AlertManager to update the active limit. */
        @Volatile
        var currentSpeedLimit: Float = DEFAULT_SPEED_LIMIT_KMH
            private set

        fun updateSpeedLimit(limit: Float) {
            currentSpeedLimit = limit
        }
    }

    // -------------------------------------------------------------------------
    // Private fields
    // -------------------------------------------------------------------------

    private val tag = "LocationMonitoringService"
    private lateinit var fusedClient: FusedLocationProviderClient
    private var lastOverspeedAlertMs = 0L

    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            val lat      = location.latitude
            val lon      = location.longitude
            // Android location speed is in m/s; convert to km/h
            val speedKmh = (location.speed * 3.6f).coerceAtLeast(0f)

            // Publish to SharedFlow (non-blocking; extra capacity absorbs bursts)
            _locationFlow.tryEmit(Triple(lat, lon, speedKmh))

            // Broadcast for the Activity's BroadcastReceiver
            sendBroadcast(Intent(ACTION_LOCATION_UPDATE).apply {
                putExtra(EXTRA_LATITUDE,  lat)
                putExtra(EXTRA_LONGITUDE, lon)
                putExtra(EXTRA_SPEED_KMH, speedKmh)
            })

            // Local overspeed guard (doesn't require backend round-trip)
            checkLocalOverspeed(speedKmh)
        }
    }

    // -------------------------------------------------------------------------
    // Service lifecycle
    // -------------------------------------------------------------------------

    override fun onCreate() {
        super.onCreate()
        fusedClient = LocationServices.getFusedLocationProviderClient(this)
        createNotificationChannel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForegroundWithNotification()
        requestLocationUpdates()
        Log.i(tag, "Location monitoring started")
        return START_STICKY
    }

    override fun onDestroy() {
        fusedClient.removeLocationUpdates(locationCallback)
        Log.i(tag, "Location monitoring stopped")
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // -------------------------------------------------------------------------
    // Foreground notification
    // -------------------------------------------------------------------------

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "SafeGuard Monitoring",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Persistent notification while SafeGuard is monitoring your drive"
        }
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun startForegroundWithNotification() {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        val notification: Notification = NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.app_name))
            .setContentText("SafeGuard is monitoring your drive")
            .setSmallIcon(R.drawable.ic_shield_notification)
            .setOngoing(true)
            .setContentIntent(pendingIntent)
            .build()

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
            startForeground(NOTIFICATION_ID, notification, ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION)
        } else {
            startForeground(NOTIFICATION_ID, notification)
        }
    }

    // -------------------------------------------------------------------------
    // Location updates
    // -------------------------------------------------------------------------

    private fun requestLocationUpdates() {
        val request = LocationRequest.Builder(
            Priority.PRIORITY_HIGH_ACCURACY,
            2_000L          // desired interval: 2 s
        ).apply {
            setMinUpdateIntervalMillis(1_000L)   // fastest: 1 s
            setWaitForAccurateLocation(false)
        }.build()

        try {
            fusedClient.requestLocationUpdates(
                request,
                locationCallback,
                Looper.getMainLooper()
            )
        } catch (se: SecurityException) {
            Log.e(tag, "Location permission not granted", se)
            stopSelf()
        }
    }

    // -------------------------------------------------------------------------
    // Local overspeed check
    // -------------------------------------------------------------------------

    private fun checkLocalOverspeed(speedKmh: Float) {
        val limit = currentSpeedLimit
        val now   = System.currentTimeMillis()
        if (speedKmh > (limit + 5f) && (now - lastOverspeedAlertMs) > OVERSPEED_COOLDOWN_MS) {
            lastOverspeedAlertMs = now
            Log.w(tag, "Local overspeed: ${speedKmh.toInt()} km/h in ${limit.toInt()} km/h zone")
            // Notify the AlertManager via a broadcast so it can show the notification
            sendBroadcast(Intent("com.safeguard.ACTION_OVERSPEED_LOCAL").apply {
                putExtra("speed_kmh", speedKmh)
                putExtra("limit_kmh", limit)
            })
        }
    }
}
