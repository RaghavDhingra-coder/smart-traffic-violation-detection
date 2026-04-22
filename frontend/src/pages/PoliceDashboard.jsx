import { useMemo, useState } from "react";

const navItems = [
  { label: "Dashboard", icon: "M3 10.5 12 3l9 7.5v9a1.5 1.5 0 0 1-1.5 1.5H15v-6H9v6H4.5A1.5 1.5 0 0 1 3 19.5v-9Z" },
  { label: "Live Monitor", icon: "M4 6h16v10H4V6Zm5 13h6m-3-3v3" },
  { label: "Violations", icon: "M6 3h9l3 3v15H6V3Zm8 0v4h4M9 11h6M9 15h6" },
  { label: "E-Challans", icon: "M7 4h10v16H7V4Zm3 4h4M10 12h4M10 16h2" },
  { label: "Vehicles", icon: "M5 13h14l-1.5-4.5h-11L5 13Zm1 0v4m12-4v4M7 17h2m6 0h2" },
  { label: "Stolen Vehicles", icon: "M12 3 4 6v5c0 5 3.5 8 8 10 4.5-2 8-5 8-10V6l-8-3Zm0 5v5" },
  { label: "Analytics", icon: "M5 19V9m7 10V5m7 14v-7" },
  { label: "Reports", icon: "M6 4h12v16H6V4Zm3 4h6M9 12h6M9 16h4" },
  { label: "Users", icon: "M16 19a4 4 0 0 0-8 0m4-8a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z" },
  { label: "Settings", icon: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-5v3m0 12v3M4.2 4.2l2.1 2.1m11.4 11.4 2.1 2.1M3 12h3m12 0h3M4.2 19.8l2.1-2.1M17.7 6.3l2.1-2.1" },
];

const sampleViolations = [
  { id: 1, time: "08:13 PM", type: "No Helmet", plate: "KA01AB1234", location: "Silk Board", fine: 500, status: "Pending", camera: "Cam 04", owner: "Ravi Kumar", stolen: false },
  { id: 2, time: "08:10 PM", type: "Overspeeding", plate: "KA03EF5678", location: "Outer Ring Road", fine: 1000, status: "Pending", camera: "Cam 11", owner: "Sneha Rao", stolen: false },
  { id: 3, time: "08:08 PM", type: "Red Light Jump", plate: "KA51GH9012", location: "RTO Circle", fine: 1000, status: "Pending", camera: "Cam 07", owner: "Manoj Das", stolen: false },
  { id: 4, time: "08:05 PM", type: "No Parking", plate: "KA02CD3456", location: "Majestic", fine: 500, status: "Generated", camera: "Cam 02", owner: "Asha Nair", stolen: false },
  { id: 5, time: "07:58 PM", type: "No Number Plate", plate: "UNKNOWN", location: "Hebbal Flyover", fine: 5000, status: "Under Review", camera: "Cam 15", owner: "Unverified", stolen: false },
  { id: 6, time: "07:51 PM", type: "Triple Riding", plate: "KA05MN7788", location: "BTM Layout", fine: 1000, status: "Pending", camera: "Cam 08", owner: "Iqbal Khan", stolen: false },
  { id: 7, time: "07:44 PM", type: "Overspeeding", plate: "KA41PQ4481", location: "Electronic City", fine: 1000, status: "Paid", camera: "Cam 21", owner: "Nisha Patel", stolen: false },
  { id: 8, time: "07:39 PM", type: "Stolen Vehicle", plate: "KA09ST2026", location: "Marathahalli", fine: 0, status: "Alerted", camera: "Cam 17", owner: "Police Alert", stolen: true },
  { id: 9, time: "07:31 PM", type: "No Helmet", plate: "KA04UV3344", location: "Indiranagar", fine: 500, status: "Generated", camera: "Cam 05", owner: "Dev Singh", stolen: false },
  { id: 10, time: "07:20 PM", type: "Red Light Jump", plate: "KA22WX9011", location: "Koramangala", fine: 1000, status: "Pending", camera: "Cam 12", owner: "Meera Iyer", stolen: false },
  { id: 11, time: "07:12 PM", type: "Stolen Vehicle", plate: "KA18ZZ1001", location: "Jayanagar", fine: 0, status: "Alerted", camera: "Cam 20", owner: "Police Alert", stolen: true },
  { id: 12, time: "07:05 PM", type: "No Parking", plate: "KA06JK6060", location: "MG Road", fine: 500, status: "Paid", camera: "Cam 04", owner: "Arun Menon", stolen: false },
  { id: 13, time: "06:55 PM", type: "Overspeeding", plate: "KA53LM4545", location: "Airport Road", fine: 1000, status: "Generated", camera: "Cam 19", owner: "Pooja Shah", stolen: false },
  { id: 14, time: "06:47 PM", type: "No Helmet", plate: "KA01BC2200", location: "Whitefield", fine: 500, status: "Pending", camera: "Cam 14", owner: "Kiran Gowda", stolen: false },
  { id: 15, time: "06:41 PM", type: "No Number Plate", plate: "UNKNOWN-2", location: "Yeshwanthpur", fine: 5000, status: "Under Review", camera: "Cam 10", owner: "Unverified", stolen: false },
  { id: 16, time: "06:34 PM", type: "Triple Riding", plate: "KA07RT7732", location: "K R Puram", fine: 1000, status: "Generated", camera: "Cam 09", owner: "Farah Ali", stolen: false },
];

const timeRanges = ["Today", "This Week", "This Month"];
const mapLabels = ["Marathahalli", "Silk Board", "Majestic", "K R Puram", "Jayanagar"];

function Icon({ path, className = "" }) {
  return (
    <svg className={className} viewBox="0 0 24 24" aria-hidden="true" fill="none">
      <path d={path} stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function StatCard({ metric }) {
  const colors = {
    violet: "from-[#1b172a] to-[#141520] text-[#a98dff]",
    blue: "from-[#111b2c] to-[#121820] text-[#5f9dff]",
    green: "from-[#121e1d] to-[#11191b] text-[#86d899]",
    red: "from-[#20161c] to-[#17161b] text-[#ff7777]",
  };

  return (
    <article className={`rounded-lg border border-white/5 bg-gradient-to-br ${colors[metric.tone]} px-6 py-5 shadow-[0_18px_45px_rgba(0,0,0,0.2)]`}>
      <p className="text-[11px] font-bold">{metric.title}</p>
      <p className="mt-3 text-3xl font-extrabold tracking-normal text-slate-100">{metric.value}</p>
      <p className={`mt-3 text-[11px] font-bold ${metric.tone === "green" ? "text-emerald-400" : metric.tone === "red" ? "text-red-400" : "text-[#719dff]"}`}>
        {metric.change}
      </p>
    </article>
  );
}

function LiveMonitor({ activeRecord }) {
  return (
    <section className="rounded-lg border border-emerald-400/20 bg-[#111820] p-5 shadow-[0_18px_45px_rgba(0,0,0,0.22)]">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-100">Live Monitor</h2>
        <span className="rounded bg-red-500 px-2 py-1 text-[10px] font-extrabold text-white">LIVE</span>
      </div>
      <div className="traffic-scene mt-3 aspect-[16/7] overflow-hidden rounded-md bg-[#1a2027]">
        <div className="scene-caption">{activeRecord.camera} - {activeRecord.location}</div>
        <div className="road-lane lane-one" />
        <div className="road-lane lane-two" />
        <div className="road-lane lane-three" />
        <div className="vehicle-box alert-car"><span>{activeRecord.plate}</span></div>
        <div className="vehicle-box bus"><span>BUS</span></div>
        <div className="vehicle-box white-car"><span>KA01AB</span></div>
        <div className="vehicle-box bike"><span>BIKE</span></div>
      </div>
    </section>
  );
}

function DistributionChart({ distribution, total, timeRange, onRangeChange }) {
  const gradient = useMemo(() => {
    let current = 0;
    const stops = distribution.map((item) => {
      const next = current + item.value;
      const stop = `${item.color} ${current}% ${next}%`;
      current = next;
      return stop;
    });
    return `conic-gradient(${stops.join(", ")})`;
  }, [distribution]);

  return (
    <section className="rounded-lg border border-emerald-400/20 bg-[#111820] p-5 shadow-[0_18px_45px_rgba(0,0,0,0.22)]">
      <div className="mb-5 flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-100">Violation Distribution</h2>
        <button className="rounded-md border border-white/10 bg-[#151b25] px-3 py-1.5 text-[11px] font-bold text-slate-300" type="button" onClick={onRangeChange}>
          {timeRange}
        </button>
      </div>
      <div className="grid items-center gap-7 md:grid-cols-[0.8fr_1fr]">
        <div className="mx-auto grid h-40 w-40 place-items-center rounded-full" style={{ background: gradient }}>
          <div className="grid h-24 w-24 place-items-center rounded-full bg-[#111820] text-center">
            <p className="text-2xl font-extrabold text-slate-100">{total}</p>
            <p className="text-xs font-bold text-slate-500">Sample</p>
          </div>
        </div>
        <div className="space-y-3">
          {distribution.map((item) => (
            <button
              className="grid w-full grid-cols-[1rem_1fr_2.5rem] items-center gap-2 text-left text-xs font-bold"
              key={item.label}
              type="button"
              onClick={item.onClick}
            >
              <span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: item.color }} />
              <span className="text-slate-300">{item.label}</span>
              <span className="text-right text-slate-400">{item.value}%</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

function RecentViolations({ records, showAll, onToggleShowAll, onStatusChange }) {
  return (
    <section className="rounded-lg border border-emerald-400/20 bg-[#111820] p-5 shadow-[0_18px_45px_rgba(0,0,0,0.22)]">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-bold text-slate-100">Recent Violations</h2>
        <span className="rounded-md bg-white/5 px-3 py-1 text-xs font-bold text-slate-400">{records.length} records</span>
      </div>
      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[780px] text-left text-xs font-bold">
          <thead className="text-[11px] text-slate-500">
            <tr>
              <th className="pb-4">Time</th>
              <th className="pb-4">Type</th>
              <th className="pb-4">Vehicle No.</th>
              <th className="pb-4">Location</th>
              <th className="pb-4">Fine</th>
              <th className="pb-4">Status</th>
              <th className="pb-4">Action</th>
            </tr>
          </thead>
          <tbody>
            {records.map((violation) => (
              <tr className="border-t border-white/5 text-slate-300" key={violation.id}>
                <td className="py-2.5 text-slate-400">{violation.time}</td>
                <td className="py-2.5">{violation.type}</td>
                <td className="py-2.5 text-[#6f8cff]">{violation.plate}</td>
                <td className="py-2.5 text-slate-400">{violation.location}</td>
                <td className="py-2.5 text-slate-300">{violation.fine ? `Rs. ${violation.fine}` : "Alert"}</td>
                <td className="py-2.5">
                  <span className={`rounded-full px-3 py-1 text-[11px] ${violation.status === "Paid" ? "bg-emerald-500/10 text-emerald-300" : violation.status === "Alerted" ? "bg-red-500/10 text-red-300" : "bg-[#5f4214] text-[#ffb331]"}`}>
                    {violation.status}
                  </span>
                </td>
                <td className="py-2.5">
                  <button
                    className="rounded-md border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] font-extrabold text-slate-200 transition hover:bg-emerald-500/20"
                    type="button"
                    onClick={() => onStatusChange(violation.id, violation.stolen ? "Alerted" : violation.status === "Paid" ? "Pending" : "Paid")}
                  >
                    {violation.stolen ? "Notify" : violation.status === "Paid" ? "Reopen" : "Mark Paid"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <button className="mx-auto mt-4 block text-xs font-extrabold text-[#6f8cff]" type="button" onClick={onToggleShowAll}>
        {showAll ? "Show recent only" : "View all violations +"}
      </button>
    </section>
  );
}

function HotspotMap({ timeRange, onRangeChange }) {
  return (
    <section className="rounded-lg border border-emerald-400/20 bg-[#111820] p-5 shadow-[0_18px_45px_rgba(0,0,0,0.22)]">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-bold text-slate-100">Violation Hotspots</h2>
        <button className="rounded-md border border-white/10 bg-[#151b25] px-3 py-1.5 text-[11px] font-bold text-slate-300" type="button" onClick={onRangeChange}>
          {timeRange}
        </button>
      </div>
      <div className="city-map mt-4 h-48 overflow-hidden rounded-md bg-[#0d141b]">
        {mapLabels.map((label, index) => (
          <span className={`map-label label-${index + 1}`} key={label}>{label}</span>
        ))}
        <span className="hotspot hot-1" />
        <span className="hotspot hot-2" />
        <span className="hotspot hot-3" />
        <span className="hotspot hot-4" />
      </div>
    </section>
  );
}

export default function PoliceDashboard({ user, onLogout }) {
  const [records, setRecords] = useState(sampleViolations);
  const [activeSection, setActiveSection] = useState("Dashboard");
  const [searchTerm, setSearchTerm] = useState("");
  const [typeFilter, setTypeFilter] = useState("All");
  const [showAll, setShowAll] = useState(false);
  const [timeRangeIndex, setTimeRangeIndex] = useState(0);

  const timeRange = timeRanges[timeRangeIndex];
  const uniqueTypes = useMemo(() => ["All", ...new Set(records.map((record) => record.type))], [records]);

  const sectionRecords = useMemo(() => {
    if (activeSection === "Stolen Vehicles") return records.filter((record) => record.stolen);
    if (activeSection === "E-Challans") return records.filter((record) => record.fine > 0);
    return records;
  }, [activeSection, records]);

  const filteredRecords = useMemo(() => {
    return sectionRecords.filter((record) => {
      const matchesType = typeFilter === "All" || record.type === typeFilter;
      const query = searchTerm.trim().toLowerCase();
      const matchesSearch = !query || [record.plate, record.type, record.location, record.owner, record.camera].some((value) => value.toLowerCase().includes(query));
      return matchesType && matchesSearch;
    });
  }, [sectionRecords, searchTerm, typeFilter]);

  const visibleRecords = showAll ? filteredRecords : filteredRecords.slice(0, 6);
  const activeRecord = visibleRecords[0] || records[0];
  const challanCount = records.filter((record) => record.fine > 0 && record.status !== "Under Review").length;
  const paidCount = records.filter((record) => record.status === "Paid").length;
  const alertCount = records.filter((record) => record.stolen).length;

  const metrics = [
    { title: "Total Violations", value: records.length.toString(), change: `${filteredRecords.length} shown in ${activeSection}`, tone: "violet" },
    { title: "E-Challans Generated", value: challanCount.toString(), change: `${paidCount} marked paid`, tone: "blue" },
    { title: "Active Cameras", value: "24", change: "Online", tone: "green" },
    { title: "Stolen Vehicles Alert", value: alertCount.toString(), change: "+ New Alerts", tone: "red" },
  ];

  const distribution = useMemo(() => {
    const colors = ["#7565ff", "#ffb331", "#46c778", "#4e9cff", "#8a78d8", "#97a782", "#ff6969"];
    const counts = records.reduce((acc, record) => {
      acc[record.type] = (acc[record.type] || 0) + 1;
      return acc;
    }, {});
    return Object.entries(counts).map(([label, count], index) => ({
      label,
      value: Math.round((count / records.length) * 100),
      color: colors[index % colors.length],
      onClick: () => setTypeFilter(label),
    }));
  }, [records]);

  function cycleTimeRange() {
    setTimeRangeIndex((current) => (current + 1) % timeRanges.length);
  }

  function handleNavClick(label) {
    setActiveSection(label);
    setShowAll(label !== "Dashboard");
    if (label === "Stolen Vehicles") {
      setTypeFilter("Stolen Vehicle");
    } else {
      setTypeFilter("All");
    }
  }

  function handleStatusChange(id, status) {
    setRecords((current) => current.map((record) => record.id === id ? { ...record, status } : record));
  }

  return (
    <div className="min-h-screen bg-[#080c12] text-slate-100">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-60 border-r border-white/5 bg-[#0b1017] px-5 py-7 lg:flex lg:flex-col">
        <div className="flex items-center gap-3">
          <div className="grid h-9 w-9 place-items-center rounded-md bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-400/30">
            <Icon className="h-5 w-5" path="M5 12h14M12 5v14M7 7h10v10H7V7Z" />
          </div>
          <div>
            <p className="text-sm font-extrabold text-white">Traffic Sentinel</p>
            <p className="text-[11px] font-bold text-slate-500">Smart Traffic Enforcement</p>
          </div>
        </div>

        <nav className="mt-10 space-y-2">
          {navItems.map((item) => {
            const active = item.label === activeSection;
            return (
              <button
                className={`flex w-full items-center gap-3 rounded-md px-4 py-3 text-left text-sm font-extrabold transition ${
                  active ? "bg-emerald-500 text-white" : "text-slate-400 hover:bg-white/5 hover:text-slate-100"
                }`}
                key={item.label}
                type="button"
                onClick={() => handleNavClick(item.label)}
              >
                <Icon className="h-4 w-4" path={item.icon} />
                {item.label}
              </button>
            );
          })}
        </nav>

        <div className="mt-auto border-t border-white/5 pt-6">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-full bg-[linear-gradient(135deg,#96e6a1,#4c8f68_55%,#2a3440)] text-sm font-extrabold text-white">
              {user?.name?.slice(0, 1) || "K"}
            </div>
            <div>
              <p className="text-sm font-extrabold text-slate-100">{user?.name || "Kabir Ahmed"}</p>
              <p className="text-xs font-bold text-slate-500">{user?.role || "Admin"}</p>
            </div>
          </div>
          <button className="mt-4 w-full rounded-md border border-white/10 px-3 py-2 text-xs font-extrabold text-slate-400 transition hover:bg-white/5 hover:text-white" type="button" onClick={onLogout}>
            Logout
          </button>
        </div>
      </aside>

      <main className="lg:pl-60">
        <div className="mx-auto max-w-[1180px] px-4 py-5 sm:px-6 lg:px-9">
          <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h1 className="text-3xl font-extrabold tracking-normal text-slate-100">{activeSection}</h1>
              <p className="mt-1 text-sm font-bold text-slate-500">Logged in with {user?.provider || "Demo credentials"} as {user?.email}</p>
            </div>
            <button className="inline-flex w-fit items-center gap-2 rounded-md border border-white/10 bg-[#111820] px-4 py-2.5 text-sm font-extrabold text-slate-300" type="button" onClick={cycleTimeRange}>
              <Icon className="h-4 w-4" path="M7 3v3m10-3v3M4 9h16M5 5h14v15H5V5Z" />
              {timeRange}
            </button>
          </header>

          <section className="mt-6 grid gap-3 lg:grid-cols-[1fr_15rem]">
            <input
              className="rounded-lg border border-white/10 bg-[#111820] px-4 py-3 text-sm font-bold text-white outline-none placeholder:text-slate-600 focus:border-emerald-400"
              value={searchTerm}
              onChange={(event) => setSearchTerm(event.target.value)}
              placeholder="Search plate, location, owner, camera..."
            />
            <select
              className="rounded-lg border border-white/10 bg-[#111820] px-4 py-3 text-sm font-bold text-white outline-none focus:border-emerald-400"
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
            >
              {uniqueTypes.map((type) => <option key={type} value={type}>{type}</option>)}
            </select>
          </section>

          <section className="mt-5 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {metrics.map((metric) => <StatCard key={metric.title} metric={metric} />)}
          </section>

          <section className="mt-5 grid gap-5 xl:grid-cols-[1.05fr_1fr]">
            <LiveMonitor activeRecord={activeRecord} />
            <DistributionChart distribution={distribution} total={records.length} timeRange={timeRange} onRangeChange={cycleTimeRange} />
          </section>

          <section className="mt-5 grid gap-5 xl:grid-cols-[1.4fr_0.7fr]">
            <RecentViolations
              records={visibleRecords}
              showAll={showAll}
              onToggleShowAll={() => setShowAll((current) => !current)}
              onStatusChange={handleStatusChange}
            />
            <HotspotMap timeRange={timeRange} onRangeChange={cycleTimeRange} />
          </section>
        </div>
      </main>
    </div>
  );
}
