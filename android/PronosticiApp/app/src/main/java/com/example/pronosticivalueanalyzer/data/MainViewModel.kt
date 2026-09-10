package com.example.pronosticivalueanalyzer.data

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

sealed class UiState {
    object Loading : UiState()
    data class Success(val report: PredictionReport) : UiState()
    data class Error(val message: String) : UiState()
}

class MainViewModel : ViewModel() {
    private val _uiState = MutableStateFlow<UiState>(UiState.Loading)
    val uiState: StateFlow<UiState> = _uiState

    init {
        fetchPredictions()
    }

    fun fetchPredictions() {
        viewModelScope.launch {
            _uiState.value = UiState.Loading
            try {
                // In produzione utilizzerà l'URL reale. 
                // Per test potremmo iniettare dei mock
                val report = RetrofitClient.instance.getLatestPredictions()
                
                // Ordina le predizioni per Edge decrescente
                val sortedPredictions = report.predictions.sortedByDescending { it.edge }
                val sortedReport = report.copy(predictions = sortedPredictions)
                
                _uiState.value = UiState.Success(sortedReport)
            } catch (e: Exception) {
                _uiState.value = UiState.Error("Errore di rete: ${e.message ?: "Impossibile scaricare i dati"}")
            }
        }
    }
}
