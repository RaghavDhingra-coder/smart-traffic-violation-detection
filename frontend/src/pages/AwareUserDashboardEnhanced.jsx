// Enhanced Aware User Dashboard with educational feedback and violation prevention
import { useState, useMemo } from "react";
import api from "../api/axios";
import FileUpload from "../components/FileUpload";

const VIOLATION_PREVENTION_TIPS = {
  NO_HELMET: [
    "Always wear an ISI-certified helmet",
    "Ensure the helmet is properly fastened",
    "Replace helmets after accidents",
    "Helmets reduce head injury risk by 70%",
  ],
  TRIPPLING: [
    "Only ride with one passenger maximum",
    "Passenger should sit properly on the seat",
    "Keep proper balance on the road",
    "Avoid overloading the vehicle",
  ],
  OVER_SPEED: [
    "Follow posted speed limits",
    "Reduce speed in residential areas",
    "Adjust speed based on weather conditions",
    "Speeding reduces reaction time",
  ],
  TRAFFIC_LIGHT_JUMP: [
    "Always wait for green signal",
    "Observe pedestrian movement",
    "Check both directions at intersections",
    "Be patient at traffic signals",
  ],
  RASH_DRIVING: [
    "Maintain safe distance from other vehicles",
    "Avoid sudden lane changes",
    "Don't use phone while driving",
    "Keep both hands on the steering wheel",
  ],
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

export default function AwareUserDashboard() {
  const [results, setResults] = useState([]);
  const [plate, setPlate] = useState("");
  const [lookup, setLookup] = useState(null);
  const [error, setError] = useState("");
  const [expandedViolation, setExpandedViolation] = useState(null);

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

  // Identify relevant violations based on uploaded content
  const detectedViolations = useMemo(() => {
    return results.filter((item) => VIOLATION_PREVENTION_TIPS[item.type]);
  }, [results]);

  const mostCritical = useMemo(() => {
    if (detectedViolations.length === 0) return null;
    return detectedViolations.reduce((max, v) => (v.confidence > max.confidence ? v : max));
  }, [detectedViolations]);

  const pendingCount = lookup?.challans?.filter((item) => item.status === "pending").length || 0;
  const totalAmount = lookup?.challans?.reduce((sum, c) => sum + c.amount, 0) || 0;

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-amber-50 via-white to-emerald-50 p-6 shadow-panel">
        <p className="text-sm uppercase tracking-[0.28em] text-emerald-700">Awareness Mode</p>
        <h1 className="mt-2 font-display text-3xl font-semibold text-ink md:text-4xl">Aware User Dashboard</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600 md:text-base">
          Self-check your compliance before hitting the road. Upload images or videos to detect violations and receive
          personalized prevention tips.
        </p>
      </section>

      <FileUpload onViolationsDetected={(payload) => setResults(payload.violations || [])} />

      {/* Violation Summary */}
      {detectedViolations.length > 0 && (
        <section className="rounded-[2rem] border-l-4 border-orange-500 bg-gradient-to-r from-orange-50 to-amber-50 p-6 shadow-panel">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-orange-700">Violations Detected</p>
              <h2 className="mt-1 font-display text-2xl font-semibold text-ink">
                {detectedViolations.length} issue{detectedViolations.length !== 1 ? "s" : ""} found
              </h2>
              <p className="mt-2 text-sm text-slate-600">
                Review the violations below and follow the prevention tips to avoid traffic challan in the future.
              </p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-orange-200">
              <span className="text-xl font-bold text-orange-700">⚠️</span>
            </div>
          </div>

          {mostCritical && (
            <div className="mt-4 rounded-lg border-2 border-red-300 bg-white p-4">
              <p className="text-sm font-semibold text-red-700">Most Critical Issue</p>
              <p className="mt-1 text-lg font-bold text-ink">
                {VIOLATION_LABELS[mostCritical.type] || mostCritical.type}
              </p>
              <p className="mt-1 text-sm text-slate-600">Confidence: {(mostCritical.confidence * 100).toFixed(1)}%</p>
            </div>
          )}
        </section>
      )}

      {/* Detailed Violation Analysis */}
      {detectedViolations.length > 0 && (
        <section className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Detailed Analysis</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Prevention Guide</h2>

          <div className="mt-6 space-y-4">
            {detectedViolations.map((violation, index) => (
              <div
                key={`${violation.type}-${index}`}
                className="rounded-xl border border-slate-200 p-5 transition hover:shadow-md"
              >
                <div
                  className="flex cursor-pointer items-start justify-between"
                  onClick={() =>
                    setExpandedViolation(expandedViolation === index ? null : index)
                  }
                >
                  <div>
                    <h3 className="font-display text-lg font-semibold text-ink">
                      {VIOLATION_LABELS[violation.type] || violation.type}
                    </h3>
                    <div className="mt-2 flex gap-4 text-sm text-slate-600">
                      <span>Confidence: {(violation.confidence * 100).toFixed(1)}%</span>
                      {violation.plate_number && <span>Plate: {violation.plate_number}</span>}
                    </div>
                  </div>
                  <button
                    type="button"
                    className="mt-1 text-2xl text-slate-400 hover:text-slate-600"
                  >
                    {expandedViolation === index ? "−" : "+"}
                  </button>
                </div>

                {expandedViolation === index && (
                  <div className="mt-4 space-y-4 border-t pt-4">
                    <div>
                      <h4 className="font-semibold text-slate-900">Prevention Tips:</h4>
                      <ul className="mt-3 space-y-2">
                        {(VIOLATION_PREVENTION_TIPS[violation.type] || []).map((tip, tipIndex) => (
                          <li key={tipIndex} className="flex items-start gap-3 text-sm text-slate-700">
                            <span className="mt-0.5 flex h-5 w-5 items-center justify-center rounded-full bg-emerald-100 text-xs font-bold text-emerald-700">
                              ✓
                            </span>
                            {tip}
                          </li>
                        ))}
                      </ul>
                    </div>

                    <div className="rounded-lg bg-blue-50 p-4">
                      <p className="text-sm font-semibold text-blue-900">📋 Compliance Recommendation</p>
                      <p className="mt-1 text-sm text-blue-800">
                        {violation.confidence > 0.8
                          ? "High confidence detection. Immediate action recommended."
                          : "Moderate confidence. Review and take corrective measures."}
                      </p>
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {detectedViolations.length === 0 && results.length > 0 && (
        <section className="rounded-[2rem] border-l-4 border-emerald-500 bg-gradient-to-r from-emerald-50 to-green-50 p-6 shadow-panel">
          <div className="flex items-start justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Great Job!</p>
              <h2 className="mt-1 font-display text-2xl font-semibold text-ink">No major violations detected</h2>
              <p className="mt-2 text-sm text-slate-600">Your image appears compliant with traffic rules.</p>
            </div>
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-200">
              <span className="text-xl">✓</span>
            </div>
          </div>
        </section>
      )}

      {/* Vehicle Lookup Section */}
      <section className="grid gap-6 lg:grid-cols-[0.85fr_1.15fr]">
        <form onSubmit={handleCheckVehicle} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-700">Check My Vehicle</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Pending challan lookup</h2>
          <p className="mt-2 text-sm text-slate-600">
            Enter your vehicle number to check for any pending challans or violations.
          </p>
          <input
            value={plate}
            onChange={(event) => setPlate(event.target.value.toUpperCase())}
            placeholder="KA01AB1234"
            className="mt-5 w-full rounded-2xl border border-slate-200 px-4 py-3"
          />
          <button
            type="submit"
            className="mt-4 w-full rounded-2xl bg-emerald-600 px-5 py-3 font-semibold text-white hover:bg-emerald-700"
          >
            Check My Vehicle
          </button>
          {error && <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        </form>

        <div className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          {lookup ? (
            <div className="space-y-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Vehicle Status</p>
                  <h3 className="mt-1 font-display text-2xl font-semibold text-ink">{lookup.vehicle.plate}</h3>
                </div>
                <span
                  className={`rounded-full px-4 py-2 text-sm font-semibold ${
                    pendingCount > 0
                      ? "bg-red-100 text-red-700"
                      : "bg-emerald-100 text-emerald-700"
                  }`}
                >
                  {pendingCount > 0 ? `${pendingCount} pending` : "Clear"}
                </span>
              </div>

              <div className="grid gap-3 md:grid-cols-2">
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Owner</p>
                  <p className="mt-1 font-semibold text-slate-900">{lookup.vehicle.owner_name}</p>
                </div>
                <div className="rounded-2xl bg-slate-50 p-4">
                  <p className="text-sm text-slate-500">Vehicle Type</p>
                  <p className="mt-1 font-semibold text-slate-900">{lookup.vehicle.vehicle_type}</p>
                </div>
              </div>

              {lookup.challans && lookup.challans.length > 0 && (
                <div className="rounded-lg border-l-4 border-amber-500 bg-amber-50 p-4">
                  <p className="font-semibold text-amber-900">Pending Amount</p>
                  <p className="mt-1 text-lg font-bold text-amber-700">₹{totalAmount.toLocaleString()}</p>
                </div>
              )}

              <div className="space-y-3">
                {lookup.challans && lookup.challans.length > 0 ? (
                  lookup.challans.map((challan) => (
                    <div
                      key={challan.id}
                      className={`rounded-2xl p-4 text-sm ${
                        challan.status === "pending"
                          ? "border border-red-200 bg-red-50"
                          : "border border-slate-200 bg-slate-50"
                      }`}
                    >
                      <p className="font-semibold capitalize text-slate-900">
                        {VIOLATION_LABELS[challan.violation_type] || challan.violation_type}
                      </p>
                      <div className="mt-2 flex items-center justify-between text-xs text-slate-600">
                        <span>Status: {challan.status}</span>
                        <span className="font-bold">₹{challan.amount}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-2xl bg-emerald-50 p-4 text-center text-sm text-emerald-700">
                    ✓ No challans found. Keep maintaining compliance!
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="flex h-full min-h-72 items-center justify-center rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 text-center text-slate-500">
              <div>
                <p className="text-lg">🔍</p>
                <p className="mt-2">Vehicle details appear here</p>
                <p className="text-sm">after a plate search.</p>
              </div>
            </div>
          )}
        </div>
      </section>

      {/* Educational Resources */}
      <section className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Resources</p>
        <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Road Safety Tips</h2>

        <div className="mt-6 grid gap-4 md:grid-cols-3">
          <div className="rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 p-4">
            <p className="text-2xl">🎓</p>
            <p className="mt-2 font-semibold text-slate-900">Know the Rules</p>
            <p className="mt-1 text-sm text-slate-600">
              Familiarize yourself with local traffic regulations and speed limits.
            </p>
          </div>

          <div className="rounded-lg bg-gradient-to-br from-emerald-50 to-emerald-100 p-4">
            <p className="text-2xl">⛑️</p>
            <p className="mt-2 font-semibold text-slate-900">Safety First</p>
            <p className="mt-1 text-sm text-slate-600">
              Always wear safety gear and follow defensive driving practices.
            </p>
          </div>

          <div className="rounded-lg bg-gradient-to-br from-amber-50 to-amber-100 p-4">
            <p className="text-2xl">🎯</p>
            <p className="mt-2 font-semibold text-slate-900">Stay Aware</p>
            <p className="mt-1 text-sm text-slate-600">
              Keep checking this dashboard regularly to maintain compliance.
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
