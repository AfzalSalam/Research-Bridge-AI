import { expect, it } from "vitest";
import { citationIdentifier, normalizeCitationDoi } from "./citation-identifier";

it.each([
 ["https://arxiv.org/abs/2301.12345v2", "10.48550/arxiv.2301.12345"],
 ["https://arxiv.org/pdf/0704.0001v3.pdf", "10.48550/arxiv.0704.0001"],
 ["http://www.arxiv.org/abs/math.GT/0309136v1", "10.48550/arxiv.math.gt/0309136"],
 ["https://arxiv.org/abs/hep-th/9901001", "10.48550/arxiv.hep-th/9901001"],
])("resolves the canonical identifier from %s", (url, doi) => {
 expect(citationIdentifier(null, url)).toEqual({doi, arxiv: true});
});
it.each(["https://arxiv.org.evil.test/abs/2301.12345", "https://arxiv.org@evil.test/abs/2301.12345", "https://arxiv.org/abs/invalid", "https://arxiv.org/search/2301.12345", "file:///abs/2301.12345", "https://arxiv.org/abs/2301.12345v0"])("rejects untrusted or malformed identifiers: %s", url => {
 expect(citationIdentifier(null, url)).toBeNull();
});
it("normalizes DOI prefixes and prefers a supplied valid publication DOI", () => {
 expect(normalizeCitationDoi(" HTTPS://DX.DOI.ORG/10.1234/AbC ")).toBe("10.1234/abc");
 expect(citationIdentifier("doi:10.1234/ABC", "https://arxiv.org/abs/2301.12345")).toEqual({doi:"10.1234/abc", arxiv:false});
 expect(normalizeCitationDoi("unverified citation title")).toBeNull();
});
