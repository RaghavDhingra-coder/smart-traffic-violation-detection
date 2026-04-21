// TODO for aware-user-dashboard: add richer educational feedback, prevention tips, and repeat analysis history.
import { useState } from "react";

import api from "../api/axios";
import FileUpload from "../components/FileUpload";

export default function AwareUserDashboard() {
  const [results, setResults] = useState([]);
  const [plate, setPlate] = useState("");
  const [lookup, setLookup] = useState(null);
  const [error, setError] = useState("");

  async function handleCheckVehicle(event) {
    event.preventDefault();
    try {
      setError("");
      const response = await api.get(`/vehicle/${plate}`);
      setLookup(response.data);
    } catch (requestError) {
      setLookup(null);
      setError(requestError.response?.data?.detail || "Could not fetch vehicle details.");
    }
  }

  const relevantViolations = results.filter((item) => ["no_helmet", "trippling"].includes(item.type));
  const pendingCount = lookup?.challans?.filter((item) => item.status === "pending").length || 0;

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-amber-50 via-white to-emerald-50 p-6 shadow-panel">
        <p className="text-sm uppercase tracking-[0.28em] text-emerald-700">Awareness Mode</p>
        <h1 className="mt-2 font-display text-3xl font-semibold text-ink md:text-4xl">Aware User Dashboard</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600 md:text-base">Upload an image or short clip to self-check common two-wheeler violations like helmet usage and trippling before you hit the road.</p>
      </section>

      <FileUpload onViolationsDetected={(payload) => setResults(payload.violations || [])} />

      <section className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Self-Check Summary</p>
        <div className="mt-4 grid gap-4 md:grid-cols-2">
          {relevantViolations.length > 0 ? relevantViolations.map((violation, index) => (
            <div key={`${violation.type}-${index}`} className="rounded-2xl bg-slate-50 p-5">
              <p className="text-sm text-slate-500">Detected issue</p>
              <h3 className="mt-1 font-display text-xl font-semibold capitalize text-ink">{violation.type.replaceAll("_", " ")}</h3>
              <p className="mt-2 text-sm text-slate-600">Confidence: {(violation.confidence * 100).toFixed(1)}%</p>
              <p className="mt-2 text-sm text-slate-600">Plate read: {violation.plate_number || "Unknown"}</p>
            </div>
          )) : <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50 p-6 text-slate-500 md:col-span-2">Upload an image or video to see helmet and trippling analysis here.</div>}
        </div>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <form onSubmit={handleCheckVehicle} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Check My Vehicle</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Pending challan lookup</h2>
          <input value={plate} onChange={(event) => setPlate(event.target.value.toUpperCase())} placeholder="KA01AB1234" className="mt-5 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          <button type="submit" className="mt-4 w-full rounded-2xl bg-emerald-600 px-5 py-3 font-semibold text-white">Check My Vehicle</button>
          {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
        </form>

        <div className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          {lookup ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Vehicle status</p>
                  <h3 className="mt-1 font-display text-2xl font-semibold text-ink">{lookup.vehicle.plate}</h3>
                </div>
                <span className={`rounded-full px-4 py-2 text-sm font-semibold ${pendingCount > 0 ? "bg-red-100 text-red-700" : "bg-emerald-100 text-emerald-700"}`}>{pendingCount > 0 ? `${pendingCount} pending challan(s)` : "No pending challans"}</span>
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Owner</p><p className="mt-1 font-semibold text-slate-900">{lookup.vehicle.owner_name}</p></div>
                <div className="rounded-2xl bg-slate-50 p-4"><p className="text-sm text-slate-500">Vehicle Type</p><p className="mt-1 font-semibold text-slate-900">{lookup.vehicle.vehicle_type}</p></div>
              </div>
              <div className="space-y-3">
                {lookup.challans.length > 0 ? lookup.challans.map((challan) => (
                  <div key={challan.id} className="rounded-2xl border border-slate-200 p-4 text-sm text-slate-600">
                    <p className="font-semibold capitalize text-slate-900">{challan.violation_type.replaceAll("_", " ")}</p>
                    <p>Status: {challan.status}</p>
                    <p>Amount: ?{challan.amount}</p>
                  </div>
                )) : <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500">No challans found for this vehicle.</div>}
              </div>
            </div>
          ) : (
            <div className="flex h-full min-h-72 items-center justify-center rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 text-slate-500">Vehicle lookup details appear here after a plate search.</div>
          )}
        </div>
      </section>
    </div>
  );
}
