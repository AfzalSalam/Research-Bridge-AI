export function normalizeCitationDoi(value: string | null): string | null {
  if (!value) return null;
  const doi = value.trim().replace(/^https?:\/\/(?:dx\.)?doi\.org\//i, "").replace(/^doi:\s*/i, "").toLowerCase();
  return /^10\.\d{4,9}\/[^\s?#]+$/.test(doi) ? doi : null;
}

export function citationIdentifier(doi: string | null, publicationUrl?: string): { doi: string; arxiv: boolean } | null {
  const normalized = normalizeCitationDoi(doi);
  if (normalized) return { doi: normalized, arxiv: normalized.startsWith("10.48550/arxiv.") };
  if (!publicationUrl) return null;
  let url: URL;
  try { url = new URL(publicationUrl); } catch { return null; }
  if (!["https:", "http:"].includes(url.protocol) || !["arxiv.org", "www.arxiv.org"].includes(url.hostname) || url.username || url.password || url.port) return null;
  const match = url.pathname.match(/^\/(?:abs|pdf)\/(\d{4}\.\d{4,5}|[a-z-]+(?:\.[A-Za-z]{2})?\/\d{7})(?:v[1-9]\d*)?(?:\.pdf)?$/);
  if (!match) return null;
  return { doi: `10.48550/arxiv.${match[1].toLowerCase()}`, arxiv: true };
}
