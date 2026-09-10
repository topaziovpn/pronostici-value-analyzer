package com.example.pronosticivalueanalyzer.data

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import retrofit2.Retrofit
import retrofit2.http.GET

interface ApiService {
    @GET("latest.json")
    suspend fun getLatestPredictions(): PredictionReport
}

object RetrofitClient {
    // URL dell'emulatore Android che punta al localhost (127.0.0.1) del tuo PC
    private const val BASE_URL = "http://10.0.2.2:8000/"

    private val json = Json { ignoreUnknownKeys = true }

    val instance: ApiService by lazy {
        val retrofit = Retrofit.Builder()
            .baseUrl(BASE_URL)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
        
        retrofit.create(ApiService::class.java)
    }
}
