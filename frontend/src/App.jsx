// TODO for app-shell: replace page toggling with a proper router and role-based entry flow when auth is implemented.
import { useState } from "react";

import Navbar from "./components/Navbar";
import AwareUserDashboard from "./pages/AwareUserDashboard";
import PoliceDashboard from "./pages/PoliceDashboard";
import UserDashboard from "./pages/UserDashboard";

const pageMap = {
  police: <PoliceDashboard />,
  user: <UserDashboard />,
  aware: <AwareUserDashboard />,
};

export default function App() {
  const [currentPage, setCurrentPage] = useState("police");

  return (
    <div className="min-h-screen text-ink">
      <Navbar currentPage={currentPage} onPageChange={setCurrentPage} />
      <main className="mx-auto max-w-7xl px-4 py-6 md:px-6 md:py-8">{pageMap[currentPage]}</main>
    </div>
  );
}
