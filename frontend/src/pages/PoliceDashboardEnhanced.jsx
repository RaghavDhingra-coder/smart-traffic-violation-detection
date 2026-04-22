// Enhanced Police Dashboard with officer workflow and real-time analytics
import { useMemo, useState } from "react";
import api from "../api/axios";
import WebcamCapture from "../components/WebcamCapture";
import ViolationCard from "../components/ViolationCard";

const VIOLATION_FINES = {
  NO_HELMET: 500,
  TRIPPLING: 1000,
  OVER_SPEED: 2000,
  TRAFFIC_LIGHT_JUMP: 1000,
  NO_PARKING: 500,
  NO_NUMBER_PLATE: 5000,
  RASH_DRIVING: 2500,
  WRONG_WAY: 1500,
};

const VIOLATION_LABELS = {
  OVER_SPEED: "Speeding",
  NO_HELMET: "No Helmet",
  TRIPPLING: "Trippling",
  TRAFFIC_LIGHT_JUMP: "Signal Jump",
  NO_PARKING: "Illegal Parking",
  NO_NUMBER_PLATE: "No Number Plate",
  RASH_DRIVING: "Rash Driving",
  WRONG_WAY: "Wrong Way",
};

const tabs = ["Live Detection", "Plate Lookup", "Issue Challan", "Stats", "Officer Actions"];

export default function PoliceDashboard() {
  const [activeTab, setActiveTab] = useState("Live Detection");
  const [liveFeed, setLiveFeed] = useState([]);
  const [lookupPlate, setLookupPlate] = useState("");
  const [lookupResult, setLookupResult] = useState(null);
  const [lookupError, setLookupError] = useState("");
  const [challanForm, setChallanForm] = useState({
    plate: "",
    violation_type: "NO_HELMET",
    image_path: "",
    officer_id: "BADGE001",
    location: "",
  });
  const [submitMessage, setSubmitMessage] = useState("");
  const [selectedViolation, setSelectedViolation] = useState(null);

  const stats = useMemo(() => {
    const allViolations = liveFeed.flatMap((entry) => entry.violations || []);
    const breakdown = allViolations.reduce((acc, violation) => {
      acc[violation.type] = (acc[violation.type] || 0) + 1;
      return acc;
    }, {});

    const totalFines = Object.entries(breakdown).reduce((sum, [type, count]) => {
      return sum + (VIOLATION_FINES[type] || 0) * count;
    }, 0);

    return {
      totalDetections: liveFeed.length,
      totalViolations: allViolations.length,
      breakdown,
      totalFines,
      averageConfidence: allViolations.length > 0
        ? (allViolations.reduce((sum, v) => sum + v.confidence, 0) / allViolations.length * 100).toFixed(1)
        : 0,
    };
  }, [liveFeed]);

  async function handlePlateLookup(event) {
    event.preventDefault();
    try {
      setLookupError("");
      const response = await api.get(`/vehicle/${lookupPlate}`);
      setLookupResult(response.data);
    } catch (error) {
      setLookupResult(null);
      setLookupError(error.response?.data?.detail || "Plate lookup failed.");
    }
  }

  async function handleIssueChallan(event) {
    event.preventDefault();
    try {
      const response = await api.post("/challan", challanForm);
      setSubmitMessage(`✓ Challan #${response.data.id} created for ${response.data.plate}`);
      setChallanForm({
        plate: "",
        violation_type: "NO_HELMET",
        image_path: "",
        officer_id: "BADGE001",
        location: "",
      });
      setTimeout(() => setSubmitMessage(""), 3000);
    } catch (error) {
      setSubmitMessage("✗ " + (error.response?.data?.detail || "Failed to create challan."));
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-ink via-asphalt to-slate-900 p-6 text-white shadow-panel">
        <p className="text-sm uppercase tracking-[0.28em] text-amber-300">Operations Control</p>
        <h1 className="mt-2 font-display text-3xl font-semibold md:text-4xl">Police Dashboard</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-200 md:text-base">
          Monitor live detections, manage vehicle records, issue and track challans, and review officer actions.
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

      {/* Live Detection Tab */}
      {activeTab === "Live Detection" && (
        <div className="space-y-6">
          <WebcamCapture onViolationDetected={(result) => setLiveFeed((prev) => [result, ...prev].slice(0, 12))} />

          <section className="grid gap-4 lg:grid-cols-2">
            {liveFeed.map((entry, entryIndex) =>
              (entry.violations || []).map((violation, violationIndex) => (
                <ViolationCard
                  key={`${entry.timestamp}-${entryIndex}-${violationIndex}`}
                  violation={{
                    ...violation,
                    sourceLabel: `Live event ${new Date(entry.timestamp).toLocaleTimeString()}`,
                  }}
                  onClick={() => {
                    setChallanForm({
                      ...challanForm,
                      plate: violation.plate_number || "",
                      violation_type: violation.type,
                      image_path: violation.annotated_frame_base64 || "",
                    });
                    setActiveTab("Issue Challan");
                  }}
                />
              ))
            )}
          </section>

          {liveFeed.length === 0 && (
            <div className="rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-500">
              No live detections yet. Start the webcam capture to begin.
            </div>
          )}
        </div>
      )}

      {/* Plate Lookup Tab */}
      {activeTab === "Plate Lookup" && (
        <section className="grid gap-6 lg:grid-cols-2">
          <form onSubmit={handlePlateLookup} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Vehicle Search</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Enter plate number</h2>
            <input
              value={lookupPlate}
              onChange={(event) => setLookupPlate(event.target.value.toUpperCase())}
              placeholder="KA01AB1234"
              className="mt-5 w-full rounded-2xl border border-slate-200 px-4 py-3"
            />
            <button
              type="submit"
              className="mt-4 w-full rounded-2xl bg-ink px-5 py-3 font-semibold text-white hover:bg-slate-800"
            >
              Search Vehicle
            </button>
            {lookupError && (
              <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{lookupError}</p>
            )}
          </form>

          {lookupResult && (
            <div className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
              <h3 className="font-display text-xl font-semibold text-ink">Vehicle Details</h3>
              <div className="mt-4 space-y-3">
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Registration Number</p>
                  <p className="font-semibold text-slate-900">{lookupResult.vehicle?.plate}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Owner Name</p>
                  <p className="font-semibold text-slate-900">{lookupResult.vehicle?.owner_name}</p>
                </div>
                <div className="rounded-lg bg-slate-50 p-3">
                  <p className="text-xs text-slate-500">Vehicle Type</p>
                  <p className="font-semibold text-slate-900">{lookupResult.vehicle?.vehicle_type}</p>
                </div>
                <div className="mt-4 border-t pt-4">
                  <p className="text-xs font-semibold uppercase text-slate-500">Challan History</p>
                  <div className="mt-3 space-y-2">
                    {lookupResult.challans?.length > 0 ? (
                      lookupResult.challans.map((challan) => (
                        <div key={challan.id} className="rounded-lg bg-amber-50 p-3 text-sm">
                          <p className="font-semibold text-amber-900">
                            {VIOLATION_LABELS[challan.violation_type] || challan.violation_type}
                          </p>
                          <p className="text-amber-700">₹{challan.amount} • {challan.status}</p>
                        </div>
                      ))
                    ) : (
                      <p className="text-slate-500">No challan history found.</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )}
        </section>
      )}

      {/* Issue Challan Tab */}
      {activeTab === "Issue Challan" && (
        <section className="grid gap-6 lg:grid-cols-2">
          <form onSubmit={handleIssueChallan} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Create New Challan</p>
            <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Violation Details</h2>

            <div className="mt-6 space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700">Vehicle Plate</label>
                <input
                  type="text"
                  value={challanForm.plate}
                  onChange={(e) => setChallanForm({ ...challanForm, plate: e.target.value.toUpperCase() })}
                  placeholder="KA01AB1234"
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700">Violation Type</label>
                <select
                  value={challanForm.violation_type}
                  onChange={(e) => setChallanForm({ ...challanForm, violation_type: e.target.value })}
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2"
                >
                  {Object.entries(VIOLATION_FINES).map(([type, fine]) => (
                    <option key={type} value={type}>
                      {VIOLATION_LABELS[type] || type} (₹{fine})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700">Location</label>
                <input
                  type="text"
                  value={challanForm.location}
                  onChange={(e) => setChallanForm({ ...challanForm, location: e.target.value })}
                  placeholder="e.g., Ring Road, Delhi"
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700">Officer Badge ID</label>
                <input
                  type="text"
                  value={challanForm.officer_id}
                  onChange={(e) => setChallanForm({ ...challanForm, officer_id: e.target.value })}
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2"
                />
              </div>

              <button
                type="submit"
                className="mt-6 w-full rounded-lg bg-ink px-4 py-3 font-semibold text-white hover:bg-slate-800"
              >
                Issue Challan
              </button>

              {submitMessage && (
                <div
                  className={`rounded-lg p-3 text-sm font-semibold ${
                    submitMessage.startsWith("✓")
                      ? "bg-emerald-100 text-emerald-700"
                      : "bg-red-100 text-red-700"
                  }`}
                >
                  {submitMessage}
                </div>
              )}
            </div>
          </form>

          <div className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
            <p className="text-xs font-semibold uppercase text-slate-500">Fine Reference</p>
            <h3 className="mt-1 font-display text-xl font-semibold text-ink">Violation Penalties</h3>
            <div className="mt-4 space-y-2">
              {Object.entries(VIOLATION_FINES).map(([type, fine]) => (
                <div key={type} className="flex items-center justify-between rounded-lg bg-slate-50 p-3">
                  <span className="font-medium text-slate-700">{VIOLATION_LABELS[type] || type}</span>
                  <span className="font-bold text-slate-900">₹{fine}</span>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Stats Tab */}
      {activeTab === "Stats" && (
        <section className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Real-time Analytics</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Detection Statistics</h2>

          <div className="mt-6 grid gap-4 md:grid-cols-4">
            <div className="rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 p-4">
              <p className="text-sm text-slate-600">Total Detections</p>
              <p className="mt-2 text-3xl font-bold text-blue-700">{stats.totalDetections}</p>
            </div>
            <div className="rounded-lg bg-gradient-to-br from-red-50 to-red-100 p-4">
              <p className="text-sm text-slate-600">Total Violations</p>
              <p className="mt-2 text-3xl font-bold text-red-700">{stats.totalViolations}</p>
            </div>
            <div className="rounded-lg bg-gradient-to-br from-amber-50 to-amber-100 p-4">
              <p className="text-sm text-slate-600">Potential Revenue</p>
              <p className="mt-2 text-3xl font-bold text-amber-700">₹{stats.totalFines.toLocaleString()}</p>
            </div>
            <div className="rounded-lg bg-gradient-to-br from-emerald-50 to-emerald-100 p-4">
              <p className="text-sm text-slate-600">Avg Confidence</p>
              <p className="mt-2 text-3xl font-bold text-emerald-700">{stats.averageConfidence}%</p>
            </div>
          </div>

          <div className="mt-6 border-t pt-6">
            <h3 className="font-semibold text-slate-900">Violation Breakdown</h3>
            <div className="mt-4 space-y-2">
              {Object.entries(stats.breakdown).map(([type, count]) => (
                <div key={type} className="flex items-center justify-between">
                  <span className="text-slate-700">{VIOLATION_LABELS[type] || type}</span>
                  <div className="flex items-center gap-3">
                    <span className="font-semibold text-slate-900">{count}</span>
                    <span className="text-sm text-slate-500">₹{(VIOLATION_FINES[type] * count).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>
      )}

      {/* Officer Actions Tab */}
      {activeTab === "Officer Actions" && (
        <section className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Officer Workflow</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Review & Approve</h2>
          <p className="mt-2 text-sm text-slate-600">
            Review pending challans, approve violations, and manage dismissal requests from here.
          </p>

          <div className="mt-6">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="rounded-lg border-l-4 border-amber-500 bg-amber-50 p-4">
                <p className="text-sm font-semibold text-amber-700">Pending Review</p>
                <p className="mt-1 text-2xl font-bold text-amber-900">0</p>
              </div>
              <div className="rounded-lg border-l-4 border-emerald-500 bg-emerald-50 p-4">
                <p className="text-sm font-semibold text-emerald-700">Approved</p>
                <p className="mt-1 text-2xl font-bold text-emerald-900">0</p>
              </div>
              <div className="rounded-lg border-l-4 border-slate-500 bg-slate-50 p-4">
                <p className="text-sm font-semibold text-slate-700">Dismissed</p>
                <p className="mt-1 text-2xl font-bold text-slate-900">0</p>
              </div>
            </div>

            <div className="mt-6 rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-500">
              <p>Officer actions workflow will appear here when challans require review.</p>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
