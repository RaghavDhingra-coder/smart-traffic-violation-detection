// TODO for frontend-theme: evolve the design tokens into a stronger brand system and responsive component scale.
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0f172a",
        ember: "#dc2626",
        asphalt: "#1f2937",
        signal: "#f59e0b",
        mint: "#10b981",
        fog: "#e2e8f0"
      },
      boxShadow: {
        panel: "0 20px 45px rgba(15, 23, 42, 0.12)"
      },
      backgroundImage: {
        "road-grid": "radial-gradient(circle at 1px 1px, rgba(15, 23, 42, 0.08) 1px, transparent 0)"
      },
      fontFamily: {
        display: ["Poppins", "sans-serif"],
        body: ["Manrope", "sans-serif"]
      }
    }
  },
  plugins: []
};
