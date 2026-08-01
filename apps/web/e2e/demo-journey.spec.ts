import { expect, test } from "@playwright/test";

test("student can move from fictional profile to evidence-grounded outreach", async ({
  page,
}) => {
  await page.goto("/profile");
  await page.getByLabel("Name").fill("Riya Demo");
  await page.getByRole("button", { name: "Save demo profile" }).click();
  await expect(page.getByText("Fictional profile saved in this browser session.")).toBeVisible();
  await expect
    .poll(() =>
      page.evaluate(() =>
        window.sessionStorage.getItem("research-bridge.demo.phase-04.v1"),
      ),
    )
    .toContain("Riya Demo");

  await page.goto("/discover");
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

test("mentor list becomes a focused detail flow on mobile", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/mentors");
  await page.getByRole("button", { name: /Dr. Mira Sen/ }).click();
  await expect(page.getByRole("button", { name: "Back to candidates" })).toBeVisible();
  await page.getByRole("button", { name: "Back to candidates" }).click();
  await expect(page.getByRole("heading", { name: "Fictional researcher candidates" })).toBeVisible();
});

test("mock API discovery keeps partial, empty, and source failures explicit", async ({
  page,
}) => {
  await page.goto("/discover");

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
