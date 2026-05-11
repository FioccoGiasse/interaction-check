"use client";

import { useEffect, useState } from "react";

type Source = {
  id: string;
  name: string;
  description: string;
  source_type: string;
  enabled: boolean;
  configured: boolean;
  clinical_interaction_source: boolean;
};

type Drug = {
  id: number;
  aic_code: string;
  commercial_name: string;
  package_description: string;
  marketing_authorisation_holder: string;
  administrative_status: string;
  pharmaceutical_form: string;
  atc_code: string;
  active_ingredient: string;
  supply_regime: string;
  leaflet_url: string;
  rcp_url: string;
  source: string;
  source_url: string;
  source_updated_at: string;
};

function getApiBaseUrl() {
  if (typeof window === "undefined") return "";

  const origin = window.location.origin;

  if (origin.includes("-3000.app.github.dev")) {
    return origin.replace("-3000.app.github.dev", "-8000.app.github.dev");
  }

  return "http://localhost:8000";
}

export default function Home() {
  const [apiStatus, setApiStatus] = useState("Controllo connessione API...");
  const [sources, setSources] = useState<Source[]>([]);
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [sourcesStatus, setSourcesStatus] = useState("Caricamento fonti...");

  const [patientIdentifier, setPatientIdentifier] = useState("");
  const [patientYearOfBirth, setPatientYearOfBirth] = useState("");
  const [clinicianName, setClinicianName] = useState("");
  const [clinicianRole, setClinicianRole] = useState("");
  const [clinicalNotes, setClinicalNotes] = useState("");
  const [consentInformation, setConsentInformation] = useState(false);
  const [consentDataUse, setConsentDataUse] = useState(false);
  const [drugQuery, setDrugQuery] = useState("");
  const [drugResults, setDrugResults] = useState<Drug[]>([]);
  const [drugSearchStatus, setDrugSearchStatus] = useState("");
  const [drugSearchLoading, setDrugSearchLoading] = useState(false);

  useEffect(() => {
    async function checkApi() {
      try {
        const response = await fetch(`${getApiBaseUrl()}/health`);
        const data = await response.json();

        if (data.status === "ok") {
          setApiStatus("Backend collegato correttamente");
        } else {
          setApiStatus("Backend raggiunto, ma risposta non valida");
        }
      } catch {
        setApiStatus("Backend non raggiungibile");
      }
    }

    async function loadSources() {
      try {
        const response = await fetch(`${getApiBaseUrl()}/api/sources`);
        const data = await response.json();

        setSources(data.sources || []);

        const defaultSelected = (data.sources || [])
          .filter((source: Source) => source.enabled)
          .map((source: Source) => source.id);

        setSelectedSources(defaultSelected);
        setSourcesStatus("Fonti caricate correttamente");
      } catch {
        setSourcesStatus("Fonti non raggiungibili");
      }
    }

    checkApi();
    loadSources();
  }, []);

  function toggleSource(sourceId: string) {
    setSelectedSources((current) => {
      if (current.includes(sourceId)) {
        return current.filter((id) => id !== sourceId);
      }

      return [...current, sourceId];
    });
  }

  async function searchDrugs() {
    const cleanQuery = drugQuery.trim();

    if (cleanQuery.length < 2) {
      setDrugSearchStatus("Inserisci almeno 2 caratteri.");
      setDrugResults([]);
      return;
    }

    setDrugSearchLoading(true);
    setDrugSearchStatus("Ricerca in corso...");
    setDrugResults([]);

    try {
      const response = await fetch(
        `${getApiBaseUrl()}/api/drugs/search?q=${encodeURIComponent(cleanQuery)}`
      );

      const data = await response.json();

      setDrugResults(data.results || []);
      setDrugSearchStatus(
        `Risultati trovati: ${data.count || 0}. Fonte: AIFA Anagrafica Farmaci.`
      );
    } catch {
      setDrugSearchStatus("Errore durante la ricerca farmaci.");
      setDrugResults([]);
    } finally {
      setDrugSearchLoading(false);
    }
  }

  return (
    <main className="container">
      <div className="card">
        <div className="logo">ENIA Interaction Check</div>

        <p className="subtitle">
          Piattaforma italiana per supportare la verifica informativa di possibili
          interazioni tra farmaci, alimenti e integratori, usando fonti tracciabili
          e senza generare contenuti clinici non verificati.
        </p>

        <div className="section">
          <h2>Stato sistema</h2>
          <div className="status">{apiStatus}</div>
          <p className="small">
            Frontend e backend sono collegati. I moduli useranno solo fonti
            selezionate e tracciabili.
          </p>
        </div>


        <div className="section">
          <h2>Flusso medico</h2>
          <p className="small">
            Qui costruiremo il flusso per paziente, consenso, verifica e report.
          </p>

          <label className="field">
            <span>ID paziente o iniziali</span>
            <input
              className="input"
              value={patientIdentifier}
              onChange={(event) => setPatientIdentifier(event.target.value)}
              placeholder="Es. Paziente 001 oppure iniziali"
            />
          </label>

          <label className="field">
            <span>Anno di nascita</span>
            <input
              className="input"
              value={patientYearOfBirth}
              onChange={(event) => setPatientYearOfBirth(event.target.value)}
              placeholder="Es. 1978"
            />
          </label>

          <label className="field">
            <span>Nome operatore</span>
            <input
              className="input"
              value={clinicianName}
              onChange={(event) => setClinicianName(event.target.value)}
              placeholder="Es. Dr.ssa Rossi"
            />
          </label>

          <label className="field">
            <span>Ruolo operatore</span>
            <input
              className="input"
              value={clinicianRole}
              onChange={(event) => setClinicianRole(event.target.value)}
              placeholder="Es. Medico, farmacista"
            />
          </label>

          <label className="field">
            <span>Note cliniche rilevanti</span>
            <textarea
              className="textarea"
              value={clinicalNotes}
              onChange={(event) => setClinicalNotes(event.target.value)}
              placeholder="Es. Terapia attuale, allergie note, motivo della verifica. Inserire solo dati necessari."
              rows={4}
            />
          </label>

          <div className="consent-box">
            <h3>Consenso paziente</h3>

            <label className="check-row">
              <input
                type="checkbox"
                checked={consentInformation}
                onChange={(event) => setConsentInformation(event.target.checked)}
              />
              <span>
                Il paziente dichiara di aver ricevuto informazioni sullo scopo informativo dello strumento.
              </span>
            </label>

            <label className="check-row">
              <input
                type="checkbox"
                checked={consentDataUse}
                onChange={(event) => setConsentDataUse(event.target.checked)}
              />
              <span>
                Il paziente acconsente all’utilizzo dei dati inseriti per generare il report della verifica.
              </span>
            </label>
          </div>
        </div>

        <div className="section">
          <h2>Fonti dati disponibili</h2>
          <div className="status">{sourcesStatus}</div>

          <div className="sources-list">
            {sources.map((source) => (
              <label
                key={source.id}
                className={source.enabled ? "source-card" : "source-card disabled"}
              >
                <input
                  type="checkbox"
                  checked={selectedSources.includes(source.id)}
                  disabled={!source.enabled}
                  onChange={() => toggleSource(source.id)}
                />

                <div>
                  <div className="source-title">{source.name}</div>

                  <div className="source-description">
                    {source.description}
                  </div>

                  <div className="badges">
                    <span className="badge">{source.source_type}</span>

                    <span className={source.enabled ? "badge green" : "badge red"}>
                      {source.enabled ? "attiva" : "non attiva"}
                    </span>

                    <span className={source.configured ? "badge green" : "badge amber"}>
                      {source.configured ? "configurata" : "da configurare"}
                    </span>

                    {source.clinical_interaction_source && (
                      <span className="badge blue">
                        fonte interazioni cliniche
                      </span>
                    )}
                  </div>
                </div>
              </label>
            ))}
          </div>

          <div className="selected-box">
            <h3>Fonti selezionate per la verifica</h3>

            {selectedSources.length === 0 ? (
              <p>Nessuna fonte selezionata.</p>
            ) : (
              <ul>
                {selectedSources.map((sourceId) => {
                  const source = sources.find((item) => item.id === sourceId);

                  return <li key={sourceId}>{source?.name || sourceId}</li>;
                })}
              </ul>
            )}
          </div>
        </div>

        <div className="section">
          <h2>Ricerca farmaco AIFA</h2>

          <p className="small">
            Questa ricerca usa l’anagrafica AIFA importata. I risultati mostrano
            sempre la fonte del dato.
          </p>

          <div className="search-row">
            <input
              className="input"
              value={drugQuery}
              onChange={(event) => setDrugQuery(event.target.value)}
              placeholder="Cerca per nome, principio attivo o AIC. Esempio: Tachipirina"
              onKeyDown={(event) => {
                if (event.key === "Enter") {
                  searchDrugs();
                }
              }}
            />

            <button
              className="button"
              onClick={searchDrugs}
              disabled={drugSearchLoading}
            >
              {drugSearchLoading ? "Cerco..." : "Cerca"}
            </button>
          </div>

          {drugSearchStatus && (
            <div className="notice">{drugSearchStatus}</div>
          )}

          <div className="drug-results">
            {drugResults.map((drug) => (
              <div key={drug.id} className="drug-card">
                <div className="drug-header">
                  <h3>{drug.commercial_name}</h3>
                  <span className="badge green">Fonte: {drug.source}</span>
                </div>

                <div className="drug-grid">
                  <p><strong>AIC:</strong> {drug.aic_code || "Non disponibile"}</p>
                  <p><strong>Principio attivo:</strong> {drug.active_ingredient || "Non disponibile"}</p>
                  <p><strong>ATC:</strong> {drug.atc_code || "Non disponibile"}</p>
                  <p><strong>Forma:</strong> {drug.pharmaceutical_form || "Non disponibile"}</p>
                  <p><strong>Regime:</strong> {drug.supply_regime || "Non disponibile"}</p>
                  <p><strong>Titolare:</strong> {drug.marketing_authorisation_holder || "Non disponibile"}</p>
                  <p><strong>Stato:</strong> {drug.administrative_status || "Non disponibile"}</p>
                </div>

                <p><strong>Confezione:</strong> {drug.package_description || "Non disponibile"}</p>

                <div className="link-row">
                  {drug.leaflet_url && (
                    <a href={drug.leaflet_url} target="_blank" rel="noreferrer">
                      Foglio illustrativo
                    </a>
                  )}

                  {drug.rcp_url && (
                    <a href={drug.rcp_url} target="_blank" rel="noreferrer">
                      RCP
                    </a>
                  )}
                </div>

                <p className="small">
                  Dato recuperato da {drug.source}. Import database:{" "}
                  {drug.source_updated_at}
                </p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
