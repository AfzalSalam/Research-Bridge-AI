import { expect, test, type APIRequestContext, type Page } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

import { paperDiscoveryResponseSchema } from "../src/features/discovery/contracts";

const apiBaseUrl = "http://127.0.0.1:8100/api/v1";
const authHeaders = { Authorization: "Bearer e2e-token" };
const researchQuery = "interpretable machine learning for clinical decision support";
const profile = {
  name: "E2E Student",
  program: "Computer Science, Year 3",
  institution: "E2E University",
  graduationYear: "2027",
  researchInterests: ["machine learning", "clinical AI"],
  skills: ["Python", "PyTorch"],
  projectTitle: "Interpretable clinical decision support",
  projectSummary:
    "Built an interface for reviewing clinical model predictions alongside feature attribution explanations.",
  weeklyAvailability: "10-15 hours",
};

async function seedProfile(request: APIRequestContext) {
  const response = await request.put(`${apiBaseUrl}/profile`, {
    headers: authHeaders,
    data: profile,
  });
  expect(response.ok(), await response.text()).toBe(true);
}

async function fillOnboarding(page: Page) {
  await page.getByLabel("Full Name", { exact: true }).fill(profile.name);
  await page.getByLabel("Graduation year").fill(profile.graduationYear);
  await page.getByLabel("Programme and year", { exact: false }).fill(profile.program);
  await page.getByLabel("Institution", { exact: true }).fill(profile.institution);
  await page.getByLabel("Research interests").fill(profile.researchInterests.join(", "));
  await page.getByLabel("Relevant skills").fill(profile.skills.join(", "));
  await page.getByLabel("Most relevant project").fill(profile.projectTitle);
  await page.getByLabel("What you actually built or studied").fill(profile.projectSummary);
  await page.getByLabel("Weekly availability").selectOption(profile.weeklyAvailability);
}

test.beforeEach(async ({ request, page }) => {
  // Automatic enrichment must not crawl live university sites in browser tests.
  await page.route("**/api/v1/authors/*/public-email", async route => {
    const authorId = route.request().url().split("/authors/")[1].split("/")[0];
    await route.fulfill({ json: { authorId, authorName: "Fixture author", status: "not-found", emails: [], profiles: [], warnings: [], checkedAt: "2026-10-11T10:00:00Z", pagesChecked: 1, elapsedSeconds: 1, cacheHit: false, lookupUrl: null, verification: "official-profile-evidence-not-deliverability" } });
  });
  // The runner owns a temporary database and a fixed test-only identity. Reset
  // its private aggregate so tests and retries never depend on previous saves.
  const response = await request.delete(`${apiBaseUrl}/account`, { headers: authHeaders });
  expect(response.status()).toBe(204);
});

test("account onboarding and saved profile edits reach mentor evidence and reviewed outreach", async ({
  context,
  page,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/discover");
  await expect(page).toHaveURL(/\/onboarding$/);
  await expect(page.getByRole("heading", { name: "Complete your student profile" })).toBeVisible();
  await fillOnboarding(page);
  await page.getByRole("button", { name: "Continue to Dashboard" }).click();
  await expect(page).toHaveURL(/\/discover$/);

  await page.goto("/profile");
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue(profile.name);
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByLabel("Name", { exact: true }).fill("Riya Researcher");
  await page.getByLabel("Most relevant project").fill("Clinical evidence review workspace");
  await page.getByLabel("Research interests").fill("clinical AI, human-centred AI");
  await page.getByRole("button", { name: "Save profile", exact: true }).click();
  await expect(page.getByText("Your research profile has been saved.")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Name", { exact: true })).toHaveValue("Riya Researcher");
  await expect(page.getByLabel("Most relevant project")).toHaveValue("Clinical evidence review workspace");

  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await expect(page.getByRole("button", { name: "Search papers" })).toBeVisible();
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
  await page.getByRole("button", { name: "Search papers" }).click();
  await page.locator("main").getByRole("link", { name: "Find Professors", exact: true }).click();
  await expect(page).toHaveURL(/\/mentors\?query=/);
  await expect(page.getByLabel("What topic interests you?")).toHaveValue(researchQuery);
  await page.getByRole("button", { name: "Find researchers" }).click();
  await expect(page.getByRole("heading", { name: "People working on your topic" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mira Sen", exact: true })).toBeVisible();
  await expect(page.getByText("Clinical evidence review workspace", { exact: true })).toBeVisible();
  await expect(page.getByText("clinical AI · human-centred AI", { exact: true })).toBeVisible();
  await expect(page.getByText("Affiliations at publication").first()).toBeVisible();
  await expect(page.getByText(/historical paper evidence/)).toBeVisible();
  await page.getByText("How are these results ordered?", { exact: true }).click();
  await expect(page.getByRole("heading", { name: "Why this candidate appears here" })).toBeVisible();
  await expect(page.getByText("Academic title", { exact: true })).toBeVisible();

  await page.getByLabel("2. Choose generation mode").selectOption("deterministic");
  await page.getByRole("button", { name: "Build grounded draft" }).click();
  await expect(page.getByRole("heading", { name: "Outreach draft", exact: true })).toBeVisible();
  await expect(page.getByLabel("Email body")).toHaveValue(/Riya Researcher/);
  await expect(page.getByLabel("Email body")).toHaveValue(/Clinical evidence review workspace/);
  await expect(page.getByLabel("Email body")).toHaveValue(/Human-centred AI for clinical decision support/);
  await expect(page.getByText("Claim-to-evidence map")).toBeVisible();
  await expect(page.getByText(/Deterministic mode requested/)).toBeVisible();

  await page.getByRole("textbox", { name: "Subject", exact: true }).fill("Edited evidence-grounded clinical AI question");
  await expect(page.getByRole("checkbox", { name: /I reviewed the current saved/i })).toBeDisabled();
  await page.getByRole("button", { name: "Save new version" }).click();
  await expect(page.getByText("Saved version 2")).toBeVisible();
  await page.getByRole("checkbox", { name: /I reviewed the current saved/i }).check();
  await page.getByRole("button", { name: "Copy reviewed draft" }).click();
  await expect(page.getByRole("button", { name: "Copied for your review" })).toBeVisible();
  await expect(page.getByRole("button", { name: /send/i })).toHaveCount(0);
});

test("guided discovery pauses for selection and streams a draft using the account profile", async ({ page, request }) => {
  await seedProfile(request);
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await page.getByText("Want help going from a topic to an email?", { exact: true }).click();
  await page.getByLabel("Guided research topic").fill(researchQuery);
  await page.getByRole("button", { name: "Find Mentors", exact: true }).click();
  await page.getByRole("button", { name: /Mira Sen/ }).click();
  await page.getByRole("checkbox", { name: /Human-centred AI for clinical decision support/ }).check();
  await page.getByRole("button", { name: "Generate Outreach Draft" }).click();
  await expect(page.getByText("Draft ready — review before sending")).toBeVisible();
  await expect(page.locator("pre")).toContainText(profile.name);
  await expect(page.locator("pre")).toContainText("Human-centred AI for clinical decision support");
  await expect(page.getByRole("button", { name: /send/i })).toHaveCount(0);
});

test("verified opportunity becomes a durable versioned application record", async ({ page, request }) => {
  await seedProfile(request);
  await page.goto("/opportunities");
  // The fixed provider fixture has a historical deadline; keep this journey date-independent.
  await page.getByRole("checkbox", { name: "Include records with an explicit past deadline" }).check();
  await page.getByRole("button", { name: "Search", exact: true }).click();
  await expect(page.getByText("Research Internship, Robotics")).toBeVisible();
  await expect(page.getByText(/no ranking/i).first()).toBeVisible();
  await expect(page.getByText("Unclear").first()).toBeVisible();
  await expect(page.getByRole("link", { name: /Inspect application/ })).toHaveAttribute(
    "href",
    "https://job-boards.greenhouse.io/thealleninstitute/jobs/7366273",
  );
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("button", { name: "Saved · remove" })).toBeVisible();
  await page.getByRole("button", { name: "Track", exact: true }).click();
  await page.getByRole("link", { name: "Open tracker" }).click();
  await expect(page.getByText("Research Internship, Robotics")).toBeVisible();
  await page.getByLabel("Recorded status").selectOption("applied");
  await page.getByLabel("Private notes").fill("Submitted through the official application page.");
  await page.getByLabel("Follow-up date").fill("2027-01-15");
  await page.getByRole("button", { name: "Save tracker update" }).click();
  await expect(page.getByText("Version 2", { exact: true })).toBeVisible();
  await expect(page.getByText("2 recorded events")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Recorded status")).toHaveValue("applied");
  await expect(page.getByLabel("Private notes")).toHaveValue("Submitted through the official application page.");
  await expect(page.getByRole("button", { name: /submit application/i })).toHaveCount(0);
});

test("OpenAlex integration retains provider evidence without ranking claims", async ({ page, request }) => {
  await seedProfile(request);
  const browserRequests: string[] = [];
  page.on("request", (outgoing) => browserRequests.push(outgoing.url()));
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await page.getByRole("button", { name: "Search papers" }).click();
  await expect(page.getByRole("heading", { name: "Papers on your topic" })).toBeVisible();
  await expect(page.getByText("Human-centred AI for clinical decision support")).toBeVisible();
  await expect(page.getByText("Feedback under distribution shift")).toBeVisible();
  await expect(page.getByText("Academic database results", { exact: true })).toBeVisible();
  await expect(page.getByText("Title-only evidence")).toBeVisible();
  await expect(page.getByRole("link", { name: /DOI record/ })).toHaveAttribute("href", "https://doi.org/10.1234/rbai.2026.001");
  expect(browserRequests.some((url) => url.includes("e2e-provider-key"))).toBe(false);
  await page.getByRole("button", { name: "Search papers" }).click();
  await expect(page.getByText("Provider cache hit")).toBeVisible();
});

test("discovery search and evidence navigation work with the keyboard", async ({ page, request }) => {
  await seedProfile(request);
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  const query = page.getByLabel("What topic interests you?", { exact: true });
  await query.focus();
  await page.keyboard.press("Tab");
  await expect(page.getByLabel("Number of papers")).toBeFocused();
  await page.keyboard.press("Tab");
  await expect(page.getByRole("button", { name: "Search papers" })).toBeFocused();
  await page.keyboard.press("Enter");
  const researcherLink = page.locator("main").getByRole("link", { name: "Find Professors", exact: true });
  await expect(researcherLink).toBeVisible();
  await researcherLink.focus();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/mentors\?query=/);
});

test("mentor list becomes a focused detail flow on mobile", async ({ page, request }) => {
  await seedProfile(request);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/mentors");
  await page.getByRole("button", { name: "Find researchers" }).click();
  await expect(page.getByRole("heading", { name: "Mira Sen", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Back to candidates" }).click();
  const candidate = page.getByRole("button", { name: /Mira Sen/ });
  await expect(candidate).toBeFocused();
  await expect(page.getByRole("heading", { name: "Research authors", exact: true })).toBeVisible();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("button", { name: "Back to candidates" })).toBeVisible();
});

test("discovery keeps loading, partial, empty, and source failure states explicit", async ({ page, request }) => {
  await seedProfile(request);
  const response = await request.post(`${apiBaseUrl}/discovery/papers`, {
    headers: authHeaders,
    data: { query: researchQuery, limit: 12 },
  });
  expect(response.ok(), await response.text()).toBe(true);
  const complete = paperDiscoveryResponseSchema.parse(await response.json());
  let mode: "partial" | "empty" | "error" = "partial";
  let releaseResponse: (() => void) | undefined;
  const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve; });
  await page.route("**/backend/api/v1/discovery/papers", async (route) => {
    await responseGate;
    if (mode === "error") {
      await route.fulfill({ status: 503, json: { error: {
        code: "provider_unavailable",
        message: "The academic source is temporarily unavailable.",
        requestId: "e2e-source-failure",
        details: [],
      } } });
      return;
    }
    await route.fulfill({ json: mode === "partial" ? {
      ...complete, status: "partial", skippedCount: 1,
      warnings: ["One invalid source record was excluded."],
    } : {
      ...complete, status: "empty", papers: [], returnedCount: 0,
      skippedCount: 0, totalProviderResults: 0, warnings: [],
    } });
  });
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await page.getByRole("button", { name: "Search papers" }).click();
  await expect(page.getByRole("heading", { name: "Retrieving publication evidence" })).toBeVisible();
  releaseResponse?.();
  await expect(page.getByRole("heading", { name: "OpenAlex returned partial evidence" })).toBeVisible();
  await expect(page.getByText("Human-centred AI for clinical decision support")).toBeVisible();
  await expect(page.getByText(/One invalid source record was excluded/)).toBeVisible();
  mode = "empty";
  await page.getByRole("button", { name: "Search papers" }).click();
  await expect(page.getByRole("heading", { name: "No paper evidence found" })).toBeVisible();
  mode = "error";
  await page.getByRole("button", { name: "Search papers" }).click();
  await expect(page.getByRole("heading", { name: "OpenAlex evidence is unavailable" })).toBeVisible();
  await expect(page.getByText(/Request reference: e2e-source-failure/)).toBeVisible();
  mode = "partial";
  await page.getByRole("button", { name: "Retry request" }).click();
  await expect(page.getByRole("heading", { name: "Papers on your topic" })).toBeVisible();
});

test("product routes do not create page-level horizontal overflow", async ({ page, request }) => {
  await seedProfile(request);
  for (const width of [360, 390, 768, 1280]) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of ["/profile", "/discover", "/mentors", "/opportunities", "/applications"]) {
      await page.goto(route);
      await expect(page.locator("main h1")).toBeVisible();
      const dimensions = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      expect(dimensions.scrollWidth, `${route} at ${width}px`).toBeLessThanOrEqual(dimensions.clientWidth);
    }
  }
});

test("mobile navigation keeps keyboard focus and honors reduced motion", async ({ page, request }) => {
  await seedProfile(request);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/profile");
  await expect(page.getByLabel("Name", { exact: true })).toBeVisible();
  const skipLink = page.getByRole("link", { name: "Skip to main content" });
  await skipLink.focus();
  await expect(skipLink).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main-content$/);
  const menuButton = page.getByRole("button", { name: "Open navigation" });
  await menuButton.focus();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("dialog", { name: "Navigate Research Bridge" })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(menuButton).toBeFocused();
  const transitionDuration = await page.getByRole("button", { name: "Save profile", exact: true })
    .evaluate((element) => getComputedStyle(element).transitionDuration);
  expect(Number.parseFloat(transitionDuration)).toBeLessThanOrEqual(0.00001);
});


test("university scan submits a chosen target and shows honest partial results", async ({ page, request }) => {
  await seedProfile(request);
  // Browser contract fixture; live university extraction is checked separately.
  await page.route("**/backend/api/v1/discovery/universities/scan", async (route) => {
    expect(route.request().postDataJSON().target).toBe(30);
    const snapshot = {
      state: "partial", query: "machine learning", target: 30,
      papers: [{ id: "paper-one", university: "OIST", title: null,
        citation: "Machine learning for robotics — fixture citation", doi: "10.1234/test",
        publicationUrl: "https://doi.org/10.1234/test", sourceUrl: "https://www.oist.jp/",
        checkedAt: "2026-10-09T00:00:00Z", matchedTerms: ["machine", "learning"] }],
      programs: [], pagesAttempted: 2, pagesRead: 1, elapsedSeconds: 2,
      budgetSeconds: 120, currentUniversity: null, stopReason: "reviewed_links_exhausted",
      warnings: ["A university source could not be reached."],
    };
    await route.fulfill({ status: 200, contentType: "text/event-stream", body: `data: ${JSON.stringify(snapshot)}\n\n` });
  });
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await page.getByRole("button", { name: "University websites", exact: true }).click();
  await page.getByLabel("Number of papers").selectOption("30");
  await page.getByRole("button", { name: "Scan university websites", exact: true }).click();
  await expect(page.getByText("Found 1 of 30 requested papers")).toBeVisible();
  await expect(page.getByText("Machine learning for robotics — fixture citation")).toBeVisible();
  await expect(page.getByRole("link", { name: "University evidence" })).toHaveAttribute("href", "https://www.oist.jp/");
  expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
});


test("paper results and query survive navigation and reload without repeating the search", async ({ page, request }) => {
  await seedProfile(request);
  let searches = 0;
  page.on("request", (req) => { if (req.method() === "POST" && req.url().endsWith("/discovery/papers")) searches++; });
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await page.getByRole("button", { name: "Search papers", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Papers on your topic" })).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "Primary", exact: true });
  await navigation.getByRole("link", { name: "My Research", exact: true }).click();
  await expect(page).toHaveURL(/\/research$/);
  await navigation.getByRole("link", { name: "Discover", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Papers on your topic" })).toBeVisible();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Papers on your topic" })).toBeVisible();
  await expect(page.getByLabel("What topic interests you?", { exact: true })).toHaveValue(researchQuery);
  expect(searches).toBe(1);
  await page.getByRole("button", { name: "Clear results", exact: true }).click();
  await page.reload();
  await expect(page.getByRole("heading", { name: "Papers on your topic" })).toHaveCount(0);
});

test("a university scan finishes while another section is open and restores on refresh", async ({ page, request }) => {
  await seedProfile(request);
  let release: () => void = () => {};
  const gate = new Promise<void>((resolve) => { release = resolve; });
  let scans = 0;
  await page.route("**/backend/api/v1/discovery/universities/scan", async (route) => {
    scans++;
    expect(route.request().postDataJSON().region).toBe("both");
    expect(route.request().postDataJSON().universities).toBeUndefined();
    await gate;
    await route.fulfill({ contentType: "text/event-stream", body: `data: ${JSON.stringify({
      state: "partial", query: "machine learning", target: 20, papers: [], programs: [],
      pagesAttempted: 3, pagesRead: 2, elapsedSeconds: 2, budgetSeconds: 120,
      currentUniversity: null, stopReason: "reviewed_links_exhausted", warnings: ["Background scan complete."],
    })}\n\n` });
  });
  await page.goto("/discover");
  await page.getByRole("button", { name: "University websites", exact: true }).click();
  await page.getByRole("button", { name: "Scan university websites", exact: true }).click();
  await expect(page.getByRole("button", { name: "Cancel scan", exact: true })).toBeVisible();
  await expect(page.getByText(/up to 2 minutes total/)).toBeVisible();
  const navigation = page.getByRole("navigation", { name: "Primary", exact: true });
  await navigation.getByRole("link", { name: "My Research", exact: true }).click();
  release();
  await navigation.getByRole("link", { name: "Discover", exact: true }).click();
  await expect(page.getByText("Found 0 of 20 requested papers")).toBeVisible();
  await expect(page.getByRole("button", { name: "Cancel scan", exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByText("Found 0 of 20 requested papers")).toBeVisible();
  expect(scans).toBe(1);
});


test("selected researcher contact lookup exposes evidence and survives navigation", async ({ page, request }) => {
  await seedProfile(request);
  let calls = 0;
  await page.route("**/api/v1/authors/*/public-email", async (route) => {
    calls += 1;
    const authorId = route.request().url().split("/authors/")[1].split("/")[0];
    await route.fulfill({ json: {
      authorId, authorName: "Mira Sen", status: "found",
      emails: [{ email: "mira.sen@iitk.ac.in", sourceUrl: "https://www.cse.iitk.ac.in/users/mira/", identityEvidence: ["ORCID matches the stored author identifier"], evidenceUrls: ["https://www.cse.iitk.ac.in/users/mira/"], extraction: "mailto", checkedAt: "2026-10-10T10:00:00Z" }],
      profiles: [], warnings: [], checkedAt: "2026-10-10T10:00:00Z", pagesChecked: 2,
      elapsedSeconds: 3, cacheHit: false, lookupUrl: null,
      verification: "official-profile-evidence-not-deliverability",
    } });
  });
  await page.goto("/mentors");
  await page.getByRole("button", { name: "Find researchers", exact: true }).click();
  await page.getByRole("button", { name: "Find public email", exact: true }).click();
  await expect(page.getByText("mira.sen@iitk.ac.in", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: /View email on official source/ })).toHaveAttribute("href", "https://www.cse.iitk.ac.in/users/mira/");
  const navigation = page.getByRole("navigation", { name: "Primary", exact: true });
  await navigation.getByRole("link", { name: "Discover", exact: true }).click();
  await page.goto("/mentors");
  await expect(page.getByText("mira.sen@iitk.ac.in", { exact: true })).toBeVisible();
  await page.reload();
  await expect(page.getByText("mira.sen@iitk.ac.in", { exact: true })).toBeVisible();
  expect(calls).toBe(1);
});



test("saved research preserves notes and the exact author-to-draft handoff", async ({page,request})=>{
 await seedProfile(request);
 await page.goto("/discover");
 await page.getByRole("button",{name:"Academic databases",exact:true}).click();
 await page.getByRole("button",{name:"Search papers",exact:true}).click();
 await page.getByRole("link",{name:"Read, save, and contact authors"}).first().click();
 await page.getByRole("button",{name:"Save to My Research",exact:true}).click();
 await expect(page.getByRole("button",{name:"Saved to My Research"})).toBeVisible();
 await page.getByRole("link",{name:"Find contact and prepare outreach"}).first().click();
 await expect(page.getByText(/^Selected from:/)).toBeVisible();
 await page.getByRole("button",{name:"Build grounded draft",exact:true}).click();
 await expect(page.getByRole("heading",{name:"Outreach draft",exact:true})).toBeVisible();
 await page.getByRole("navigation",{name:"Primary",exact:true}).getByRole("link",{name:"Conversations",exact:true}).click();
 await page.getByRole("link",{name:"Continue draft",exact:true}).first().click();
 await expect(page.getByRole("heading",{name:"Outreach draft",exact:true})).toBeVisible();
 await page.goto("/research");
 await page.getByLabel("Your reading notes").fill("Compare the methods with my current project.");
 await page.getByRole("button",{name:"Save notes and shortlist"}).click();
 await expect(page.getByText("Saved to your account.")).toBeVisible();
 await page.reload();
 await expect(page.getByLabel("Your reading notes")).toHaveValue("Compare the methods with my current project.");
});


test("Discover checks emails before opening a paper", async ({ page, request }) => {
  await seedProfile(request);
  let lookups = 0;
  await page.route("**/api/v1/authors/*/public-email", async route => {
    lookups++;
    const authorId = route.request().url().split("/authors/")[1].split("/")[0];
    await route.fulfill({ json: { authorId, authorName: "Fixture author", status: "found", emails: [{ email: "researcher@example.edu", sourceUrl: "https://example.edu/researcher", identityEvidence: ["Fixture publication match"], evidenceUrls: ["https://example.edu/researcher"], extraction: "mailto", checkedAt: "2026-10-11T10:00:00Z" }], profiles: [], warnings: [], checkedAt: "2026-10-11T10:00:00Z", pagesChecked: 1, elapsedSeconds: 1, cacheHit: false, lookupUrl: null, verification: "official-profile-evidence-not-deliverability" } });
  });
  await page.goto("/discover");
  await page.getByRole("button", { name: "Academic databases", exact: true }).click();
  await page.getByRole("button", { name: "Search papers", exact: true }).click();
  await expect(page.getByText(/Public email found for/).first()).toBeVisible();
  await page.getByLabel("Only papers with a public email found").check();
  await expect(page.getByRole("link", { name: "researcher@example.edu · source" }).first()).toHaveAttribute("href", "https://example.edu/researcher");
  await page.getByRole("link", { name: /^Contact / }).first().click();
  await expect(page.getByText(/^Selected from:/)).toBeVisible();
  await expect(page.getByText("researcher@example.edu", { exact: true })).toBeVisible();
  expect(lookups).toBeLessThanOrEqual(6);
});


test("paper PDF setup state and extracted page preview are accessible", async ({ page, request }) => {
 await seedProfile(request);
 const found = await request.post(`${apiBaseUrl}/discovery/papers`, { headers: authHeaders, data: { query: researchQuery, limit: 10 } });
 const paper = paperDiscoveryResponseSchema.parse(await found.json()).papers[0];
 await page.goto(`/research/papers/${paper.id}`);
 await expect(page.getByText(/PDF uploads are not enabled yet/)).toBeVisible();
 await expect(page.getByRole("button", { name: "Upload PDF", exact: true })).toHaveCount(0);
 const id = "11111111-1111-4111-8111-111111111111";
 await page.route("**/api/v1/documents/paper/*", route => route.fulfill({ json: { uploads_enabled: false, documents: [{ id, filename: "fixture.pdf", status: "ready", reason: "extracted", warnings: [] }] } }));
 await page.route(`**/api/v1/documents/${id}/index`, route => route.fulfill({ json: { enabled: true, status: "completed", reason: null, retry_at: null, disclosure_version: "paper-embeddings-v1", reserved_today: 0, daily_limit: 1000000 } }));
 await page.route(`**/api/v1/documents/${id}/pages`, route => route.fulfill({ json: [{ number: 1, text: "Fixture method evidence on page one." }, { number: 2, text: "Fixture limitations on page two." }] }));
 await page.route(`**/api/v1/documents/${id}/file`, route => route.fulfill({ status: 503, json: {} }));
 let answerCalls = 0;
 await page.route(`**/api/v1/documents/${id}/reading-history`, route => route.fulfill({json: answerCalls ? [{id:"22222222-2222-4222-8222-222222222222",question:"What limitations?",model:"fixture",created_at:"2026-10-22T00:00:00Z",result:{status:"answer",reason:"reviewed",notice:"Fixture saved answer only.",source_scope:"retrieved_full_text_excerpts",claims:[{text:"Saved fixture limitations.",citations:[{page:2,start:0,end:32,quote:"Fixture limitations on page two."}]}]}}] : []}));
 await page.route(`**/api/v1/documents/${id}/answers`, async route => {
  if (route.request().method() === "GET") {
   await route.fulfill({ json: { enabled: true, provider: "Google Gemini", model: "fixture", disclosure_version: "paper-answer-gemini-v1", disclosure: "Fixture question and excerpt disclosure.", reserved_calls_today: 0, daily_call_limit: 30, calls_reserved_per_question: 3 } });
  } else {
   answerCalls++;
   expect(route.request().postDataJSON()).toMatchObject({ accepted: true, disclosure_version: "paper-answer-gemini-v1", question: "What limitations?" });
   expect(route.request().postDataJSON().request_id).toMatch(/^[a-f0-9-]{36}$/);
   await route.fulfill({ json: { status: "answer", reason: "reviewed", notice: "Fixture answer only.", source_scope: "retrieved_full_text_excerpts", claims: [{ text: "The fixture discusses limitations.", citations: [{ page: 2, start: 0, end: 32, quote: "Fixture limitations on page two." }] }] } });
  }
 });
 await page.reload();
 await page.getByRole("button", { name: "View original PDF" }).click();
 await expect(page.getByRole("button", { name: "Retry PDF" })).toBeVisible();
 await page.getByRole("button", { name: "Close original PDF" }).click();
 await page.getByRole("button", { name: "Read extracted pages" }).click();
 await expect(page.getByText("Fixture method evidence on page one.")).toBeVisible();
 await page.route(`**/api/v1/documents/${id}/passages`, route => route.fulfill({ json: { document_id: id, status: "matches", engine: "lexical_fallback", notice: "Fixture passages only", passages: [{ page: 2, start: 0, end: 32, text: "Fixture limitations on page two." }] } }));
 await page.getByLabel("Topic or keywords").fill("limitations");
 await page.getByRole("button", { name: "Find passages", exact: true }).click();
 await page.getByRole("button", { name: "Read page 2", exact: true }).click();
 await expect(page.getByRole("combobox", { name: "Page", exact: true })).toHaveValue("2");
 await expect(page.getByLabel("Extracted text for page 2")).toHaveText("Fixture limitations on page two.");
 let semanticCalls = 0;
 await page.route(`**/api/v1/documents/${id}/semantic-passages`, async route => {
  semanticCalls++;
  expect(route.request().postDataJSON()).toMatchObject({ accepted: true, disclosure_version: "paper-query-embeddings-v1" });
  await route.fulfill({ json: { document_id: id, notice: "Fixture only", passages: [{ page: 1, start: 0, end: 36, text: "Fixture method evidence on page one." }] } });
 });
 const semantic = page.getByRole("region", { name: "Semantic search within this paper", exact: true });
 await semantic.getByLabel("Question or topic").fill("How does the method work?");
 await semantic.getByRole("button", { name: "Search by meaning", exact: true }).click();
 await expect(semantic.getByRole("alert")).toContainText("Review and accept");
 expect(semanticCalls).toBe(0);
 await semantic.getByRole("checkbox").check();
 await semantic.getByRole("button", { name: "Search by meaning", exact: true }).click();
 await semantic.getByRole("button", { name: "Read page 1", exact: true }).click();
 await expect(page.getByRole("combobox", { name: "Page", exact: true })).toHaveValue("1");
 expect(semanticCalls).toBe(1);
 const answers = page.getByRole("region", { name: "Ask about this paper", exact: true });
 await answers.getByLabel("Your question about the paper").fill("What limitations?");
 await answers.getByRole("button", { name: "Ask the paper", exact: true }).click();
 await expect(answers.getByRole("alert")).toContainText("Review and accept");
 expect(answerCalls).toBe(0);
 await answers.getByRole("checkbox").check();
 await answers.getByRole("button", { name: "Ask the paper", exact: true }).click();
 await answers.getByRole("button", { name: "Read cited page 2", exact: true }).click();
 await expect(page.getByRole("combobox", { name: "Page", exact: true })).toHaveValue("2");
 expect(answerCalls).toBe(1);
 const history = page.getByRole("region", {name:"Saved reading questions",exact:true});
 await history.getByText("What limitations?", {exact:true}).click();
 await history.getByRole("button", {name:"Read saved cited page 2"}).click();
 await expect(page.getByRole("combobox", {name:"Page",exact:true})).toHaveValue("2");
 await page.getByRole("button", { name: "Show PDF beside questions", exact: true }).click();
 await expect(page.getByRole("button", { name: "Retry PDF", exact: true })).toBeVisible();
 await expect(answers.getByText("The fixture discusses limitations.")).toBeVisible();

 expect((await new AxeBuilder({ page }).analyze()).violations).toEqual([]);
 await page.setViewportSize({ width: 390, height: 844 });
 expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
});
