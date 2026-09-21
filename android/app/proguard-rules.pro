# ============================================================
# SafeGuard ProGuard Rules
# ============================================================

# ---- Retrofit / OkHttp ----
-dontwarn okhttp3.**
-dontwarn okio.**
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Signature
-keepattributes Exceptions
-keepattributes *Annotation*

# ---- Gson ----
-dontwarn com.google.gson.**
-keep class com.google.gson.** { *; }
-keepattributes EnclosingMethod

# ---- SafeGuard data models (used as Gson/Retrofit bodies) ----
-keep class com.safeguard.data.models.** { *; }

# ---- Kotlin coroutines ----
-keepnames class kotlinx.coroutines.internal.MainDispatcherFactory {}
-keepnames class kotlinx.coroutines.CoroutineExceptionHandler {}
-keepclassmembernames class kotlinx.** {
    volatile <fields>;
}

# ---- Android ----
-keepattributes SourceFile,LineNumberTable
-renamesourcefileattribute SourceFile
