import Link from "next/link";

import { HealthCard } from "@/components/health-card";
import { getApiHealth } from "@/lib/api/health";

export const dynamic = "force-dynamic";

export default async function Home() {
  const health = await getApiHealth();

  return (
    <main>
      <header className="site-header">
        <Link className="brand" href="/" aria-label="Research Bridge AI home">
          <span className="brand-mark" aria-hidden="true">
            RB
          </span>
          <span>Research Bridge AI</span>
        </Link>
        <p>Phase 1 · Foundation</p>
      </header>

      <div className="page-shell" id="main-content">
        <section className="intro" aria-labelledby="page-title">
          <p className="eyebrow">Evidence-first academic discovery</p>
          <h1 id="page-title">
            A trustworthy bridge from research interest to informed outreach.
          </h1>
          <p className="lede">
            The product journey arrives in later phases. This page proves the
            typed boundary between the Next.js frontend and FastAPI backend.
          </p>
        </section>

        <HealthCard result={health} />
      </div>
    </main>
  );
}
