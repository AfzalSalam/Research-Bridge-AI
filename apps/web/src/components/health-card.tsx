import type { HealthResult } from "@/lib/api/health";

interface HealthCardProps {
  result: HealthResult;
}

export function HealthCard({ result }: HealthCardProps) {
  const isAvailable = result.state === "available";

  return (
    <section className="health-card" aria-labelledby="system-status-title">
      <div className="status-heading">
        <div>
          <p className="eyebrow">Foundation check</p>
          <h2 id="system-status-title">System boundary</h2>
        </div>
        <p
          className="status-badge"
          data-state={isAvailable ? "available" : "unavailable"}
          role="status"
        >
          <span aria-hidden="true" />
          {isAvailable ? "API available" : "API unavailable"}
        </p>
      </div>

      {isAvailable ? (
        <dl className="health-details">
          <div>
            <dt>Service</dt>
            <dd>{result.data.service}</dd>
          </div>
          <div>
            <dt>Version</dt>
            <dd>{result.data.version}</dd>
          </div>
          <div>
            <dt>Environment</dt>
            <dd>{result.data.environment}</dd>
          </div>
        </dl>
      ) : (
        <p className="health-message">{result.message}</p>
      )}
    </section>
  );
}
