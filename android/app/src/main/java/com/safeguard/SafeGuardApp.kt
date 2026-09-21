package com.safeguard

import android.app.Application
import com.safeguard.alert.AlertManager

/**
 * Application subclass – creates notification channels once at startup so that
 * all channels exist before any service or receiver tries to post to them.
 */
class SafeGuardApp : Application() {

    lateinit var alertManager: AlertManager
        private set

    override fun onCreate() {
        super.onCreate()
        alertManager = AlertManager(this)
        alertManager.createChannels()
    }
}
