// TODO for auth-context: replace plate-only session state with real authentication and persisted identity management.
import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [vehicleNumber, setVehicleNumber] = useState("");
  const [challans, setChallans] = useState([]);

  const loginWithVehicle = (plate, challanList = []) => {
    setVehicleNumber(plate.toUpperCase());
    setChallans(challanList);
  };

  const logout = () => {
    setVehicleNumber("");
    setChallans([]);
  };

  const value = useMemo(
    () => ({
      vehicleNumber,
      challans,
      setChallans,
      loginWithVehicle,
      logout,
      isAuthenticated: Boolean(vehicleNumber),
    }),
    [vehicleNumber, challans]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return context;
}
