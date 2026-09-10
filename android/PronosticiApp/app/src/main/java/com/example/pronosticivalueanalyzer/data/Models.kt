package com.example.pronosticivalueanalyzer.data

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PredictionReport(
    @SerialName("updated_at") val updatedAt: String = "",
    @SerialName("total_analyzed") val totalAnalyzed: Int = 0,
    @SerialName("predictions") val predictions: List<MatchPrediction> = emptyList()
)

@Serializable
data class MatchPrediction(
    @SerialName("match_id") val matchId: String = "",
    @SerialName("market_recommended") val marketRecommended: String = "NO BET",
    @SerialName("confidence") val confidence: String = "",
    @SerialName("edge") val edge: Double = 0.0,
    @SerialName("ev") val ev: Double = 0.0,
    @SerialName("disclaimer") val disclaimer: String = ""
)
