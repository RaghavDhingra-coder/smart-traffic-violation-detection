// Enhanced Violation Card Component with detailed frame and confidence information
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

const VIOLATION_FINES = {
  OVER_SPEED: 2000,
  NO_HELMET: 500,
  TRIPPLING: 1000,
  TRAFFIC_LIGHT_JUMP: 1000,
  NO_PARKING: 500,
  NO_NUMBER_PLATE: 5000,
  RASH_DRIVING: 2500,
  WRONG_WAY: 1500,
};

const CONFIDENCE_LEVELS = {
  high: { min: 0.8, color: "text-red-600", bg: "bg-red-50", label: "High" },
  medium: { min: 0.6, color: "text-amber-600", bg: "bg-amber-50", label: "Medium" },
  low: { min: 0, color: "text-slate-600", bg: "bg-slate-50", label: "Low" },
};

function getConfidenceLevel(confidence) {
  if (confidence >= 0.8) return CONFIDENCE_LEVELS.high;
  if (confidence >= 0.6) return CONFIDENCE_LEVELS.medium;
  return CONFIDENCE_LEVELS.low;
}

export default function ViolationCard({ violation, onClick, sourceLabel }) {
  const [showImage, setShowImage] = useState(false);
  const confidenceLevel = getConfidenceLevel(violation.confidence);
  const fine = VIOLATION_FINES[violation.type] || 1000;

  const renderAnnotatedFrame = () => {
    if (!violation.annotated_frame_base64) return null;

    return (
      <img
        src={`data:image/jpeg;base64,${violation.annotated_frame_base64}`}
        alt="Annotated violation frame"
        className="mt-2 w-full rounded-lg object-cover"
      />
    );
  };

  return (
    <div
      className={`cursor-pointer rounded-2xl border transition hover:shadow-lg ${confidenceLevel.bg}`}
      onClick={onClick}
    >
      <div className="p-4 sm:p-5">
        {/* Header */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <h3 className="font-display text-lg font-semibold text-ink">
              {VIOLATION_LABELS[violation.type] || violation.type}
            </h3>
            {sourceLabel && (
              <p className="mt-1 text-xs text-slate-500">{sourceLabel}</p>
            )}
          </div>
          <div className="text-right">
            <p className="text-2xl font-bold text-ink">₹{fine}</p>
            <p className="text-xs text-slate-500">Potential fine</p>
          </div>
        </div>

        {/* Main Info */}
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg bg-white/50 p-3">
            <p className="text-xs font-semibold text-slate-600">Confidence</p>
            <div className="mt-2 flex items-center gap-2">
              <div className="h-2 flex-1 rounded-full bg-white">
                <div
                  className={`h-full rounded-full ${
                    violation.confidence >= 0.8
                      ? "bg-red-500"
                      : violation.confidence >= 0.6
                      ? "bg-amber-500"
                      : "bg-slate-500"
                  }`}
                  style={{ width: `${violation.confidence * 100}%` }}
                />
              </div>
              <span className={`font-bold ${confidenceLevel.color}`}>
                {(violation.confidence * 100).toFixed(0)}%
              </span>
            </div>
          </div>

          {violation.plate_number && (
            <div className="rounded-lg bg-white/50 p-3">
              <p className="text-xs font-semibold text-slate-600">Plate Detected</p>
              <p className="mt-2 font-display text-lg font-bold text-ink">
                {violation.plate_number}
              </p>
            </div>
          )}

          {violation.frame_metadata && (
            <div className="rounded-lg bg-white/50 p-3">
              <p className="text-xs font-semibold text-slate-600">Frame Index</p>
              <p className="mt-2 font-mono text-sm font-bold text-slate-900">
                #{violation.frame_metadata.frame_index}
              </p>
            </div>
          )}

          {violation.evidence_quality && (
            <div className="rounded-lg bg-white/50 p-3">
              <p className="text-xs font-semibold text-slate-600">Evidence Quality</p>
              <p className="mt-2 capitalize font-medium text-slate-900">
                {violation.evidence_quality}
              </p>
            </div>
          )}
        </div>

        {/* Annotated Frame Preview */}
        {violation.annotated_frame_base64 && (
          <div className="mt-4">
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowImage(!showImage);
              }}
              className="text-xs font-semibold text-slate-600 hover:text-slate-900"
            >
              {showImage ? "Hide" : "Show"} annotated frame
            </button>
            {showImage && renderAnnotatedFrame()}
          </div>
        )}

        {/* Frame Metadata Details */}
        {violation.frame_metadata?.bounding_box && (
          <div className="mt-3 rounded-lg bg-white/50 p-3 text-xs">
            <p className="font-semibold text-slate-600">Bounding Box</p>
            <p className="mt-1 font-mono text-slate-700">
              x1={violation.frame_metadata.bounding_box.x1?.toFixed(0)},
              y1={violation.frame_metadata.bounding_box.y1?.toFixed(0)},
              x2={violation.frame_metadata.bounding_box.x2?.toFixed(0)},
              y2={violation.frame_metadata.bounding_box.y2?.toFixed(0)}
            </p>
          </div>
        )}

        {/* Action Hint */}
        <div className="mt-4 text-center">
          <p className="text-xs font-semibold text-slate-600">Click to take action</p>
        </div>
      </div>
    </div>
  );
}

ViolationCard.propTypes = {
  violation: PropTypes.shape({
    type: PropTypes.string.isRequired,
    confidence: PropTypes.number.isRequired,
    plate_number: PropTypes.string,
    annotated_frame_base64: PropTypes.string,
    frame_metadata: PropTypes.object,
    evidence_quality: PropTypes.string,
  }).isRequired,
  onClick: PropTypes.func,
  sourceLabel: PropTypes.string,
};

ViolationCard.defaultProps = {
  onClick: null,
  sourceLabel: null,
};
