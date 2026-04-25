// TODO for police-dashboard: add real-time officer workflow, filtering, and live stats powered by backend analytics.
import { useMemo, useState } from "react";

import api from "../api/axios";
import WebcamCapture from "../components/WebcamCapture";
import ViolationCard from "../components/ViolationCard";

const fineMap = {
  NO_HELMET: 500,
  TRIPPLING: 1000,
  TRIPLE_RIDING: 1000,
  OVERSPEEDING: 2000,
  TRAFFIC_LIGHT_JUMP: 1000,
  SIGNAL_VIOLATION: 1000,
  NO_NUMBER_PLATE: 5000,
};

const tabs = ["Live Detection", "Plate Lookup", "Issue Challan", "Stats"];

export default function PoliceDashboard() {
  const [activeTab, setActiveTab] = useState("Live Detection");
  const [liveFeed, setLiveFeed] = useState([]);
  const [lookupPlate, setLookupPlate] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [challanForm, setChallanForm] = useState({ plate: "", violation_type: "NO_HELMET", image_url: "" });
  const [submitMessage, setSubmitMessage] = useState("");

  const stats = useMemo(() => {
    const pendingPayments = liveFeed.filter((entry) => entry.detections?.some((violation) => violation.type)).length;
    const breakdown = liveFeed.flatMap((entry) => entry.detections || []).reduce((acc, violation) => {
      acc[violation.type] = (acc[violation.type] || 0) + 1;
      return acc;
    }, {});

    return {
      totalChallansToday: liveFeed.length,
      pendingPayments,
      breakdown,
    };
  }, [liveFeed]);

  async function handlePlateLookup(event) {
    event.preventDefault();
    try {
      setLookupError("");
      const response = await api.get(`/challan/${lookupPlate}`);
      setLookupResult(response.data);
    } catch (error) {
      setLookupResult(null);
      setLookupError(error.response?.data?.detail || "Plate lookup failed.");
    }
  }

  async function handleIssueChallan(event) {
    event.preventDefault();
    try {
      const response = await api.post("/challan", {
        ...challanForm,
        timestamp: new Date().toISOString(),
      });
      setSubmitMessage(`Challan #${response.data.id} created for ${response.data.plate}.`);
      setChallanForm({ plate: "", violation_type: "NO_HELMET", image_url: "" });
    } catch (error) {
      setSubmitMessage(error.response?.data?.detail || "Failed to create challan.");
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-ink via-asphalt to-slate-900 p-6 text-white shadow-panel">
        <p className="text-sm uppercase tracking-[0.28em] text-amber-300">Operations Control</p>
        <h1 className="mt-2 font-display text-3xl font-semibold md:text-4xl">Police Dashboard</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-200 md:text-base">
          Monitor live detections, search vehicle records, issue challans, and track the violation pipeline in one place.
        </p>
      </section>

      <div className="flex flex-wrap gap-3">
        {tabs.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
              activeTab === tab ? "bg-ink text-white" : "bg-white text-slate-600 shadow-panel"
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "Live Detection" ? (
        <div className="space-y-6">
          <WebcamCapture onViolationDetected={(result) => setLiveFeed((prev) => [result, ...prev].slice(0, 8))} />
          <section className="grid gap-4 lg:grid-cols-2">
            {liveFeed.map((entry, entryIndex) =>
              (entry.detections || []).map((violation, violationIndex) => (
                <ViolationCard
                  key={`${entry.timestamp}-${entryIndex}-${violationIndex}`}
                  violation={{
                    ...violation,
                    sourceLabel: `Live event ${new Date(entry.timestamp).toLocaleTimeString()}`,
                  }}
                />
              ))
            )}
          </section>
        </div>
      ) : null}

      {activeTab === "Plate Lookup" ? (
        <section className="grid gap-6 lg:grid-cols-[0.75fr_1.25fr]">
          <form onSubmit={handlePlateLookup} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember">Lookup</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Search by plate</h2>
            <input
              value={lookupPlate}
              onChange={(event) => setLookupPlate(event.target.value.toUpperCase())}
              placeholder="KA01AB1234"
              className="mt-5 w-full rounded-2xl border border-slate-200 px-4 py-3 outline-none ring-0 transition focus:border-amber-400"
            />
            <button type="submit" className="mt-4 rounded-2xl bg-ink px-5 py-3 font-semibold text-white">
              Lookup Vehicle
            </button>
            {lookupError ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{lookupError}</p> : null}
          </form>

          <div className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
            {lookupResult ? (
              <div className="space-y-5">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Plate</p>
                  <h3 className="mt-1 font-display text-2xl font-semibold text-ink">{lookupPlate || "N/A"}</h3>
                </div>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Challan History</p>
                  <div className="mt-3 space-y-3">
                    {lookupResult.length > 0 ? lookupResult.map((challan) => (
                      <div key={challan.id} className="rounded-2xl border border-slate-200 p-4 text-sm text-slate-600">
                        <p className="font-semibold capitalize text-slate-900">{challan.violation_type.replaceAll("_", " ")}</p>
                        <p>Status: {challan.status}</p>
                        <p>Time: {new Date(challan.timestamp).toLocaleString()}</p>
                      </div>
                    )) : <p className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">No challans found for this plate.</p>}
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex h-full min-h-72 items-center justify-center rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 text-slate-500">
                Lookup results will appear here.
              </div>
            )}
          </div>
        </section>
      ) : null}

      {activeTab === "Issue Challan" ? (
        <section className="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <form onSubmit={handleIssueChallan} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember">Manual Action</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Issue a challan</h2>
            <div className="mt-5 space-y-4">
              <input value={challanForm.plate} onChange={(event) => setChallanForm((prev) => ({ ...prev, plate: event.target.value.toUpperCase() }))} placeholder="Vehicle plate" className="w-full rounded-2xl border border-slate-200 px-4 py-3" />
              <select value={challanForm.violation_type} onChange={(event) => setChallanForm((prev) => ({ ...prev, violation_type: event.target.value }))} className="w-full rounded-2xl border border-slate-200 px-4 py-3">
                {Object.keys(fineMap).map((key) => <option key={key} value={key}>{key.replaceAll("_", " ")}</option>)}
              </select>
              <input value={challanForm.image_url} onChange={(event) => setChallanForm((prev) => ({ ...prev, image_url: event.target.value }))} placeholder="Evidence image URL (optional)" className="w-full rounded-2xl border border-slate-200 px-4 py-3" />
              <div className="rounded-2xl bg-amber-50 px-4 py-3 text-sm text-amber-800">Auto-filled fine amount: <span className="font-bold">?{fineMap[challanForm.violation_type]}</span></div>
              <button type="submit" className="w-full rounded-2xl bg-ink px-5 py-3 font-semibold text-white">Create Challan</button>
              {submitMessage ? <p className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-700">{submitMessage}</p> : null}
            </div>
          </form>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">No Helmet</p><p className="mt-2 font-display text-3xl font-bold text-ink">?500</p></div>
            <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">Trippling</p><p className="mt-2 font-display text-3xl font-bold text-ink">?1000</p></div>
            <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">Overspeeding</p><p className="mt-2 font-display text-3xl font-bold text-ink">?2000</p></div>
            <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">Signal Violation</p><p className="mt-2 font-display text-3xl font-bold text-ink">?1000</p></div>
            <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">No Number Plate</p><p className="mt-2 font-display text-3xl font-bold text-ink">?5000</p></div>
          </div>
        </section>
      ) : null}

      {activeTab === "Stats" ? (
        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">Total Challans Today</p><p className="mt-2 font-display text-4xl font-bold text-ink">{stats.totalChallansToday}</p></div>
          <div className="rounded-[2rem] bg-white p-6 shadow-panel"><p className="text-sm text-slate-500">Pending Payments</p><p className="mt-2 font-display text-4xl font-bold text-ink">{stats.pendingPayments}</p></div>
          <div className="rounded-[2rem] bg-white p-6 shadow-panel md:col-span-2 xl:col-span-2">
            <p className="text-sm text-slate-500">Violation Type Breakdown</p>
            <div className="mt-4 flex flex-wrap gap-3">
              {Object.entries(stats.breakdown).length > 0 ? Object.entries(stats.breakdown).map(([key, value]) => (
                <span key={key} className="rounded-full bg-slate-100 px-4 py-2 text-sm font-semibold text-slate-700">{key.replaceAll("_", " ")}: {value}</span>
              )) : <span className="rounded-full bg-slate-100 px-4 py-2 text-sm text-slate-500">Placeholder until live data arrives</span>}
            </div>
          </div>
        </section>
      ) : null}
    </div>
  );
}
