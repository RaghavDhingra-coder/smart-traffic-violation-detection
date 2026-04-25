// TODO for user-dashboard: add persisted sessions, payment verification callbacks, and richer challan filtering.
import { useState } from "react";

import api from "../api/axios";
import ChallanCard from "../components/ChallanCard";
import { useAuth } from "../context/AuthContext";

const defaultFineByType = {
  NO_HELMET: 500,
  TRIPPLING: 1000,
  TRIPLE_RIDING: 1000,
  OVERSPEEDING: 2000,
  TRAFFIC_LIGHT_JUMP: 1000,
  SIGNAL_VIOLATION: 1000,
  NO_NUMBER_PLATE: 5000,
};

export default function UserDashboard() {
  const { vehicleNumber, challans, setChallans, loginWithVehicle, isAuthenticated } = useAuth();
  const [plateInput, setPlateInput] = useState(vehicleNumber);
  const [error, setError] = useState("");
  const [payingId, setPayingId] = useState(null);

  async function handleLogin(event) {
    event.preventDefault();
    try {
      setError("");
      const response = await api.get(`/challan/${plateInput}`);
      loginWithVehicle(plateInput, response.data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to fetch challans for that vehicle.");
    }
  }

  async function handlePay(challan) {
    try {
      setPayingId(challan.id);
      const amount = challan.amount ?? defaultFineByType[(challan.violation_type || "").toUpperCase()] ?? 500;
      const response = await api.post("/payment/create-order", {
        challan_id: challan.id,
        amount,
        currency: "INR",
      });

      const options = {
        key: response.data.key_id,
        amount: amount * 100,
        currency: response.data.currency || "INR",
        name: "Traffic Violation System",
        description: `Payment for challan #${challan.id}`,
        order_id: response.data.razorpay_order_id,
        handler: async function (gatewayResponse) {
          await api.post("/payment/verify", {
            challan_id: challan.id,
            razorpay_order_id: gatewayResponse.razorpay_order_id,
            razorpay_payment_id: gatewayResponse.razorpay_payment_id,
            razorpay_signature: gatewayResponse.razorpay_signature,
          });
          setChallans((prev) => prev.map((item) => (item.id === challan.id ? { ...item, status: "PAID" } : item)));
        },
        theme: {
          color: "#0f172a",
        },
      };

      // STUB: replace with real implementation by loading Razorpay checkout script securely and handling failures.
      if (window.Razorpay) {
        const paymentObject = new window.Razorpay(options);
        paymentObject.open();
      } else {
        alert(`Razorpay checkout stub. Order created: ${response.data.razorpay_order_id}`);
      }
    } catch (paymentError) {
      setError(paymentError.response?.data?.detail || "Payment initialization failed.");
    } finally {
      setPayingId(null);
    }
  }

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] bg-gradient-to-r from-slate-100 via-white to-amber-50 p-6 shadow-panel">
        <p className="text-sm uppercase tracking-[0.28em] text-ember">Citizen Access</p>
        <h1 className="mt-2 font-display text-3xl font-semibold text-ink md:text-4xl">User Dashboard</h1>
        <p className="mt-3 max-w-3xl text-sm text-slate-600 md:text-base">Look up your vehicle by registration number, review challans, and start payment through the Razorpay stub flow.</p>
      </section>

      <section className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
        <form onSubmit={handleLogin} className="rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember">Vehicle Login</p>
          <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Enter vehicle number</h2>
          <input value={plateInput} onChange={(event) => setPlateInput(event.target.value.toUpperCase())} placeholder="KA01AB1234" className="mt-5 w-full rounded-2xl border border-slate-200 px-4 py-3" />
          <button type="submit" className="mt-4 w-full rounded-2xl bg-ink px-5 py-3 font-semibold text-white">Fetch My Challans</button>
          {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
        </form>

        <section className="space-y-4 rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Challan List</p>
              <h2 className="mt-1 font-display text-2xl font-semibold text-ink">{isAuthenticated ? `Vehicle ${vehicleNumber}` : "Waiting for login"}</h2>
            </div>
            <span className="rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-700">{challans.length} record(s)</span>
          </div>

          {challans.length > 0 ? challans.map((challan) => (
            <ChallanCard key={challan.id} challan={challan} onPay={handlePay} loading={payingId === challan.id} />
          )) : <div className="rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-500">No challans to display yet. Enter a vehicle number to begin.</div>}
        </section>
      </section>
    </div>
  );
}
