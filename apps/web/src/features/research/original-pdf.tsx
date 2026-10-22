"use client";

import { useEffect, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { readOriginalPdf } from "@/lib/api/documents";

export function OriginalPdf({ id, page = 1 }: { id: string; page?: number }) {
 const frame = useRef<HTMLIFrameElement>(null);
 const download = useRef<HTMLAnchorElement>(null);
 const query = useQuery({
  queryKey: ["original-pdf", id],
  queryFn: ({ signal }) => readOriginalPdf(id, signal),
  gcTime: 0, staleTime: Infinity, retry: false,
 });
 useEffect(() => {
  if (!query.data) return;
  const objectUrl = URL.createObjectURL(query.data);
  if (frame.current) frame.current.src = `${objectUrl}#page=${Number.isInteger(page) && page > 0 ? page : 1}`;
  if (download.current) download.current.href = objectUrl;
  return () => URL.revokeObjectURL(objectUrl);
 }, [query.data, page]);
 if (query.isPending) return <p role="status">Loading original PDF…</p>;
 if (query.error) return <div role="alert" className="space-y-2"><p>{query.error.message}</p><Button variant="outline" onClick={() => query.refetch()}>Retry PDF</Button></div>;
 return <section aria-label="Original paper PDF" className="min-w-0 space-y-3">
  <p className="text-sm text-muted-foreground">Original layout. If your browser cannot display PDFs, download the file or use the extracted text preview.</p>
  {query.data && <><a ref={download} className="underline focus-visible:outline" download="paper.pdf">Download PDF</a><iframe title="Original paper PDF" ref={frame} className="h-[32rem] w-full rounded border border-border" sandbox="" /></>}
 </section>;
}
