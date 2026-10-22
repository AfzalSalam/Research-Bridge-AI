"""Topic-driven worldwide institution selection, independent of internship claims."""

from collections import Counter

from app.clients.institutions import InstitutionRegistry, RegistryUnavailable
from app.core.errors import AppError
from app.schemas.discovery import PaperDiscoveryRequest
from app.schemas.university import UniversityScanRequest
from app.services.discovery import PaperDiscoveryReader
from app.services.university_sources import UniversitySource


class GlobalUniversityDiscovery:
    def __init__(
        self, papers: PaperDiscoveryReader, registry: InstitutionRegistry
    ) -> None:
        self.papers = papers
        self.registry = registry

    async def sources(
        self, request: UniversityScanRequest
    ) -> tuple[dict[str, UniversitySource], list[str]]:
        try:
            response = await self.papers.search(
                PaperDiscoveryRequest(query=request.query, limit=25)
            )
        except AppError:
            return {}, [
                "Worldwide institution discovery is unavailable; "
                "reviewed starting sources are still scanned."
            ]
        counts: Counter[str] = Counter()
        for paper in response.papers:
            seen: set[str] = set()
            for author in paper.authors:
                for institution in author.institutions:
                    if not institution.ror_id:
                        continue
                    if request.region == "india" and institution.country_code != "IN":
                        continue
                    if (
                        request.region == "international"
                        and institution.country_code in {None, "IN"}
                    ):
                        continue
                    seen.add(institution.ror_id)
            counts.update(sorted(seen))
        sources: dict[str, UniversitySource] = {}
        warnings = list(response.warnings)
        for identifier, _ in counts.most_common(6):
            try:
                official = await self.registry.resolve(identifier)
            except RegistryUnavailable as error:
                warnings.append(str(error))
                break
            if official is None:
                continue
            sources[identifier] = UniversitySource(
                id=identifier,
                name=official.name,
                program_name="Research internship information",
                program_url=official.website,
                seeds=(),
                hosts=official.hosts,
                application_note=(
                    "Discovered through relevant publications. Verify the "
                    "current call and external-student eligibility; "
                    "a paper affiliation is not an opening."
                ),
                program_verified_seed=False,
            )
        warnings.append(
            f"Worldwide discovery verified {len(sources)} topic-relevant websites "
            "(up to six per scan). This is partial coverage, "
            "not all universities or confirmed internships."
        )
        return sources, warnings
