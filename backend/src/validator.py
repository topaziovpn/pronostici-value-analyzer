def validate_prediction(prediction):
    """
    Controlla che l'output sia strutturalmente valido e sicuro.
    Forza l'inserimento del disclaimer di responsabilit.
    """
    disclaimer_obbligatorio = "Nessuna scommessa  sicura. Gioca responsabilmente."
    
    # Forza il disclaimer
    prediction["disclaimer"] = disclaimer_obbligatorio
    
    # Rimuovi termini pericolosi come "sicuro", "garantito" dall'analisi
    analisi = str(prediction.get("analysis_360", ""))
    for bad_word in ["sicuro", "garantito", "100%", "infallibile"]:
        # Case insensitive replace
        import re
        analisi = re.sub(f"(?i){bad_word}", "***", analisi)
    prediction["analysis_360"] = analisi
    
    # Rimuovi dai value level
    for pred in prediction.get("top_predictions", []):
        lvl = str(pred.get("value_level", ""))
        for bad_word in ["sicuro", "garantito", "100%", "infallibile"]:
            import re
            lvl = re.sub(f"(?i){bad_word}", "***", lvl)
        pred["value_level"] = lvl
            
    return prediction
