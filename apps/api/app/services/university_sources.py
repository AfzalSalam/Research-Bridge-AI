"""Reviewed entry points; no arbitrary hostnames supplied by users or pages."""

from dataclasses import dataclass

from app.schemas.university import UniversityId


@dataclass(frozen=True)
class UniversitySource:
    id: str
    name: str
    program_name: str
    program_url: str
    seeds: tuple[str, ...]
    hosts: frozenset[str]
    application_note: str
    program_verified_seed: bool = True


SOURCES: dict[str, UniversitySource] = {
    "oist": UniversitySource(
        "oist",
        "OIST · Japan",
        "Research Internship",
        "https://www.oist.jp/admissions/research-internship/apply-research-internship",
        (
            "https://www.oist.jp/admissions/research-internship/ri-faculty-project-availability",
        ),
        frozenset({"oist.jp"}),
        "Use the official internship portal. OIST asks applicants not to seek "
        "faculty approval by email for this centralized program.",
    ),
    "kaust": UniversitySource(
        "kaust",
        "KAUST · Saudi Arabia",
        "Visiting Student Research Program",
        "https://admissions.kaust.edu.sa/study/internships",
        ("https://cemse.kaust.edu.sa/profiles",),
        frozenset({"kaust.edu.sa"}),
        "Check the official project and application requirements. A university "
        "program does not confirm that every professor has a vacancy.",
    ),
    "ista": UniversitySource(
        "ista",
        "ISTA · Austria",
        "Year-round Scientific Internships",
        "https://phd.pages.ist.ac.at/scientific-internships/",
        ("https://ista.ac.at/en/research/", "https://pub.ista.ac.at/~chl/index.html"),
        frozenset({"ist.ac.at", "ista.ac.at"}),
        "Scientific internships depend on a research group's funding and approval. "
        "The separate summer ISTernship program is not this opportunity.",
    ),
    "iitgn": UniversitySource(
        "iitgn",
        "IIT Gandhinagar · India",
        "Summer Research Internship Program",
        "https://srip.iitgn.ac.in/info/guidelines/",
        ("https://cse.iitgn.ac.in/people/faculty/",),
        frozenset({"iitgn.ac.in"}),
        "Seasonal program. Check the current call and student eligibility. "
        "A closed call is not an active opening; Indian preference is not inferred.",
    ),
}


# Official external-student program pages reviewed on 2026-10-09. A seasonal
# program is not labelled open unless the fetched page supplies current evidence.
SOURCES.update(
    {
        "iitk": UniversitySource(
            "iitk",
            "IIT Kanpur · India",
            "SURGE",
            "https://surge.iitk.ac.in/",
            ("https://www.cse.iitk.ac.in/",),
            frozenset({"iitk.ac.in"}),
            "SURGE includes a non-IITK student category. Check the current call, "
            "eligibility and dates; participation is not guaranteed.",
        ),
        "iisc": UniversitySource(
            "iisc",
            "IISc · India",
            "IPC Summer Research Fellowship",
            "https://ipc.iisc.ac.in/summer_fellowships.php",
            ("https://ipc.iisc.ac.in/",),
            frozenset({"iisc.ac.in"}),
            "This is a department-specific seasonal fellowship, not an institute-wide "
            "open internship. Read its eligibility and current deadline.",
        ),
        "epfl": UniversitySource(
            "epfl",
            "EPFL · Switzerland",
            "Summer@EPFL",
            "https://summer.epfl.ch/",
            ("https://www.epfl.ch/schools/ic/research/",),
            frozenset({"epfl.ch"}),
            "Summer@EPFL is a seasonal fellowship for eligible external students. "
            "Other EPFL programs may have different eligibility "
            "or partner restrictions.",
        ),
    }
)


def selected_sources(region: str, universities: list[UniversityId] | None) -> list[str]:
    keys = universities if universities is not None else list(SOURCES)
    indian = {"iitgn", "iitk", "iisc"}
    return [
        key
        for key in keys
        if region == "both" or (key in indian) == (region == "india")
    ]
