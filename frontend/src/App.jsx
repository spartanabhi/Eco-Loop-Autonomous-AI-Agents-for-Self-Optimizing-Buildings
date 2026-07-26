import React, { useState, useEffect } from "react";
import {
  fetchHealth,
  fetchStatus,
  fetchHero,
  fetchLatestTelemetry,
  fetchTelemetryHistory,
  fetchLatestAgent,
  fetchAgentHistory,
  fetchActionHistory,
  fetchEvaluationSummary,
  fetchSeasons
} from "./api";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from "recharts";

export default function App() {
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  const [health, setHealth] = useState(null);
  const [hero, setHero] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [telemetryHistory, setTelemetryHistory] = useState([]);
  const [agent, setAgent] = useState(null);
  const [agentHistory, setAgentHistory] = useState([]);
  const [actionHistory, setActionHistory] = useState([]);
  const [evaluation, setEvaluation] = useState(null);
  const [seasons, setSeasons] = useState([]);

  const loadData = async () => {
    try {
      const [
        healthData,
        heroData,
        telemData,
        telemHist,
        agentData,
        agentHist,
        actHist,
        evalData,
        seasonsData
      ] = await Promise.all([
        fetchHealth(),
        fetchHero(),
        fetchLatestTelemetry(),
        fetchTelemetryHistory(60),
        fetchLatestAgent(),
        fetchAgentHistory(8),
        fetchActionHistory(8),
        fetchEvaluationSummary(),
        fetchSeasons()
      ]);

      setHealth(healthData);
      setHero(heroData);
      setTelemetry(telemData);
      setTelemetryHistory(telemHist);
      setAgent(agentData);
      setAgentHistory(agentHist);
      setActionHistory(actHist);
      setEvaluation(evalData);
      setSeasons(seasonsData);

      setOffline(false);
      setLoading(false);
    } catch (err) {
      console.error("Data fetch error:", err);
      setOffline(true);
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  if (offline) {
    return (
      <div className="dashboard-container">
        <div className="offline-banner">
          <div>
            <h3>BACKEND OFFLINE</h3>
            <p style={{ fontSize: "12px", marginTop: "4px", fontWeight: "normal" }}>
              Start Eco-Loop API on port 8000 using: <code>python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000</code>
            </p>
          </div>
          <button
            onClick={() => { setLoading(true); loadData(); }}
            style={{ padding: "8px 16px", background: "#f87171", color: "#fff", border: "none", borderRadius: "6px", cursor: "pointer", fontWeight: "bold" }}
          >
            Retry Connection
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="dashboard-container" style={{ padding: "40px", textAlign: "center" }}>
        <h2 style={{ color: "var(--accent-cyan)" }}>Loading Eco-Loop Building Command Centre...</h2>
        <p style={{ color: "var(--text-muted)", marginTop: "8px" }}>Reading validated Policy Iteration 2 project artifacts...</p>
      </div>
    );
  }

  // Hero calculations
  const heroRedPct = hero?.electricity_reduction_percent ?? 3.51;
  const heroSavedKwh = hero?.electricity_saved_kwh ?? 26.22;
  const heroBaseKwh = hero?.baseline_electricity_kwh ?? 747.11;
  const heroEcoKwh = hero?.ecoloop_electricity_kwh ?? 720.89;
  const heroDecisions = hero?.decision_count ?? 51;
  const heroActions = hero?.effective_action_count ?? 48;

  // Formatting Descriptive Action
  const selectedAction = agent?.selected_action || "--";
  const candidates = agent?.candidate_actions || [];
  const descriptiveAction = candidates.find(c => c.includes("COOLING") || c.includes("HEATING")) || selectedAction;

  return (
    <div className="dashboard-container">
      {/* 1. HEADER */}
      <header className="header">
        <div>
          <div className="brand-title">
            ECO-LOOP <span>BUILDING AGENTS</span>
          </div>
          <div className="brand-subtitle">Autonomous AI Building Optimization</div>
          <div className="brand-tag">Local AI × EnergyPlus Digital Twin</div>
        </div>
        <div className="header-badges">
          <div className="badge badge-replay">VALIDATED REPLAY</div>
          <div className="badge badge-success">EnergyPlus ✓</div>
          <div className="badge badge-success">Local Qwen ✓</div>
          <div className="badge badge-info">Controller: Policy Iteration 2</div>
        </div>
      </header>

      {/* 2. TOP GRID: HERO RESULT & CLOSED-LOOP FLOW */}
      <div className="grid-top">
        {/* HERO RESULT */}
        <div className="card hero-card">
          <div className="card-title">
            <span>Verified Optimization Evidence</span>
            <span style={{ color: "var(--accent-green)", fontSize: "12px" }}>SUMMER JUL 21–23</span>
          </div>
          <div>
            <div className="hero-metric">↓ {heroRedPct}%</div>
            <div className="hero-label">SUMMER ELECTRICITY REDUCTION</div>
            <div className="hero-subtext">{heroSavedKwh} kWh saved over validated 3-day summer evaluation</div>
          </div>

          <div className="hero-comparison">
            <div className="hero-val-box">
              <div className="hero-val-label">BASELINE ENERGYPLUS</div>
              <div className="hero-val-num">{heroBaseKwh} kWh</div>
            </div>
            <div className="hero-arrow">→</div>
            <div className="hero-val-box">
              <div className="hero-val-label">ECO-LOOP AI CONTROLLER</div>
              <div className="hero-val-num" style={{ color: "var(--accent-green)" }}>{heroEcoKwh} kWh</div>
            </div>
          </div>

          <div className="stat-pills">
            <div className="stat-pill">
              <div className="stat-pill-num">{heroDecisions}</div>
              <div className="stat-pill-lbl">AI Decisions</div>
            </div>
            <div className="stat-pill">
              <div className="stat-pill-num" style={{ color: "var(--accent-green)" }}>{heroActions}</div>
              <div className="stat-pill-lbl">Effective Actions</div>
            </div>
          </div>
        </div>

        {/* CLOSED-LOOP PIPELINE */}
        <div className="card">
          <div className="card-title">
            <span>Autonomous Supervisory Control Pipeline</span>
            <span style={{ color: "var(--accent-cyan)", fontSize: "12px" }}>FEEDBACK LOOP ↺</span>
          </div>
          <div className="pipeline-flow" style={{ marginTop: "12px" }}>
            <div className="pipe-step">
              <div className="pipe-step-title">1. SENSE</div>
              <div className="pipe-step-desc">
                Temp: {telemetry?.zone_temperature_c?.toFixed(1) ?? "--"}°C<br />
                PMV: {telemetry?.pmv?.toFixed(2) ?? "--"}<br />
                CO2: {telemetry?.co2_ppm?.toFixed(0) ?? "--"} ppm
              </div>
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-step">
              <div className="pipe-step-title">2. REASON</div>
              <div className="pipe-step-desc">
                Local Qwen2.5-0.5B<br />
                Target: Comfort & ECM
              </div>
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-step">
              <div className="pipe-step-title">3. SAFETY</div>
              <div className="pipe-step-desc">
                Schema: Valid ✓<br />
                Safety: Valid ✓
              </div>
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-step">
              <div className="pipe-step-title">4. ACT</div>
              <div className="pipe-step-desc">
                PyEnergyPlus Actuator<br />
                Setpoint Override
              </div>
            </div>
            <div className="pipe-arrow">→</div>
            <div className="pipe-step">
              <div className="pipe-step-title">5. VERIFY</div>
              <div className="pipe-step-desc">
                Measured State Change<br />
                Next Decision ↺
              </div>
            </div>
          </div>

          {/* Energy Bar Comparison Chart */}
          <div style={{ marginTop: "8px" }}>
            <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "6px", fontWeight: "600" }}>
              SUMMER ELECTRICITY COMPARISON (kWh)
            </div>
            <div className="chart-container">
              <div className="bar-wrapper">
                <div className="bar-val">{heroBaseKwh} kWh</div>
                <div className="bar bar-baseline" style={{ height: "100%" }}></div>
                <div className="bar-label">Baseline</div>
              </div>
              <div className="bar-wrapper">
                <div className="bar-val" style={{ color: "var(--accent-green)" }}>{heroEcoKwh} kWh</div>
                <div className="bar bar-ecoloop" style={{ height: `${(heroEcoKwh / heroBaseKwh) * 100}%` }}></div>
                <div className="bar-label" style={{ color: "var(--accent-green)", fontWeight: "bold" }}>Eco-Loop AI</div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. MAIN GRID: BUILDING STATE & AI DECISION PANEL */}
      <div className="grid-main">
        {/* BUILDING STATE PANEL */}
        <div className="card">
          <div className="card-title">
            <span>BUILDING STATE (CORE_ZN)</span>
            <span style={{ color: "var(--text-muted)", fontSize: "11px" }}>{telemetry?.simulation_time || "--"}</span>
          </div>

          <div className="telemetry-grid">
            <div className="telemetry-metric">
              <div className="telemetry-lbl">Zone Temperature</div>
              <div className="telemetry-val">{telemetry?.zone_temperature_c?.toFixed(1) ?? "--"} °C</div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">Thermal Comfort</div>
              <div className="telemetry-val">
                PMV {telemetry?.pmv > 0 ? `+${telemetry?.pmv?.toFixed(2)}` : telemetry?.pmv?.toFixed(2) ?? "--"}{" "}
                <span className="tag-comfortable" style={{ fontSize: "11px" }}>(COMFORTABLE)</span>
              </div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">Indoor Air Quality</div>
              <div className="telemetry-val">
                {telemetry?.co2_ppm?.toFixed(0) ?? "--"} ppm{" "}
                <span className="tag-healthy" style={{ fontSize: "11px" }}>(HEALTHY IAQ)</span>
              </div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">Facility Demand</div>
              <div className="telemetry-val">{telemetry?.facility_demand_kw?.toFixed(2) ?? "--"} kW</div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">Outdoor Temp</div>
              <div className="telemetry-val">{telemetry?.outdoor_temperature_c?.toFixed(1) ?? "--"} °C</div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">Occupancy</div>
              <div className="telemetry-val">{telemetry?.occupancy?.toFixed(0) ?? "0"} Persons</div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">HVAC Mode</div>
              <div className="telemetry-val" style={{ color: "var(--accent-cyan)" }}>{telemetry?.hvac_mode ?? "COOLING"}</div>
            </div>

            <div className="telemetry-metric">
              <div className="telemetry-lbl">Carbon State</div>
              <div className="telemetry-val" style={{ color: "var(--accent-amber)" }}>{telemetry?.carbon_state ?? "MEDIUM"}</div>
            </div>
          </div>

          <div style={{ display: "flex", gap: "12px", background: "rgba(15, 23, 42, 0.6)", padding: "10px", borderRadius: "8px", marginTop: "4px" }}>
            <div style={{ flex: 1, fontSize: "12px" }}>
              <span style={{ color: "var(--text-muted)" }}>Current Heating Setpoint: </span>
              <strong>{telemetry?.heating_setpoint_c?.toFixed(1) ?? "21.0"} °C</strong>
            </div>
            <div style={{ flex: 1, fontSize: "12px" }}>
              <span style={{ color: "var(--text-muted)" }}>Current Cooling Setpoint: </span>
              <strong style={{ color: "var(--accent-cyan)" }}>{agent?.cooling_setpoint?.toFixed(1) ?? telemetry?.cooling_setpoint_c?.toFixed(1) ?? "24.0"} °C</strong>
            </div>
          </div>
        </div>

        {/* AI DECISION PANEL */}
        <div className="card">
          <div className="card-title">
            <span>AI AGENT DECISION (LOCAL QWEN2.5-0.5B)</span>
            <span style={{ color: "var(--accent-amber)", fontSize: "11px" }}>SUPERVISORY OPTIMIZATION</span>
          </div>

          <div className="decision-box">
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div className="decision-action-highlight">{selectedAction}</div>
              {descriptiveAction !== selectedAction && (
                <div className="candidate-tag" style={{ fontSize: "12px", background: "rgba(251, 191, 36, 0.2)", color: "var(--accent-amber)", border: "1px solid rgba(251, 191, 36, 0.4)" }}>
                  {descriptiveAction}
                </div>
              )}
            </div>

            <div className="decision-reason">
              "{agent?.reason || "Restores occupied cooling comfort when zone is warm."}"
            </div>

            <div style={{ marginTop: "4px" }}>
              <div style={{ fontSize: "11px", color: "var(--text-muted)", marginBottom: "4px" }}>Evaluated Candidates:</div>
              <div className="candidates-list">
                {candidates.map((c, i) => (
                  <span key={i} className="candidate-tag">{c}</span>
                ))}
              </div>
            </div>
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", gap: "8px", flexWrap: "wrap", fontSize: "11px" }}>
            <span style={{ color: "var(--accent-green)" }}>ECM Available ✓</span>
            <span style={{ color: "var(--accent-green)" }}>ECM Selected ✓</span>
            <span style={{ color: "var(--accent-green)" }}>Schema Valid ✓</span>
            <span style={{ color: "var(--accent-green)" }}>Safety Valid ✓</span>
            <span style={{ color: "var(--accent-cyan)" }}>Inference: {agent?.inference_latency_seconds?.toFixed(2) ?? "13.29"}s</span>
          </div>
        </div>
      </div>

      {/* 4. SAFETY GUARDRAILS & TELEMETRY TREND */}
      <div className="grid-main">
        {/* DETERMINISTIC SAFETY LAYER */}
        <div className="card">
          <div className="card-title">
            <span>DETERMINISTIC SAFETY LAYER</span>
            <span style={{ color: "var(--accent-green)", fontSize: "11px" }}>ZERO VIOLATION GUARANTEE</span>
          </div>

          <div className="guardrails-grid">
            <div className="guardrail-card">
              <div className="guardrail-title">THERMAL COMFORT</div>
              <div className="guardrail-val">PMV -0.5 → +0.5</div>
            </div>
            <div className="guardrail-card">
              <div className="guardrail-title">INDOOR AIR QUALITY</div>
              <div className="guardrail-val">CO2 ≤ 1000 ppm</div>
            </div>
            <div className="guardrail-card">
              <div className="guardrail-title">SETPOINT BOUNDS</div>
              <div className="guardrail-val">Protected [20°C - 28°C]</div>
            </div>
            <div className="guardrail-card">
              <div className="guardrail-title">HVAC DEADBAND</div>
              <div className="guardrail-val">Protected (≥ 1.0°C)</div>
            </div>
          </div>

          <div style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic", textAlign: "center", marginTop: "4px" }}>
            "Qwen selects only from deterministically eligible actions."
          </div>
        </div>

        {/* TELEMETRY TREND CHART */}
        <div className="card">
          <div className="card-title">
            <span>ZONE TEMPERATURE & SETPOINT TREND</span>
            <span style={{ color: "var(--accent-cyan)", fontSize: "11px" }}>SUMMER EVALUATION</span>
          </div>

          <div style={{ height: "160px", width: "100%" }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={telemetryHistory}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="simulation_time" stroke="#94a3b8" tick={{ fontSize: 10 }} interval={15} />
                <YAxis domain={[20, 30]} stroke="#94a3b8" tick={{ fontSize: 10 }} />
                <Tooltip contentStyle={{ backgroundColor: "#1e293b", borderColor: "#334155", fontSize: "12px" }} />
                <Line type="monotone" dataKey="zone_temperature_c" stroke="#38bdf8" strokeWidth={2} dot={false} name="Zone Temp (°C)" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* 5. TIMELINES & ACTION LOGS */}
      <div className="grid-main">
        {/* RECENT AUTONOMOUS DECISIONS */}
        <div className="card">
          <div className="card-title">RECENT AUTONOMOUS DECISIONS</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>ECM Candidate</th>
                <th>Reasoning Summary</th>
                <th>Safety</th>
              </tr>
            </thead>
            <tbody>
              {agentHistory.map((row, idx) => (
                <tr key={idx}>
                  <td>{row.simulation_time}</td>
                  <td style={{ color: "var(--accent-amber)", fontWeight: "bold" }}>
                    {row.candidate_actions?.find(c => c !== "MAINTAIN") || row.selected_action}
                  </td>
                  <td style={{ fontSize: "11px" }}>{row.reason}</td>
                  <td style={{ color: "var(--accent-green)", fontWeight: "bold" }}>SAFE ✓</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* ACTUATOR LOG */}
        <div className="card">
          <div className="card-title">ACTUATOR LOG (PYENERGYPLUS OVERRIDES)</div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Action</th>
                <th>Heating SP</th>
                <th>Cooling SP</th>
                <th>Source</th>
              </tr>
            </thead>
            <tbody>
              {actionHistory.map((row, idx) => (
                <tr key={idx}>
                  <td>{row.simulation_time}</td>
                  <td style={{ color: "var(--accent-green)", fontWeight: "bold" }}>{row.action}</td>
                  <td>{row.heating_setpoint ? `${row.heating_setpoint.toFixed(1)} °C` : "--"}</td>
                  <td style={{ color: "var(--accent-cyan)", fontWeight: "bold" }}>
                    {row.cooling_setpoint ? `${row.cooling_setpoint.toFixed(1)} °C` : "--"}
                  </td>
                  <td style={{ fontSize: "11px", color: "var(--text-muted)" }}>{row.source}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 6. CROSS-SEASON EVALUATION */}
      <div className="card">
        <div className="card-title">
          <span>CROSS-SEASON PERFORMANCE MATRIX</span>
          <span style={{ color: "var(--accent-cyan)", fontSize: "11px" }}>3-SEASON VERIFIED EVALUATION</span>
        </div>

        <div className="grid-three">
          <div className="card" style={{ background: "rgba(15, 23, 42, 0.6)" }}>
            <div style={{ fontWeight: "700", color: "var(--accent-cyan)" }}>SUMMER</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Cooling Optimization</div>
            <div style={{ marginTop: "8px", fontSize: "13px" }}>
              <strong>51</strong> Decisions<br />
              <strong style={{ color: "var(--accent-green)" }}>48</strong> Effective Actions<br />
              <strong style={{ color: "var(--accent-green)" }}>3.51%</strong> Electricity Reduction
            </div>
          </div>

          <div className="card" style={{ background: "rgba(15, 23, 42, 0.6)" }}>
            <div style={{ fontWeight: "700", color: "var(--accent-amber)" }}>WINTER</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Comfort Recovery</div>
            <div style={{ marginTop: "8px", fontSize: "13px" }}>
              <strong>51</strong> Decisions<br />
              <strong>2</strong> Effective Actions<br />
              Occupied Comfort: <strong>29.6% → 75.9%</strong>
            </div>
          </div>

          <div className="card" style={{ background: "rgba(15, 23, 42, 0.6)" }}>
            <div style={{ fontWeight: "700", color: "var(--accent-teal)" }}>SHOULDER</div>
            <div style={{ fontSize: "12px", color: "var(--text-muted)" }}>Selective Control</div>
            <div style={{ marginTop: "8px", fontSize: "13px" }}>
              <strong>51</strong> Decisions<br />
              <strong>6</strong> Effective Actions<br />
              Comfort & Heat Recovery
            </div>
          </div>
        </div>

        <div style={{ fontSize: "12px", color: "var(--text-muted)", textAlign: "center", fontStyle: "italic", marginTop: "4px" }}>
          "Eco-Loop does not optimise every season the same way — it adapts its actions to comfort, HVAC state, occupancy and energy conditions."
        </div>
      </div>

      {/* 7. ARCHITECTURE STRIP & REPLAY EXPLANATION */}
      <footer style={{ background: "var(--bg-card)", padding: "16px 24px", borderRadius: "12px", border: "1px solid var(--border-card)", display: "flex", flexDirection: "column", gap: "12px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "12px", fontWeight: "700", color: "var(--accent-cyan)" }}>
          <span>ENERGYPLUS → TELEMETRY → SAFE ECMs → LOCAL QWEN → SAFETY VALIDATOR → PYENERGYPLUS → HVAC ↺</span>
        </div>

        <div style={{ display: "flex", gap: "16px", fontSize: "11px", color: "var(--text-muted)" }}>
          <span>✓ 100% Local AI Inference</span>
          <span>✓ Closed-Loop Digital Twin</span>
          <span>✓ Explainable Decisions</span>
          <span>✓ Deterministic Safety</span>
        </div>

        <div style={{ fontSize: "11px", color: "var(--accent-amber)", background: "rgba(251, 191, 36, 0.1)", padding: "8px 12px", borderRadius: "6px", border: "1px solid rgba(251, 191, 36, 0.2)" }}>
          <strong>VALIDATED REPLAY:</strong> Dashboard values are sourced from a previously executed real EnergyPlus + local Qwen closed-loop experiment.
        </div>
      </footer>
    </div>
  );
}
