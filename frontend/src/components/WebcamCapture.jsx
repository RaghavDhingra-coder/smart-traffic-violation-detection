// TODO for webcam-capture: add camera selection, smarter polling, and debounce logic for live deployments.
import { useEffect, useRef, useState } from "react";

import api from "../api/axios";
import ViolationCard from "./ViolationCard";

export default function WebcamCapture({ onViolationDetected }) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const intervalRef = useRef(null);
  const streamRef = useRef(null);
  const busyRef = useRef(false);
  const [loading, setLoading] = useState(false);
  const [latestViolations, setLatestViolations] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function setupCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true });
        if (!active) return;
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          await videoRef.current.play();
        }

        intervalRef.current = window.setInterval(async () => {
          if (busyRef.current || !videoRef.current || !canvasRef.current) {
            return;
          }

          const video = videoRef.current;
          const canvas = canvasRef.current;
          if (!video.videoWidth || !video.videoHeight) {
            return;
          }

          canvas.width = video.videoWidth;
          canvas.height = video.videoHeight;
          const context = canvas.getContext("2d");
          context.drawImage(video, 0, 0, canvas.width, canvas.height);

          try {
            busyRef.current = true;
            setLoading(true);
            setError("");
            const frame = canvas.toDataURL("image/jpeg", 0.8);
            const response = await api.post("/detect", { frame, source: "webcam" });
            const violations = response.data.violations || [];
            setLatestViolations(violations);
            if (violations.length > 0 && onViolationDetected) {
              onViolationDetected({
                violations,
                timestamp: new Date().toISOString(),
              });
            }
          } catch (requestError) {
            setError(requestError.response?.data?.detail || "Failed to analyze webcam frame.");
          } finally {
            busyRef.current = false;
            setLoading(false);
          }
        }, 500);
      } catch (cameraError) {
        setError(cameraError.message || "Unable to access webcam.");
      }
    }

    setupCamera();

    return () => {
      active = false;
      if (intervalRef.current) {
        window.clearInterval(intervalRef.current);
      }
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop());
      }
    };
  }, [onViolationDetected]);

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="rounded-[2rem] border border-white/70 bg-white p-5 shadow-panel">
        <div className="mb-4 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember">Live Stream</p>
            <h2 className="font-display text-2xl font-semibold text-ink">Webcam Detection</h2>
          </div>
          <div className="relative spinner-ring flex items-center gap-2 rounded-full bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-700">
            <span className={`h-2.5 w-2.5 rounded-full ${loading ? "bg-amber-500" : "bg-mint"}`} />
            {loading ? "Analyzing" : "Camera ready"}
          </div>
        </div>
        <div className="overflow-hidden rounded-[1.5rem] bg-slate-950">
          <video ref={videoRef} className="aspect-video w-full object-cover" muted playsInline />
        </div>
        <canvas ref={canvasRef} className="hidden" />
        {error ? <p className="mt-4 rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}
      </section>

      <section className="space-y-4">
        <div className="rounded-[2rem] border border-white/70 bg-white p-5 shadow-panel">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-500">Result Feed</p>
          <h3 className="mt-1 font-display text-xl font-semibold text-ink">Latest Violations</h3>
        </div>
        {latestViolations.length > 0 ? (
          latestViolations.map((violation, index) => (
            <ViolationCard
              key={`${violation.type}-${index}`}
              violation={{ ...violation, sourceLabel: "Webcam" }}
            />
          ))
        ) : (
          <div className="rounded-[2rem] border border-dashed border-slate-300 bg-white/80 p-8 text-center text-slate-500 shadow-panel">
            Waiting for violation detections from the live feed.
          </div>
        )}
      </section>
    </div>
  );
}
