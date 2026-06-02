# Demo-Beispiele: Realistische Anfragen

Diese Dateien zeigen realistische Anfragen und Antworten des Enterprise RAG Systems mit deutschen Banking-Regulierungsfragen.

## Demo 1: Datensicherung & Wiederherstellung

**Datei**: `demo-screenshot-01-response.json`

**Frage** (auf Deutsch):
> Welche Anforderungen gibt es für die Datensicherung und Wiederherstellung in Finanzinstituten?

**Anwendungsfall**: 
Compliance-Officer überprüft Backup- und Disaster-Recovery-Anforderungen

**Was das System demonstriert**:
- ✅ Deutsche Finanzfragen verstehen
- ✅ Relevant Regulations-Sections finden (BAIT 4.3, Rundschreiben)
- ✅ Strukturierte, aussagekräftige Antwort mit Unterpunkten
- ✅ Source Attribution mit genauen Links

---

## Demo 2: IT-Sicherheitsanforderungen BAIT

**Datei**: `demo-screenshot-02-response.json`

**Frage** (auf Deutsch):
> Was sind die wichtigsten IT-Sicherheitsanforderungen nach BAIT?

**Anwendungsfall**: 
IT-Sicherheitsteam recherchiert BAIT-Compliance-Anforderungen

**Was das System demonstriert**:
- ✅ Komplexe Fachfragen beantworten
- ✅ Multiple Regulations-Quellen verbinden (BAIT, MaRisk, Merkblatt)
- ✅ Anforderungen kategorisieren und priorisieren
- ✅ Praktische Implementierungshinweise geben

---

## Response-Format Erklärung

Jede Response enthält:

```json
{
  "query": "Die originale deutsche Frage",
  "answer": "Detaillierte Antwort mit Struktur",
  "sources": ["Quellenangaben mit Kontext"],
  "source_links": ["Direkte Links zu Regulations-Dokumenten"],
  "session_id": "Für Follow-up Fragen verwendbar"
}
```

**Merkmale**:
- **Mehrsprachig**: Eingaben auf Deutsch, natürliche Antwort
- **Quellenbasiert**: Jede Behauptung ist traceable zu Regulations-Dokumenten
- **Praktisch**: Actionable Informationen für Compliance-Teams
- **Vollständig**: Abdeckung aller relevanten Aspekte

---

## Verwendung als Screenshot-Referenzen

Diese JSON-Dateien können als:
1. **API-Response-Beispiele** in Portfolio-Dokumentation verwendet
2. **Basis für UI-Screenshots** - zeigen, was im Browser angezeigt wird
3. **Realistische Use Cases** für Demo-Zwecke
4. **Validation-Tests** für das System

---

## Für Portfolio/Website Integration

Zum Einbinden auf coeln.dev:

```markdown
### Beispiel 1: Backup & Disaster Recovery

Das System beantwortet deutsche Regulierungsfragen präzise mit Quellenangaben:

**Eingabe**: "Welche Anforderungen gibt es für Datensicherung?"
**Ausgabe**: [Strukturierte Antwort mit BAIT-Referenzen]
**Quelle**: BaFin BAIT Abschnitt 4.3

Siehe: [demo-screenshot-01-response.json](./demo-screenshot-01-response.json)
```

---

**Hinweis**: Diese sind reduzierte Beispiele. Echte Responses vom System sind ausführlicher und basieren auf den tatsächlichen Regulations-Dokumenten im `/docs` Verzeichnis.
