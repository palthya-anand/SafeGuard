package com.safeguard.network

import com.safeguard.data.models.PredictRiskRequest
import com.safeguard.data.models.PredictRiskResponse
import com.safeguard.data.models.TelemetryRequest
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Response
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import retrofit2.http.*
import java.util.concurrent.TimeUnit

/**
 * Retrofit interface describing all SafeGuard backend endpoints.
 */
interface SafeGuardApi {

    /** Predict the current risk level for a given position and context. */
    @POST("predict-risk")
    suspend fun predictRisk(@Body request: PredictRiskRequest): Response<PredictRiskResponse>

    /** Stream a single telemetry record to the backend. */
    @POST("events/telemetry")
    suspend fun postTelemetry(@Body request: TelemetryRequest): Response<Map<String, Any>>

    /** Lightweight health-check to verify backend connectivity. */
    @GET("health")
    suspend fun health(): Response<Map<String, Any>>

    /** Fetch hotspots within [radiusM] metres of the supplied coordinates. */
    @GET("hotspots/nearby")
    suspend fun nearbyHotspots(
        @Query("lat") lat: Double,
        @Query("lon") lon: Double,
        @Query("radius_m") radiusM: Int = 1000
    ): Response<List<Map<String, Any>>>
}

/**
 * Singleton factory that builds a [SafeGuardApi] against the given [baseUrl].
 * Uses an [HttpLoggingInterceptor] (BODY level in debug builds) and conservative
 * connect/read timeouts suited to mobile networks.
 */
object RetrofitClient {

    fun create(baseUrl: String): SafeGuardApi {
        val logging = HttpLoggingInterceptor().apply {
            level = HttpLoggingInterceptor.Level.BODY
        }
        val client = OkHttpClient.Builder()
            .addInterceptor(logging)
            .connectTimeout(10, TimeUnit.SECONDS)
            .readTimeout(15, TimeUnit.SECONDS)
            .build()

        return Retrofit.Builder()
            .baseUrl(baseUrl)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(SafeGuardApi::class.java)
    }
}
