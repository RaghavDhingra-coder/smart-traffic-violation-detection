// TODO for file-upload: add drag-and-drop, upload cancellation, and video preview support for larger inputs.
import { useState } from "react";

import api from "../api/axios";
import ViolationCard from "./ViolationCard";

export default function FileUpload({ onViolationsDetected }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [violations, setViolations] = useState([]);
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState("");

  async function handleFileChange(event) {
    const file = event.target.files?.[0];
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      setUploading(true);
      setError("");
      setProgress(0);
      const response = await api.post("/detect/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (progressEvent) => {
          const total = progressEvent.total || 1;
          setProgress(Math.round((progressEvent.loaded / total) * 100));
        },
      });
      const receivedViolations = response.data.violations || [];
      setViolations(receivedViolations);
      setMeta({ totalFramesProcessed: response.data.total_frames_processed || 0, fileName: file.name });
      if (onViolationsDetected) {
        onViolationsDetected(response.data);
      }
    } catch (uploadError) {
      setError(uploadError.response?.data?.detail || "Upload failed.");
    } finally {
      setUploading(false);
    }
  }

  return (
    <section className="space-y-5 rounded-[2rem] border border-white/70 bg-white p-6 shadow-panel">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.24em] text-ember">Upload Analysis</p>
        <h2 className="mt-1 font-display text-2xl font-semibold text-ink">Check an Image or Video</h2>
      </div>

      <label className="flex cursor-pointer flex-col items-center justify-center rounded-[1.75rem] border border-dashed border-slate-300 bg-slate-50 px-6 py-10 text-center transition hover:border-amber-400 hover:bg-amber-50/50">
        <span className="font-semibold text-slate-700">Choose an image or video</span>
        <span className="mt-2 text-sm text-slate-500">Accepts image and video files for violation analysis.</span>
        <input type="file" accept="image/*,video/*" onChange={handleFileChange} className="hidden" />
      </label>

      {uploading ? (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm font-semibold text-slate-600">
            <span>Uploading and processing</span>
            <span>{progress}%</span>
          </div>
          <div className="h-3 overflow-hidden rounded-full bg-slate-200">
            <div className="h-full rounded-full bg-gradient-to-r from-amber-400 to-red-600" style={{ width: `${progress}%` }} />
          </div>
        </div>
      ) : null}

      {meta ? (
        <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
          <p>
            <span className="font-semibold text-slate-900">File:</span> {meta.fileName}
          </p>
          <p>
            <span className="font-semibold text-slate-900">Frames processed:</span> {meta.totalFramesProcessed}
          </p>
        </div>
      ) : null}

      {error ? <p className="rounded-2xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p> : null}

      {violations.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          {violations.map((violation, index) => (
            <ViolationCard
              key={`${violation.type}-${index}`}
              violation={{ ...violation, sourceLabel: "File upload" }}
            />
          ))}
        </div>
      ) : null}
    </section>
  );
}
