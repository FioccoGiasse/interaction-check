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
  const [consentReportGeneration, setConsentReportGeneration] = useState(false);
  const [consentCopyReceived, setConsentCopyReceived] = useState(false);
  const consentComplete =
    consentInformation &&
    consentDataUse &&
    consentReportGeneration &&
    consentCopyReceived;

  const [drugQuery, setDrugQuery] = useState("");
  const [drugResults, setDrugResults] = useState<Drug[]>([]);
  const [drugSearchStatus, setDrugSearchStatus] = useState("");
  const [drugSearchLoading, setDrugSearchLoading] = useState(false);
  const [selectedDrugs, setSelectedDrugs] = useState<Drug[]>([]);
  const [foodInteractionStatus, setFoodInteractionStatus] = useState("");
  const [foodInteractionLoading, setFoodInteractionLoading] = useState(false);
  const [foodInteractions, setFoodInteractions] = useState<any[]>([]);
  const [rcpSourcesChecked, setRcpSourcesChecked] = useState<any[]>([]);
  const [acceptedFoodInteractionIds, setAcceptedFoodInteractionIds] = useState<any[]>([]);
  const [excludedFoodInteractionIds, setExcludedFoodInteractionIds] = useState<any[]>([]);

  const [drugInteractionStatus, setDrugInteractionStatus] = useState("");
  const [drugInteractionLoading, setDrugInteractionLoading] = useState(false);
  const [drugInteractions, setDrugInteractions] = useState<any[]>([]);
  const [drugRcpSourcesChecked, setDrugRcpSourcesChecked] = useState<any[]>([]);
  const [acceptedDrugInteractionIds, setAcceptedDrugInteractionIds] = useState<any[]>([]);
  const [excludedDrugInteractionIds, setExcludedDrugInteractionIds] = useState<any[]>([]);

  const [drivingSectionStatus, setDrivingSectionStatus] = useState("");
  const [drivingSectionLoading, setDrivingSectionLoading] = useState(false);
  const [drivingSections, setDrivingSections] = useState<any[]>([]);
  const [acceptedDrivingSectionIds, setAcceptedDrivingSectionIds] = useState<any[]>([]);
  const [excludedDrivingSectionIds, setExcludedDrivingSectionIds] = useState<any[]>([]);

  const [reportPayload, setReportPayload] = useState<any | null>(null);
  const [reportStatus, setReportStatus] = useState("");
  const [pdfLoading, setPdfLoading] = useState("");
  const [foodSupplementInput, setFoodSupplementInput] = useState("");


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

  function addDrugToReport(drug: Drug) {
    setSelectedDrugs((current) => {
      const alreadySelected = current.some((item) => item.id === drug.id);

      if (alreadySelected) {
        return current;
      }

      return [...current, drug];
    });
  }

  function removeDrugFromReport(drugId: number) {
    setSelectedDrugs((current) =>
      current.filter((drug) => drug.id !== drugId)
    );
  }

  async function checkSuggestedFoodInteractions() {
    if (selectedDrugs.length === 0) {
      setFoodInteractionStatus("Seleziona almeno un farmaco prima di cercare interazioni alimentari.");
      return;
    }

    setFoodInteractionLoading(true);
    setFoodInteractionStatus("Ricerca interazioni alimentari nelle fonti selezionate...");

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/interactions/food/suggested`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          selected_drugs: selectedDrugs,
          selected_sources: selectedSources
        })
      });

      const data = await response.json();

      setFoodInteractions(data.interactions || []);
      setRcpSourcesChecked(data.rcp_sources_checked || []);
      setAcceptedFoodInteractionIds([]);
      setExcludedFoodInteractionIds([]);
      setFoodInteractionStatus(data.message || "Verifica completata.");
    } catch {
      setFoodInteractionStatus("Errore durante la verifica delle interazioni alimentari.");
    } finally {
      setFoodInteractionLoading(false);
    }
  }

  const checkSuggestedDrugInteractions = async () => {
    setDrugInteractionLoading(true);
    setDrugInteractionStatus("");

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/interactions/drugs/suggested`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          selected_drugs: selectedDrugs,
          selected_sources: selectedSources
        })
      });

      if (!response.ok) {
        throw new Error("Errore durante la verifica delle interazioni con altri farmaci.");
      }

      const data = await response.json();

      setDrugInteractions(data.interactions || []);
      setDrugRcpSourcesChecked(data.rcp_sources_checked || []);
      setAcceptedDrugInteractionIds([]);
      setExcludedDrugInteractionIds([]);
      setDrugInteractionStatus(data.message || "Verifica completata.");
    } catch (error) {
      setDrugInteractionStatus("Errore durante la verifica delle interazioni con altri farmaci.");
    } finally {
      setDrugInteractionLoading(false);
    }
  };

  const checkDrivingSection = async () => {
    setDrivingSectionLoading(true);
    setDrivingSectionStatus("");

    try {
      const response = await fetch(`${getApiBaseUrl()}/api/rcp/section-47`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          selected_drugs: selectedDrugs,
          selected_sources: selectedSources
        })
      });

      if (!response.ok) {
        throw new Error("Errore durante il recupero della sezione 4.7.");
      }

      const data = await response.json();

      setDrivingSections(data.results || []);
      setAcceptedDrivingSectionIds([]);
      setExcludedDrivingSectionIds([]);
      setDrivingSectionStatus(data.message || "Estrazione completata.");
    } catch (error) {
      setDrivingSectionStatus("Errore durante il recupero della sezione 4.7.");
    } finally {
      setDrivingSectionLoading(false);
    }
  };

  const prepareReportPayload = () => {
    const acceptedFoodInteractions = foodInteractions.filter((interaction) =>
      acceptedFoodInteractionIds.includes(interaction.id)
    );

    const acceptedDrugInteractions = drugInteractions.filter((interaction) =>
      acceptedDrugInteractionIds.includes(interaction.id)
    );

    const acceptedDrivingSections = drivingSections.filter((section, index) =>
      acceptedDrivingSectionIds.includes(section.aic_code || index)
    );

    const payload = {
      generated_at: new Date().toISOString(),
      patient: {
        identifier: patientIdentifier,
        year_of_birth: patientYearOfBirth
      },
      clinician: {
        name: clinicianName,
        role: clinicianRole
      },
      consent: {
        information: consentInformation,
        data_use: consentDataUse,
        report_generation: consentReportGeneration,
        copy_received: consentCopyReceived,
        complete: consentComplete
      },
      clinical_notes: clinicalNotes,
      selected_sources: selectedSources,
      selected_drugs: selectedDrugs,
      accepted_food_interactions: acceptedFoodInteractions,
      accepted_drug_interactions: acceptedDrugInteractions,
      accepted_driving_sections: acceptedDrivingSections
    };

    setReportPayload(payload);
    setReportStatus("Dati report preparati. Il PDF userà solo gli elementi accettati dal medico.");
  };

  const downloadReportPdf = async (reportType: "patient" | "clinician") => {
    if (!reportPayload) {
      setReportStatus("Prepara prima i dati del report.");
      return;
    }

    if (!consentComplete) {
      setReportStatus("Consenso non completo. Il PDF non dovrebbe essere generato.");
      return;
    }

    const endpoint = reportType === "patient"
      ? "/api/reports/pdf/patient"
      : "/api/reports/pdf/clinician";

    const filename = reportType === "patient"
      ? "enia_interaction_check_copia_paziente.pdf"
      : "enia_interaction_check_copia_medico.pdf";

    setPdfLoading(reportType);

    try {
      const response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(reportPayload)
      });

      if (!response.ok) {
        throw new Error("Errore durante la generazione del PDF.");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const link = document.createElement("a");
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();

      window.URL.revokeObjectURL(url);

      setReportStatus("PDF generato correttamente.");
    } catch (error) {
      setReportStatus("Errore durante la generazione del PDF.");
    } finally {
      setPdfLoading("");
    }
  };

  return (
    <main className="container">
      <div className="card">
          <div className="logo">Verifica Interazioni Farmaci e Alimenti</div>

          <p className="subtitle">
            <strong>Prototipo V1.</strong> Strumento prototipale per supportare la verifica informativa di possibili interazioni alimentari, interazioni con altri farmaci ed effetti su guida e uso di macchinari secondo la sezione 4.7 del RCP, usando fonti tracciabili e contenuti selezionati dal medico prima della generazione del report.
          </p>

          <p className="small">
            Passaggi: seleziona le fonti dati, cerca e aggiungi i farmaci del paziente, verifica le possibili interazioni e la sezione 4.7 del RCP, accetta o escludi gli elementi da includere, registra il consenso e genera la copia paziente e la copia medico.
          </p>


        <div className="section">
          <h2>Flusso medico</h2>
          <p className="small">
            Qui costruiremo il flusso per paziente, consenso, verifica e report.
          </p>

          <div className="notice">
            Farmaci selezionati per il report: {selectedDrugs.length}
          </div>

          {selectedDrugs.length > 0 && (
            <div className="selected-box">
              <h3>Farmaci aggiunti al report</h3>

              {selectedDrugs.map((drug) => (
                <div key={drug.id} className="selected-drug">
                  <strong>{drug.commercial_name}</strong>
                  <span>AIC: {drug.aic_code || "Non disponibile"}</span>
                  <span>Principio attivo: {drug.active_ingredient || "Non disponibile"}</span>
                  <span>Fonte: {drug.source}</span>

                  <button
                    className="button danger"
                    onClick={() => removeDrugFromReport(drug.id)}
                  >
                    Rimuovi dal report
                  </button>
                </div>
              ))}
            </div>
          )}

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

            <label className="check-row">
              <input
                type="checkbox"
                checked={consentReportGeneration}
                onChange={(event) => setConsentReportGeneration(event.target.checked)}
              />
              <span>
                Il paziente acconsente alla generazione di un report paziente e di un report medico.
              </span>
            </label>

            <label className="check-row">
              <input
                type="checkbox"
                checked={consentCopyReceived}
                onChange={(event) => setConsentCopyReceived(event.target.checked)}
              />
              <span>
                Il paziente dichiara di ricevere o poter ricevere copia del report informativo.
              </span>
            </label>

            <div className={consentComplete ? "status" : "warning"}>
              {consentComplete
                ? "Consenso completo. Il report può essere preparato."
                : "Consenso non completo. Il report non dovrebbe essere generato."}
            </div>
          </div>
        </div>

        <div className="section">
          <h2>Alimenti e integratori</h2>

          <p className="small">
            Inserisci alimenti, bevande o integratori da includere nella verifica.
            Per ora li aggiungiamo manualmente, senza generare interpretazioni cliniche.
          </p>

          <label className="field">
            <span>Alimento, bevanda o integratore</span>
            <input
              className="input"
              value={foodSupplementInput}
              onChange={(event) => setFoodSupplementInput(event.target.value)}
              placeholder="Es. pompelmo, alcol, magnesio, iperico"
            />
          </label>
        </div>

        <div className="section">
          <h2>Interazioni alimentari suggerite</h2>

          <p className="small">
            Il sistema proporrà automaticamente le interazioni alimentari trovate nelle fonti selezionate, in base ai farmaci aggiunti al report.
          </p>

          {selectedDrugs.length === 0 ? (
            <div className="warning">
              Seleziona almeno un farmaco per cercare interazioni alimentari nelle fonti configurate.
            </div>
          ) : (
            <div className="notice">
              Farmaci selezionati: {selectedDrugs.length}. Nessuna interazione alimentare strutturata disponibile nelle fonti configurate.
            </div>
          )}

          <button
            className="button"
            onClick={checkSuggestedFoodInteractions}
            disabled={foodInteractionLoading || selectedDrugs.length === 0}
          >
            {foodInteractionLoading ? "Verifica in corso..." : "Cerca interazioni alimentari suggerite"}
          </button>

          {foodInteractionStatus && (
            <div className="notice">
              {foodInteractionStatus}
            </div>
          )}

          {rcpSourcesChecked.length > 0 && (
            <div className="selected-box">
              <h3>Fonti RCP/FI controllate</h3>

              {rcpSourcesChecked.map((source, index) => (
                <div key={index} className="source-check-card">
                  <strong>{source.commercial_name || "Farmaco selezionato"}</strong>

                  <p>
                    Principio attivo: {source.active_ingredient || "non disponibile"}
                  </p>

                  <p>
                    AIC: {source.aic_code || "non disponibile"}
                  </p>

                  <div className="badges">
                    <span className="badge blue">
                      {source.source_name}
                    </span>

                    <span className={source.status === "source_available" ? "badge green" : "badge red"}>
                      {source.status === "source_available" ? "Fonte disponibile" : "Fonte non disponibile"}
                    </span>

                    {source.extraction_status && (
                      <span className="badge">
                        Estrazione: {source.extraction_status}
                      </span>
                    )}

                    {typeof source.candidate_count === "number" && (
                      <span className="badge green">
                        Candidati: {source.candidate_count}
                      </span>
                    )}

                    {typeof source.unclassified_sentence_count === "number" && (
                      <span className="badge">
                        Da revisionare: {source.unclassified_sentence_count}
                      </span>
                    )}
                  </div>

                  <div className="source-links">
                    {source.rcp_url && (
                      <a href={source.rcp_url} target="_blank" rel="noreferrer">
                        Apri RCP
                      </a>
                    )}

                    {source.leaflet_url && (
                      <a href={source.leaflet_url} target="_blank" rel="noreferrer">
                        Apri Foglio illustrativo
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {foodInteractions.length > 0 && (
            <div className="selected-box">
              <h3>Interazioni alimentari trovate</h3>

              {foodInteractions.map((interaction) => (
                <div key={interaction.id} className="food-interaction-card">
                  <strong>
                    {interaction.active_ingredient} + {interaction.food_or_substance}
                  </strong>

                  <p>{interaction.interaction_summary}</p>

                  <div className="badges">
                    <span className="badge blue">
                      Fonte: {interaction.source_name}
                    </span>

                    {interaction.source_section && (
                      <span className="badge">
                        Sezione: {interaction.source_section}
                      </span>
                    )}

                    {interaction.validation_status && (
                      <span className="badge green">
                        {interaction.validation_status}
                      </span>
                    )}
                  </div>

                  {interaction.recommendation && (
                    <p>
                      <strong>Raccomandazione:</strong> {interaction.recommendation}
                    </p>
                  )}

                  <div className="review-actions">
                    <button
                      type="button"
                      className={acceptedFoodInteractionIds.includes(interaction.id) ? "secondary-button active" : "secondary-button"}
                      onClick={() => {
                        setAcceptedFoodInteractionIds((current) =>
                          current.includes(interaction.id)
                            ? current
                            : [...current, interaction.id]
                        );

                        setExcludedFoodInteractionIds((current) =>
                          current.filter((id) => id !== interaction.id)
                        );
                      }}
                    >
                      Accetta nel report
                    </button>

                    <button
                      type="button"
                      className={excludedFoodInteractionIds.includes(interaction.id) ? "danger-button active" : "danger-button"}
                      onClick={() => {
                        setExcludedFoodInteractionIds((current) =>
                          current.includes(interaction.id)
                            ? current
                            : [...current, interaction.id]
                        );

                        setAcceptedFoodInteractionIds((current) =>
                          current.filter((id) => id !== interaction.id)
                        );
                      }}
                    >
                      Escludi dal report
                    </button>
                  </div>

                  <p className="review-status">
                    Stato revisione: {
                      acceptedFoodInteractionIds.includes(interaction.id)
                        ? "accettata nel report"
                        : excludedFoodInteractionIds.includes(interaction.id)
                          ? "esclusa dal report"
                          : "da valutare"
                    }
                  </p>
                </div>
              ))}
            </div>
          )}

          <div className="section-card">
            <h2>Interazioni con altri farmaci</h2>

            <p>
              Il sistema legge la sezione 4.5 del RCP AIFA e mostra i candidati documentali relativi a interazioni con altri medicinali o classi di medicinali.
            </p>

            {selectedDrugs.length === 0 && (
              <div className="warning-box">
                Seleziona almeno un farmaco per cercare interazioni con altri farmaci.
              </div>
            )}

            <button
              type="button"
              className="primary-button"
              onClick={checkSuggestedDrugInteractions}
              disabled={selectedDrugs.length === 0 || drugInteractionLoading}
            >
              {drugInteractionLoading ? "Verifica in corso..." : "Cerca interazioni con altri farmaci"}
            </button>

            {drugInteractionStatus && (
              <div className="notice">
                {drugInteractionStatus}
              </div>
            )}

            {drugRcpSourcesChecked.length > 0 && (
              <div className="selected-box">
                <h3>Fonti RCP/FI controllate per interazioni farmaco farmaco</h3>

                {drugRcpSourcesChecked.map((source, index) => (
                  <div key={index} className="source-check-card">
                    <strong>{source.commercial_name || "Farmaco selezionato"}</strong>

                    <p>
                      Principio attivo: {source.active_ingredient || "non disponibile"}
                    </p>

                    <p>
                      AIC: {source.aic_code || "non disponibile"}
                    </p>

                    <div className="badges">
                      <span className="badge blue">
                        {source.source_name}
                      </span>

                      <span className={source.status === "source_available" ? "badge green" : "badge red"}>
                        {source.status === "source_available" ? "Fonte disponibile" : "Fonte non disponibile"}
                      </span>

                      {source.extraction_status && (
                        <span className="badge">
                          Estrazione: {source.extraction_status}
                        </span>
                      )}

                      {typeof source.candidate_count === "number" && (
                        <span className="badge green">
                          Candidati: {source.candidate_count}
                        </span>
                      )}
                    </div>

                    <div className="source-links">
                      {source.rcp_url && (
                        <a href={source.rcp_url} target="_blank" rel="noreferrer">
                          Apri RCP
                        </a>
                      )}

                      {source.leaflet_url && (
                        <a href={source.leaflet_url} target="_blank" rel="noreferrer">
                          Apri Foglio illustrativo
                        </a>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {drugInteractions.length > 0 && (
              <div className="selected-box">
                <h3>Interazioni con altri farmaci trovate</h3>

                {drugInteractions.map((interaction) => (
                  <div key={interaction.id} className="drug-interaction-card">
                    <strong>
                      {interaction.active_ingredient} + {interaction.interacting_drug_or_class}
                    </strong>

                    <p>{interaction.interaction_summary}</p>

                    <div className="badges">
                      <span className="badge blue">
                        Fonte: {interaction.source_name}
                      </span>

                      {interaction.source_section && (
                        <span className="badge">
                          Sezione: {interaction.source_section}
                        </span>
                      )}

                      {interaction.recognition_status && (
                        <span className="badge">
                          {interaction.recognition_status}
                        </span>
                      )}

                      {interaction.validation_status && (
                        <span className="badge green">
                          {interaction.validation_status}
                        </span>
                      )}
                    </div>

                    {interaction.recommendation && (
                      <p>
                        <strong>Raccomandazione:</strong> {interaction.recommendation}
                      </p>
                    )}

                    <div className="review-actions">
                      <button
                        type="button"
                        className={acceptedDrugInteractionIds.includes(interaction.id) ? "secondary-button active" : "secondary-button"}
                        onClick={() => {
                          setAcceptedDrugInteractionIds((current) =>
                            current.includes(interaction.id)
                              ? current
                              : [...current, interaction.id]
                          );

                          setExcludedDrugInteractionIds((current) =>
                            current.filter((id) => id !== interaction.id)
                          );
                        }}
                      >
                        Accetta nel report
                      </button>

                      <button
                        type="button"
                        className={excludedDrugInteractionIds.includes(interaction.id) ? "danger-button active" : "danger-button"}
                        onClick={() => {
                          setExcludedDrugInteractionIds((current) =>
                            current.includes(interaction.id)
                              ? current
                              : [...current, interaction.id]
                          );

                          setAcceptedDrugInteractionIds((current) =>
                            current.filter((id) => id !== interaction.id)
                          );
                        }}
                      >
                        Escludi dal report
                      </button>
                    </div>

                    <p className="review-status">
                      Stato revisione: {
                        acceptedDrugInteractionIds.includes(interaction.id)
                          ? "accettata nel report"
                          : excludedDrugInteractionIds.includes(interaction.id)
                            ? "esclusa dal report"
                            : "da valutare"
                      }
                    </p>
                  </div>
                ))}
              </div>
            )}

            {drugInteractions.filter((interaction) => acceptedDrugInteractionIds.includes(interaction.id)).length > 0 && (
              <div className="selected-box report-summary-box">
                <h3>Interazioni farmacologiche accettate per il report</h3>

                <p>
                  Queste sono le sole interazioni con altri farmaci che entreranno nella copia paziente e nella copia medico.
                </p>

                {drugInteractions
                  .filter((interaction) => acceptedDrugInteractionIds.includes(interaction.id))
                  .map((interaction) => (
                    <div key={interaction.id} className="accepted-interaction-card">
                      <strong>
                        {interaction.active_ingredient} + {interaction.interacting_drug_or_class}
                      </strong>

                      <p>{interaction.interaction_summary}</p>

                      <div className="badges">
                        <span className="badge blue">
                          Fonte: {interaction.source_name}
                        </span>

                        {interaction.source_section && (
                          <span className="badge">
                            Sezione: {interaction.source_section}
                          </span>
                        )}

                        <span className="badge green">
                          Accettata dal medico
                        </span>
                      </div>
                    </div>
                  ))}
              </div>
            )}
          </div>

          <div className="section-card">
            <h2>Effetti su guida e uso di macchinari</h2>

            <p>
              Il sistema estrae letteralmente la sezione 4.7 del RCP AIFA per ogni farmaco selezionato, senza interpretazione automatica.
            </p>

            {selectedDrugs.length === 0 && (
              <div className="warning-box">
                Seleziona almeno un farmaco per recuperare la sezione 4.7.
              </div>
            )}

            <button
              type="button"
              className="primary-button"
              onClick={checkDrivingSection}
              disabled={selectedDrugs.length === 0 || drivingSectionLoading}
            >
              {drivingSectionLoading ? "Estrazione in corso..." : "Estrai sezione 4.7 guida e macchinari"}
            </button>

            {drivingSectionStatus && (
              <div className="notice">
                {drivingSectionStatus}
              </div>
            )}

            {drivingSections.length > 0 && (
              <div className="selected-box">
                <h3>Sezione 4.7 estratta da RCP AIFA</h3>

                {drivingSections.map((section, index) => (
                  <div key={index} className="driving-section-card">
                    <strong>{section.commercial_name || "Farmaco selezionato"}</strong>

                    <p>
                      Principio attivo: {section.active_ingredient || "non disponibile"}
                    </p>

                    <p>
                      AIC: {section.aic_code || "non disponibile"}
                    </p>

                    <div className="badges">
                      <span className="badge blue">
                        Fonte: {section.source_name}
                      </span>

                      <span className={section.section_found ? "badge green" : "badge red"}>
                        {section.section_found ? "Sezione 4.7 trovata" : "Sezione 4.7 non trovata"}
                      </span>

                      {section.extraction_status && (
                        <span className="badge">
                          Estrazione: {section.extraction_status}
                        </span>
                      )}

                      {typeof section.character_count === "number" && (
                        <span className="badge">
                          Caratteri: {section.character_count}
                        </span>
                      )}
                    </div>

                    <div className="source-links">
                      {section.rcp_url && (
                        <a href={section.rcp_url} target="_blank" rel="noreferrer">
                          Apri RCP
                        </a>
                      )}

                      {section.leaflet_url && (
                        <a href={section.leaflet_url} target="_blank" rel="noreferrer">
                          Apri Foglio illustrativo
                        </a>
                      )}
                    </div>

                    {section.section_text ? (
                      <div className="literal-section-text">
                        {section.section_text}
                      </div>
                    ) : (
                      <p className="review-status">
                        Nessun testo 4.7 disponibile per questo farmaco.
                      </p>
                    )}

                    <div className="review-actions">
                      <button
                        type="button"
                        className={acceptedDrivingSectionIds.includes(section.aic_code || index) ? "secondary-button active" : "secondary-button"}
                        onClick={() => {
                          const sectionId = section.aic_code || index;

                          setAcceptedDrivingSectionIds((current) =>
                            current.includes(sectionId)
                              ? current
                              : [...current, sectionId]
                          );

                          setExcludedDrivingSectionIds((current) =>
                            current.filter((id) => id !== sectionId)
                          );
                        }}
                        disabled={!section.section_text}
                      >
                        Accetta nel report
                      </button>

                      <button
                        type="button"
                        className={excludedDrivingSectionIds.includes(section.aic_code || index) ? "danger-button active" : "danger-button"}
                        onClick={() => {
                          const sectionId = section.aic_code || index;

                          setExcludedDrivingSectionIds((current) =>
                            current.includes(sectionId)
                              ? current
                              : [...current, sectionId]
                          );

                          setAcceptedDrivingSectionIds((current) =>
                            current.filter((id) => id !== sectionId)
                          );
                        }}
                      >
                        Escludi dal report
                      </button>
                    </div>

                    <p className="review-status">
                      Stato revisione: {
                        acceptedDrivingSectionIds.includes(section.aic_code || index)
                          ? "accettata nel report"
                          : excludedDrivingSectionIds.includes(section.aic_code || index)
                            ? "esclusa dal report"
                            : "da valutare"
                      }
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          {drivingSections.filter((section, index) => acceptedDrivingSectionIds.includes(section.aic_code || index)).length > 0 && (
            <div className="selected-box report-summary-box">
              <h3>Sezioni 4.7 guida e macchinari accettate per il report</h3>

              <p>
                Questi sono i soli testi della sezione 4.7 che entreranno nella copia paziente e nella copia medico.
              </p>

              {drivingSections
                .filter((section, index) => acceptedDrivingSectionIds.includes(section.aic_code || index))
                .map((section, index) => (
                  <div key={section.aic_code || index} className="accepted-interaction-card">
                    <strong>
                      {section.commercial_name || "Farmaco selezionato"}
                    </strong>

                    <p>
                      Principio attivo: {section.active_ingredient || "non disponibile"}
                    </p>

                    <div className="badges">
                      <span className="badge blue">
                        Fonte: {section.source_name}
                      </span>

                      <span className="badge">
                        {section.source_section}
                      </span>

                      <span className="badge green">
                        Accettata dal medico
                      </span>
                    </div>

                    <div className="literal-section-text">
                      {section.section_text}
                    </div>
                  </div>
                ))}
            </div>
          )}

          {foodInteractions.filter((interaction) => acceptedFoodInteractionIds.includes(interaction.id)).length > 0 && (
            <div className="selected-box report-summary-box">
              <h3>Interazioni alimentari, alcol e integratori accettate per il report</h3>

              <p>
                Queste sono le sole interazioni alimentari, con alcol o integratori che entreranno nella copia paziente e nella copia medico.
              </p>

              {foodInteractions
                .filter((interaction) => acceptedFoodInteractionIds.includes(interaction.id))
                .map((interaction) => (
                  <div key={interaction.id} className="accepted-interaction-card">
                    <strong>
                      {interaction.active_ingredient} + {interaction.food_or_substance}
                    </strong>

                    <p>{interaction.interaction_summary}</p>

                    <div className="badges">
                      <span className="badge blue">
                        Fonte: {interaction.source_name}
                      </span>

                      {interaction.source_section && (
                        <span className="badge">
                          Sezione: {interaction.source_section}
                        </span>
                      )}

                      <span className="badge green">
                        Accettata dal medico
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          )}

          <p className="small">
            Ogni interazione alimentare trovata potrà essere aggiunta o rimossa dal report finale, con fonte evidenziata.
          </p>
        </div>

        <div className="section">
          
            <div className="selected-box">
              <h2>Preparazione report</h2>

              <button
                type="button"
                className="primary-button"
                onClick={prepareReportPayload}
                disabled={selectedDrugs.length === 0}
              >
                Prepara dati report
              </button>

              {reportStatus && (
                <div className="notice">
                  {reportStatus}
                </div>
              )}

              {reportPayload && (
                <div>
                  <p>Farmaci selezionati: {reportPayload.selected_drugs.length}</p>
                  <p>Interazioni alimentari accettate: {reportPayload.accepted_food_interactions.length}</p>
                  <p>Interazioni farmacologiche accettate: {reportPayload.accepted_drug_interactions.length}</p>
                  <p>Sezioni 4.7 accettate: {reportPayload.accepted_driving_sections.length}</p>

                  <div className="report-actions">
                    <button
                      type="button"
                      className="primary-button"
                      onClick={() => downloadReportPdf("patient")}
                      disabled={!reportPayload.consent.complete || pdfLoading !== ""}
                    >
                      {pdfLoading === "patient" ? "Genero PDF..." : "Scarica copia paziente"}
                    </button>

                    <button
                      type="button"
                      className="primary-button"
                      onClick={() => downloadReportPdf("clinician")}
                      disabled={!reportPayload.consent.complete || pdfLoading !== ""}
                    >
                      {pdfLoading === "clinician" ? "Genero PDF..." : "Scarica copia medico"}
                    </button>
                  </div>
                </div>
              )}
            </div>

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

                <button
                  className="button secondary"
                  onClick={() => addDrugToReport(drug)}
                >
                  Aggiungi al report
                </button>

                <p className="small">
                  Dato recuperato da {drug.source}. Import database:{" "}
                  {drug.source_updated_at}
                </p>
              </div>
            ))}
          </div>
        </div>
        <details className="section">
          <summary>Stato sistema</summary>
          <div className="status">{apiStatus}</div>
          <p className="small">
            Frontend e backend sono collegati. I moduli useranno solo fonti
            selezionate e tracciabili.
          </p>
        </details>

      </div>
    </main>
  );
}
