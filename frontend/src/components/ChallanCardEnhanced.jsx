// Enhanced Challan Card Component with detailed information and actions
import { useState } from "react";
import PropTypes from "prop-types";

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

const STATUS_COLORS = {
  pending: "bg-amber-50 border-amber-200 text-amber-700",
  approved: "bg-blue-50 border-blue-200 text-blue-700",
  paid: "bg-emerald-50 border-emerald-200 text-emerald-700",
  dismissed: "bg-slate-50 border-slate-200 text-slate-700",
  appealed: "bg-purple-50 border-purple-200 text-purple-700",
};

export default function ChallanCard({ challan, onPay, loading }) {
  const [expanded, setExpanded] = useState(false);

  const formatDate = (date) => {
    return new Date(date).toLocaleDateString("en-IN", {
      year: "numeric",
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="rounded-2xl border border-slate-200 p-5 transition hover:shadow-lg">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <div className="flex items-center gap-3">
            <h3 className="font-display text-lg font-semibold text-ink">
              {VIOLATION_LABELS[challan.violation_type] || challan.violation_type}
            </h3>
            <span
              className={`rounded-full border px-3 py-1 text-xs font-semibold ${
                STATUS_COLORS[challan.status] || "bg-slate-50 border-slate-200 text-slate-700"
              }`}
            >
              {challan.status.charAt(0).toUpperCase() + challan.status.slice(1)}
            </span>
          </div>

          <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-2">
            <div>
              <p className="text-xs text-slate-500">Challan ID</p>
              <p className="font-semibold text-slate-900">#{challan.id}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Vehicle</p>
              <p className="font-semibold text-slate-900">{challan.plate}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Amount</p>
              <p className="font-semibold text-slate-900">₹{challan.amount}</p>
            </div>
            <div>
              <p className="text-xs text-slate-500">Issued On</p>
              <p className="font-semibold text-slate-900">{formatDate(challan.timestamp)}</p>
            </div>
          </div>

          {challan.location && (
            <div className="mt-3 text-sm">
              <p className="text-xs text-slate-500">Location</p>
              <p className="font-medium text-slate-700">{challan.location}</p>
            </div>
          )}
        </div>

        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-1 text-2xl text-slate-400 hover:text-slate-600"
        >
          {expanded ? "−" : "+"}
        </button>
      </div>

      {/* Expanded Details */}
      {expanded && (
        <div className="mt-4 space-y-4 border-t pt-4">
          {challan.officer_id && (
            <div>
              <p className="text-xs text-slate-500">Officer Badge</p>
              <p className="font-medium text-slate-700">{challan.officer_id}</p>
            </div>
          )}

          {challan.evidence && (
            <div className="rounded-lg bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-700">Evidence</p>
              <div className="mt-2 space-y-1 text-sm text-slate-600">
                <p>
                  Confidence:{" "}
                  <span className="font-semibold text-slate-900">
                    {(challan.evidence.confidence_score * 100).toFixed(1)}%
                  </span>
                </p>
                {challan.evidence.frame_index && (
                  <p>
                    Frame:{" "}
                    <span className="font-semibold text-slate-900">#{challan.evidence.frame_index}</span>
                  </p>
                )}
              </div>
            </div>
          )}

          {challan.dismissal_reason && (
            <div className="rounded-lg border border-slate-300 bg-slate-50 p-3">
              <p className="text-xs font-semibold text-slate-700">Dismissal Reason</p>
              <p className="mt-1 text-sm text-slate-600">{challan.dismissal_reason}</p>
            </div>
          )}

          {challan.appeal_notes && (
            <div className="rounded-lg border border-purple-300 bg-purple-50 p-3">
              <p className="text-xs font-semibold text-purple-700">Appeal Notes</p>
              <p className="mt-1 text-sm text-purple-600">{challan.appeal_notes}</p>
            </div>
          )}

          {challan.status === "pending" && onPay && (
            <button
              onClick={() => onPay(challan)}
              disabled={loading}
              className="mt-2 w-full rounded-lg bg-ink px-4 py-2 font-semibold text-white hover:bg-slate-800 disabled:opacity-50"
            >
              {loading ? "Processing..." : "Pay Now"}
            </button>
          )}
        </div>
      )}

      {/* Quick Action Footer */}
      {challan.status === "pending" && onPay && !expanded && (
        <div className="mt-4 pt-4 border-t">
          <button
            onClick={() => onPay(challan)}
            disabled={loading}
            className="w-full rounded-lg bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {loading ? "Processing..." : `Pay ₹${challan.amount}`}
          </button>
        </div>
      )}
    </div>
  );
}

ChallanCard.propTypes = {
  challan: PropTypes.shape({
    id: PropTypes.number.isRequired,
    plate: PropTypes.string.isRequired,
    violation_type: PropTypes.string.isRequired,
    amount: PropTypes.number.isRequired,
    status: PropTypes.string.isRequired,
    timestamp: PropTypes.string.isRequired,
    location: PropTypes.string,
    officer_id: PropTypes.string,
    dismissal_reason: PropTypes.string,
    appeal_notes: PropTypes.string,
    evidence: PropTypes.object,
  }).isRequired,
  onPay: PropTypes.func,
  loading: PropTypes.bool,
};

ChallanCard.defaultProps = {
  onPay: null,
  loading: false,
};
