// TODO for challan-card: connect payment verification and richer payment states after Razorpay integration is completed.
export default function ChallanCard({ challan, onPay, loading }) {
  return (
    <article className="rounded-3xl border border-white/70 bg-white p-5 shadow-panel">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Challan #{challan.id}</p>
          <h3 className="font-display text-xl font-semibold capitalize text-ink">{challan.violation_type.replaceAll("_", " ")}</h3>
          <p className="text-sm text-slate-600">Plate: <span className="font-semibold text-slate-900">{challan.plate}</span></p>
          <p className="text-sm text-slate-600">Amount: <span className="font-semibold text-ember">?{challan.amount}</span></p>
          <p className="text-sm text-slate-600">Status: <span className="font-semibold capitalize text-slate-900">{challan.status}</span></p>
          <p className="text-sm text-slate-500">Issued: {new Date(challan.timestamp).toLocaleString()}</p>
        </div>
        <button
          type="button"
          onClick={() => onPay(challan)}
          disabled={loading || challan.status === "paid"}
          className="rounded-2xl bg-ink px-5 py-3 font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {challan.status === "paid" ? "Paid" : loading ? "Opening gateway..." : "Pay Now"}
        </button>
      </div>
    </article>
  );
}
