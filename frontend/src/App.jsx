import { useEffect, useState } from "react";

import PoliceDashboard from "./pages/PoliceDashboard";

const demoOfficer = {
  name: "Kabir Ahmed",
  email: "kabir.ahmed@traffic.gov",
  role: "Admin",
};

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState("kabir.ahmed@traffic.gov");
  const [password, setPassword] = useState("demo1234");
  const [error, setError] = useState("");

  function handleGoogleLogin() {
    onLogin({ ...demoOfficer, provider: "Google" });
  }

  function handleSubmit(event) {
    event.preventDefault();
    if (!email.trim() || !password.trim()) {
      setError("Enter officer email and password to continue.");
      return;
    }
    setError("");
    onLogin({
      ...demoOfficer,
      email,
      provider: "Demo credentials",
    });
  }

  return (
    <main className="grid min-h-screen place-items-center bg-[#080c12] px-4 py-8 text-slate-100">
      <section className="login-shell grid w-full max-w-5xl overflow-hidden rounded-xl border border-white/10 bg-[#0d131b] shadow-[0_24px_80px_rgba(0,0,0,0.42)] lg:grid-cols-[1.05fr_0.95fr]">
        <div className="relative min-h-[360px] overflow-hidden bg-[#101720] p-8 sm:p-10">
          <div className="relative z-10">
            <div className="grid h-12 w-12 place-items-center rounded-lg bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-400/30">
              <svg className="h-7 w-7" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M5 12h14M12 5v14M7 7h10v10H7V7Z" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            </div>
            <p className="mt-8 text-sm font-extrabold uppercase tracking-[0.24em] text-emerald-300">Traffic Sentinel</p>
            <h1 className="mt-3 max-w-md text-4xl font-extrabold leading-tight tracking-normal text-white sm:text-5xl">
              Smart traffic control room login
            </h1>
            <p className="mt-4 max-w-md text-sm font-semibold leading-6 text-slate-400">
              Sign in to inspect live violations, challans, camera health, and alert data from the sample enforcement dataset.
            </p>
          </div>
          <div className="login-road" />
        </div>

        <form className="bg-[#0b1017] p-8 sm:p-10" onSubmit={handleSubmit}>
          <h2 className="text-2xl font-extrabold text-white">Login</h2>
          <p className="mt-2 text-sm font-semibold text-slate-500">Use Google or the demo officer credentials.</p>

          <button
            className="mt-7 flex w-full items-center justify-center gap-3 rounded-lg border border-white/10 bg-white px-4 py-3 text-sm font-extrabold text-slate-900 transition hover:bg-slate-100"
            type="button"
            onClick={handleGoogleLogin}
          >
            <span className="grid h-6 w-6 place-items-center rounded-full border border-slate-200 text-base font-black text-[#4285f4]">G</span>
            Continue with Google
          </button>

          <div className="my-7 flex items-center gap-3 text-xs font-bold uppercase tracking-[0.18em] text-slate-600">
            <span className="h-px flex-1 bg-white/10" />
            or
            <span className="h-px flex-1 bg-white/10" />
          </div>

          <label className="block text-xs font-extrabold text-slate-400" htmlFor="email">Officer Email</label>
          <input
            id="email"
            className="mt-2 w-full rounded-lg border border-white/10 bg-[#111820] px-4 py-3 text-sm font-bold text-white outline-none transition placeholder:text-slate-600 focus:border-emerald-400"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="officer@traffic.gov"
            type="email"
          />

          <label className="mt-5 block text-xs font-extrabold text-slate-400" htmlFor="password">Password</label>
          <input
            id="password"
            className="mt-2 w-full rounded-lg border border-white/10 bg-[#111820] px-4 py-3 text-sm font-bold text-white outline-none transition placeholder:text-slate-600 focus:border-emerald-400"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="demo1234"
            type="password"
          />

          {error ? <p className="mt-4 rounded-lg bg-red-500/10 px-4 py-3 text-sm font-bold text-red-300">{error}</p> : null}

          <button className="mt-6 w-full rounded-lg bg-emerald-500 px-4 py-3 text-sm font-extrabold text-white transition hover:bg-emerald-400" type="submit">
            Login to Dashboard
          </button>
        </form>
      </section>
    </main>
  );
}

export default function App() {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const savedUser = window.localStorage.getItem("trafficSentinelUser");
    if (savedUser) {
      setUser(JSON.parse(savedUser));
    }
  }, []);

  function handleLogin(nextUser) {
    window.localStorage.setItem("trafficSentinelUser", JSON.stringify(nextUser));
    setUser(nextUser);
  }

  function handleLogout() {
    window.localStorage.removeItem("trafficSentinelUser");
    setUser(null);
  }

  return user ? <PoliceDashboard user={user} onLogout={handleLogout} /> : <LoginPage onLogin={handleLogin} />;
}
