import { expect, test } from "@playwright/test";

test("student can move from fictional profile to evidence-grounded outreach", async ({
  page,
}) => {
  await page.goto("/profile");
  await page.getByLabel("Name").fill("Riya Demo");
  await page.getByRole("button", { name: "Save demo profile" }).click();
  await expect(page.getByText("Fictional profile saved to the demo database.")).toBeVisible();
  await page.evaluate(() => window.sessionStorage.clear());
  await page.reload();
  await expect(page.getByLabel("Name")).toHaveValue("Riya Demo");

  await page.goto("/discover");
  await page.getByRole("tab", { name: "Recruiter demo" }).click();
  await page.getByRole("button", { name: "Run demo search" }).click();
  await expect(
    page.getByRole("heading", { name: "Researchers connected to paper evidence" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect evidence" }).first().click();

  await expect(page.getByRole("heading", { name: "Dr. Mira Sen (fictional)" })).toBeVisible();
  await page
    .getByLabel(/Context Before Confidence: Decision Support/)
    .check();
  await page.getByRole("button", { name: "Create editable draft" }).click();

  const draftBody = page.getByLabel("Email body");
  await expect(draftBody).toHaveValue(/Riya Demo/);
  await expect(draftBody).toHaveValue(/Context Before Confidence/);
  await expect(page.getByRole("button", { name: /send/i })).toHaveCount(0);

  await page.getByRole("button", { name: "Add to tracker" }).click();
  await page.getByRole("link", { name: "Open tracker" }).click();
  await expect(page.getByRole("heading", { name: "Dr. Mira Sen (fictional)" })).toBeVisible();

  await page.getByLabel("Status").selectOption("Drafting");
  await page.getByRole("button", { name: "Save tracker update" }).click();
  await expect(page.getByText("Application record updated in this browser session.")).toBeVisible();
});

test("live OpenAlex papers retain provider evidence without ranking claims", async ({
  page,
}) => {
  const browserRequests: string[] = [];
  page.on("request", (request) => browserRequests.push(request.url()));
  await page.goto("/discover");

  await page.getByRole("button", { name: "Search OpenAlex" }).click();

  await expect(
    page.getByRole("heading", { name: "Reviewable publication evidence" }),
  ).toBeVisible();
  await expect(page.getByText("Human-centred AI for clinical decision support")).toBeVisible();
  await expect(page.getByText("Feedback under distribution shift")).toBeVisible();
  await expect(page.getByText(/not Research Bridge ranked/i).first()).toBeVisible();
  await expect(page.getByText("Title-only evidence")).toBeVisible();
  await expect(page.getByRole("link", { name: /DOI record/ })).toHaveAttribute(
    "href",
    "https://doi.org/10.1234/rbai.2026.001",
  );
  expect(browserRequests.some((url) => url.includes("e2e-provider-key"))).toBe(false);

  await page.getByRole("button", { name: "Search OpenAlex" }).click();
  await expect(page.getByText("Provider cache hit")).toBeVisible();
});

test("discovery modes implement keyboard tab navigation", async ({ page }) => {
  await page.goto("/discover");
  const liveTab = page.getByRole("tab", { name: "Live OpenAlex papers" });
  const demoTab = page.getByRole("tab", { name: "Recruiter demo" });

  await liveTab.focus();
  await page.keyboard.press("ArrowRight");
  await expect(demoTab).toBeFocused();
  await expect(demoTab).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByRole("tabpanel", { name: "Recruiter demo" }),
  ).toBeVisible();

  await page.keyboard.press("Home");
  await expect(liveTab).toBeFocused();
  await expect(liveTab).toHaveAttribute("aria-selected", "true");
});

test("mentor list becomes a focused detail flow on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/mentors");
  await page.getByRole("tab", { name: "Recruiter demo + outreach" }).click();
  await page.getByRole("button", { name: /Dr. Mira Sen/ }).click();
  await expect(page.getByRole("button", { name: "Back to candidates" })).toBeVisible();
  await page.getByRole("button", { name: "Back to candidates" }).click();
  await expect(page.getByRole("heading", { name: "Fictional researcher candidates" })).toBeVisible();
});

test("live papers lead to grounded, versioned, human-reviewed outreach", async ({
  context,
  page,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  await page.goto("/discover");
  await page.getByRole("button", { name: "Search OpenAlex" }).click();
  await page.getByRole("link", { name: "Find researchers" }).click();
  await expect(page).toHaveURL(/\/mentors\?query=/);
  await expect(page.getByLabel("Research topic, DOI, or OpenAlex Work ID")).toHaveValue(
    "interpretable machine learning for clinical decision support",
  );

  await page.getByRole("button", { name: "Find researchers" }).click();
  await expect(
    page.getByRole("heading", { name: "Reviewable researcher evidence" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mira Sen" })).toBeVisible();
  await expect(page.getByText("Affiliations at publication").first()).toBeVisible();
  await expect(page.getByText(/historical paper evidence/)).toBeVisible();
  await expect(page.getByText(/placement-relevance-v1/)).toBeVisible();
  await expect(page.getByText("Academic title", { exact: true })).toBeVisible();
  await page.getByLabel("2. Choose generation mode").selectOption("deterministic");
  await page.getByRole("button", { name: "Build grounded draft" }).click();
  await expect(page.getByRole("heading", { name: "Outreach draft" })).toBeVisible();
  await expect(page.getByText("Claim-to-evidence map")).toBeVisible();
  await expect(page.getByText(/Deterministic mode requested/)).toBeVisible();

  const subject = page.getByRole("textbox", { name: "Subject", exact: true });
  await subject.fill("Edited evidence-grounded clinical AI question");
  await expect(page.getByRole("checkbox", { name: /I reviewed the current saved/i })).toBeDisabled();
  await page.getByRole("button", { name: "Save new version" }).click();
  await expect(page.getByText("Saved version 2")).toBeVisible();

  await page.getByRole("checkbox", { name: /I reviewed the current saved/i }).check();
  await page.getByRole("button", { name: "Copy reviewed draft" }).click();
  await expect(page.getByRole("button", { name: "Copied for your review" })).toBeVisible();
  await expect(page.getByRole("button", { name: /send/i })).toHaveCount(0);
});

test("mock API discovery keeps partial, empty, and source failures explicit", async ({
  page,
}) => {
  await page.goto("/discover");
  await page.getByRole("tab", { name: "Recruiter demo" }).click();

  await page.getByLabel("Demo response").selectOption("partial");
  await page.getByRole("button", { name: "Run demo search" }).click();
  await expect(page.getByRole("heading", { name: "Two of three fixture records are available" })).toBeVisible();
  await expect(page.getByText("2 reviewable")).toBeVisible();

  await page.getByLabel("Demo response").selectOption("empty");
  await page.getByRole("button", { name: "Run demo search" }).click();
  await expect(page.getByRole("heading", { name: "No paper evidence matched this demo query" })).toBeVisible();

  await page.getByLabel("Demo response").selectOption("error");
  await page.getByRole("button", { name: "Run demo search" }).click();
  await expect(page.getByRole("heading", { name: "The source could not be reached" })).toBeVisible();
  await expect(page.getByText(/Request reference:/)).toBeVisible();
});

test("product routes do not create page-level horizontal overflow", async ({ page }) => {
  const routes = [
    "/profile",
    "/discover",
    "/mentors",
    "/opportunities",
    "/applications",
  ];
  const widths = [360, 390, 768, 1280];

  for (const width of widths) {
    await page.setViewportSize({ width, height: 900 });
    for (const route of routes) {
      await page.goto(route);
      const dimensions = await page.evaluate(() => ({
        clientWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
      }));
      expect(dimensions.scrollWidth, `${route} at ${width}px`).toBeLessThanOrEqual(
        dimensions.clientWidth,
      );
    }
  }
});

test("mobile navigation keeps keyboard focus and honors reduced motion", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/profile");
  await expect(page.getByLabel("Name")).toBeVisible();

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

  const transitionDuration = await page
    .getByRole("button", { name: "Reset demo" })
    .evaluate((element) => getComputedStyle(element).transitionDuration);
  expect(Number.parseFloat(transitionDuration)).toBeLessThanOrEqual(0.00001);
});
