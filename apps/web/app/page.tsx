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
            Frontend e backend sono collegati. I prossimi moduli useranno solo
            fonti selezionate e tracciabili.
          </p>
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
                  <div className="source-title">
                    {source.name}
                  </div>

                  <div className="source-description">
                    {source.description}
                  </div>

                  <div className="badges">
                    <span className="badge">
                      {source.source_type}
                    </span>

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

                  return (
                    <li key={sourceId}>
                      {source?.name || sourceId}
                    </li>
                  );
                })}
              </ul>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}
