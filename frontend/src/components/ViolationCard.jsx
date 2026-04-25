// TODO for violation-card: expand evidence presentation with timestamps, bounding boxes, and action shortcuts.
export default function ViolationCard({ violation }) {
  const imageSrc = violation.annotated_frame_base64
    ? `data:image/jpeg;base64,${violation.annotated_frame_base64}`
    : null;
  const violationType = violation.type || violation.violation_type || "UNKNOWN";
  const plate = violation.plate || violation.plate_number || "Unknown";
  const confidence = typeof violation.confidence === "number" ? `${(violation.confidence * 100).toFixed(0)}%` : null;

  return (
    <article className="animate-slide-up overflow-hidden rounded-3xl border border-white/70 bg-white shadow-panel">
      {imageSrc ? (
        <img src={imageSrc} alt={violation.type} className="h-48 w-full object-cover" />
      ) : (
        <div className="flex h-48 items-center justify-center bg-slate-200 text-slate-500">No annotated frame</div>
      )}
      <div className="space-y-3 p-5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.25em] text-ember">Violation</p>
            <h3 className="font-display text-xl font-semibold capitalize text-ink">{violationType.replaceAll("_", " ")}</h3>
          </div>
          {confidence ? (
            <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-bold text-amber-700">{confidence}</span>
          ) : null}
        </div>
        <div className="grid gap-2 text-sm text-slate-600">
          <p>
            <span className="font-semibold text-slate-900">Plate:</span> {plate}
          </p>
          {violation.track_id !== undefined && violation.track_id !== null ? <p><span className="font-semibold text-slate-900">Track ID:</span> {violation.track_id}</p> : null}
          {violation.sourceLabel ? (
            <p>
              <span className="font-semibold text-slate-900">Source:</span> {violation.sourceLabel}
            </p>
          ) : null}
        </div>
      </div>
    </article>
  );
}
