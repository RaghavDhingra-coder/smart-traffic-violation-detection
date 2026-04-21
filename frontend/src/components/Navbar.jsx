// TODO for navigation: replace local tab state with route-aware navigation when page routing is introduced.
export default function Navbar({ currentPage, onPageChange }) {
  const tabs = [
    { id: "police", label: "Police Dashboard" },
    { id: "user", label: "Citizen Dashboard" },
    { id: "aware", label: "Aware Rider" },
  ];

  return (
    <header className="sticky top-0 z-20 border-b border-white/60 bg-white/80 backdrop-blur-xl">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 md:flex-row md:items-center md:justify-between md:px-6">
        <div>
          <p className="font-display text-2xl font-bold text-ink">Traffic Violation Detection System</p>
          <p className="text-sm text-slate-500">Hackathon scaffold for police, citizens, and self-check flows</p>
        </div>
        <nav className="flex flex-wrap gap-2">
          {tabs.map((tab) => {
            const active = currentPage === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                onClick={() => onPageChange(tab.id)}
                className={`rounded-full px-4 py-2 text-sm font-semibold transition ${
                  active
                    ? "bg-ink text-white shadow-panel"
                    : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                }`}
              >
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
