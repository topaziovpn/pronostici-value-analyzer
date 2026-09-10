package com.example.pronosticivalueanalyzer

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.viewModels
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.pronosticivalueanalyzer.data.MainViewModel
import com.example.pronosticivalueanalyzer.data.MatchPrediction
import com.example.pronosticivalueanalyzer.data.UiState
import java.text.SimpleDateFormat
import java.util.*

class MainActivity : ComponentActivity() {
    private val viewModel: MainViewModel by viewModels()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MaterialTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    PronosticiAppScreen(viewModel)
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun PronosticiAppScreen(viewModel: MainViewModel) {
    val uiState by viewModel.uiState.collectAsState()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Value Analyzer", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primaryContainer,
                    titleContentColor = MaterialTheme.colorScheme.onPrimaryContainer
                ),
                actions = {
                    Button(onClick = { viewModel.fetchPredictions() }) {
                        Text("Aggiorna")
                    }
                }
            )
        },
        bottomBar = {
            // Footer fisso con disclaimer obbligatorio globale
            Surface(color = Color(0xFFD32F2F), modifier = Modifier.fillMaxWidth()) {
                Text(
                    text = "NESSUNA SCOMMESSA È SICURA. GIOCA RESPONSABILMENTE.",
                    color = Color.White,
                    fontWeight = FontWeight.Bold,
                    fontSize = 12.sp,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(8.dp)
                )
            }
        }
    ) { innerPadding ->
        Box(modifier = Modifier.padding(innerPadding).fillMaxSize()) {
            when (val state = uiState) {
                is UiState.Loading -> {
                    CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
                }
                is UiState.Error -> {
                    Column(
                        modifier = Modifier.align(Alignment.Center).padding(16.dp),
                        horizontalAlignment = Alignment.CenterHorizontally
                    ) {
                        Text("Errore", color = Color.Red, fontWeight = FontWeight.Bold, fontSize = 20.sp)
                        Spacer(modifier = Modifier.height(8.dp))
                        Text(state.message, textAlign = TextAlign.Center)
                    }
                }
                is UiState.Success -> {
                    Column {
                        // Alert Dati Vecchi
                        if (isDataOld(state.report.updatedAt)) {
                            Surface(color = Color(0xFFFFCC00), modifier = Modifier.fillMaxWidth()) {
                                Text(
                                    text = "ATTENZIONE: Dati non aggiornati da oltre 24 ore.",
                                    color = Color.Black,
                                    fontWeight = FontWeight.Bold,
                                    modifier = Modifier.padding(8.dp),
                                    textAlign = TextAlign.Center
                                )
                            }
                        }
                        
                        Text(
                            text = "Ultimo aggiornamento: ${formatDate(state.report.updatedAt)}",
                            style = MaterialTheme.typography.labelMedium,
                            modifier = Modifier.padding(8.dp).fillMaxWidth(),
                            textAlign = TextAlign.Center
                        )
                        
                        LazyColumn(
                            contentPadding = PaddingValues(16.dp),
                            verticalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            items(state.report.predictions) { match ->
                                MatchCard(match)
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
fun MatchCard(match: MatchPrediction) {
    val isNoBet = match.marketRecommended.uppercase().contains("NO BET")
    val cardColor = if (isNoBet) Color(0xFFF5F5F5) else Color.White
    val edgeColor = if (match.edge > 0.1) Color(0xFF4CAF50) else if (match.edge > 0) Color(0xFFFF9800) else Color.Gray

    Card(
        elevation = CardDefaults.cardElevation(defaultElevation = if (isNoBet) 1.dp else 4.dp),
        colors = CardDefaults.cardColors(containerColor = cardColor),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(text = match.matchId, fontWeight = FontWeight.Bold, fontSize = 18.sp)
            Spacer(modifier = Modifier.height(8.dp))
            
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("Mercato: ", fontWeight = FontWeight.SemiBold)
                Text(match.marketRecommended, color = if (isNoBet) Color.Gray else Color.Black)
            }
            
            if (!isNoBet) {
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Vantaggio (Edge): ", fontWeight = FontWeight.SemiBold)
                    Text(String.format("%.1f%%", match.edge * 100), color = edgeColor, fontWeight = FontWeight.Bold)
                }
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Valore Atteso (EV): ", fontWeight = FontWeight.SemiBold)
                    Text(String.format("%.2f", match.ev))
                }
                Spacer(modifier = Modifier.height(4.dp))
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Confidenza: ", fontWeight = FontWeight.SemiBold)
                    Text(match.confidence.uppercase())
                }
            }
            
            Spacer(modifier = Modifier.height(12.dp))
            Text(
                text = match.disclaimer,
                fontSize = 10.sp,
                color = Color.Gray,
                fontStyle = androidx.compose.ui.text.font.FontStyle.Italic
            )
        }
    }
}

// Helpers per le date
fun formatDate(isoString: String): String {
    if (isoString.isBlank()) return "Sconosciuto"
    return try {
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
        val formatter = SimpleDateFormat("dd/MM/yyyy HH:mm", Locale.getDefault())
        val date = parser.parse(isoString)
        date?.let { formatter.format(it) } ?: isoString
    } catch (e: Exception) {
        isoString
    }
}

fun isDataOld(isoString: String): Boolean {
    if (isoString.isBlank()) return false
    return try {
        val parser = SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", Locale.getDefault())
        val date = parser.parse(isoString)
        if (date != null) {
            val now = Date()
            val diff = now.time - date.time
            diff > 24 * 60 * 60 * 1000 // 24 ore
        } else false
    } catch (e: Exception) {
        false
    }
}
