import { scanSnapshotSchema, type ScanSnapshot, type UniversityForm } from "@/features/discovery/university-contracts";
import { getAccessToken } from "@/lib/api/setup";

export async function scanUniversityWebsites(
  form: UniversityForm,
  signal: AbortSignal,
  onSnapshot: (snapshot: ScanSnapshot) => void,
): Promise<void> {
  const token = await getAccessToken();
  if (!token) throw new Error("Sign in to scan university websites.");
  const response = await fetch("/backend/api/v1/discovery/universities/scan", {
    method: "POST", signal,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({ ...form, target: Number(form.target) }),
  });
  if (!response.ok || !response.body) {
    throw new Error(response.status === 429
      ? "A scan is already running. Wait or cancel it before trying again."
      : `Unable to start the university scan (HTTP ${response.status}).`);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  try {
    while (true) {
      const { value, done } = await reader.read();
      if (signal.aborted) return;
      if (done) throw new Error("The scan connection ended early. Results already found remain below.");
      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split(/\r?\n\r?\n/);
      buffer = frames.pop() ?? "";
      if (buffer.length > 2_000_000) throw new Error("Scan response exceeded its size limit.");
      for (const frame of frames) {
        const data = frame.split(/\r?\n/).filter((line) => line.startsWith("data:")).map((line) => line.slice(5).trim()).join("\n");
        if (!data) continue;
        const snapshot = scanSnapshotSchema.parse(JSON.parse(data));
        if (snapshot.state === "error") throw new Error(snapshot.warnings[0] ?? "The scan failed.");
        onSnapshot(snapshot);
        if (snapshot.state !== "scanning") return;
      }
    }
  } finally {
    await reader.cancel();
    reader.releaseLock();
  }
}
