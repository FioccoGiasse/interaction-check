"use client";

import { useEffect, useState } from "react";

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

    checkApi();
  }, []);

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
            Questo è solo il primo collegamento tra interfaccia web e backend.
            Nei prossimi passi aggiungeremo AIFA, selezione fonti, consenso,
            report e PDF.
          </p>
        </div>
      </div>
    </main>
  );
}
