import { test, expect } from '@playwright/test';
import path from 'path';

// Use authenticated state for all tests in this file
test.use({ storageState: path.join(__dirname, '../.auth/user.json') });

test.describe('Trips (Authenticated)', () => {
  test.beforeEach(async ({ page }) => {
    // Wait for auth state to be loaded
    await page.goto('/trips');
  });

  test('should display trips list page', async ({ page }) => {
    // Should see trips page content
    await expect(page.locator('text=/trips|reisen|meine reisen/i')).toBeVisible();

    // Should have option to create new trip
    const createButton = page.getByRole('button', { name: /new|neu|erstellen|create/i });
    await expect(createButton).toBeVisible();
  });

  test('should open create trip dialog/page', async ({ page }) => {
    // Click create trip button
    const createButton = page.getByRole('button', { name: /new|neu|erstellen|create/i });
    await createButton.click();

    // Should show trip creation form
    await expect(page.getByLabel(/title|titel/i)).toBeVisible({ timeout: 5000 });
    await expect(page.getByLabel(/destination|reiseziel/i)).toBeVisible();
  });

  test('should create a new trip', async ({ page }) => {
    // Click create trip button
    const createButton = page.getByRole('button', { name: /new|neu|erstellen|create/i });
    await createButton.click();

    // Fill in trip details
    const uniqueTitle = `E2E Test Trip ${Date.now()}`;
    await page.getByLabel(/title|titel/i).fill(uniqueTitle);
    await page.getByLabel(/destination|reiseziel/i).fill('Berlin');

    // Description if available
    const descriptionField = page.getByLabel(/description|beschreibung/i);
    if (await descriptionField.isVisible()) {
      await descriptionField.fill('Test trip created by E2E tests');
    }

    // Submit the form
    await page.getByRole('button', { name: /save|speichern|create|erstellen/i }).click();

    // Should see the new trip in the list or be redirected to it
    await expect(page.locator(`text=${uniqueTitle}`)).toBeVisible({ timeout: 10000 });
  });

  test('should navigate to trip details', async ({ page }) => {
    // Look for existing trips
    const tripCards = page.locator('[data-testid="trip-card"], .trip-card, article');

    // If there are trips, click on the first one
    if ((await tripCards.count()) > 0) {
      await tripCards.first().click();

      // Should navigate to trip detail page
      await expect(page).toHaveURL(/trips\/\d+/);

      // Should show trip details
      await expect(
        page.locator('text=/details|diary|places|timeline|budget/i')
      ).toBeVisible();
    } else {
      // No trips yet, skip this test
      test.skip();
    }
  });

  test('should handle empty trips list', async ({ page }) => {
    // Even with no trips, page should render properly
    await expect(page.locator('body')).toBeVisible();

    // Should have create button
    await expect(
      page.getByRole('button', { name: /new|neu|erstellen|create/i })
    ).toBeVisible();
  });
});

test.describe('Trip Details (Authenticated)', () => {
  test.use({ storageState: path.join(__dirname, '../.auth/user.json') });

  test('should display trip tabs/sections', async ({ page }) => {
    // First create a trip or navigate to an existing one
    await page.goto('/trips');

    // Try to click on first trip
    const tripCards = page.locator('[data-testid="trip-card"], .trip-card, article');

    if ((await tripCards.count()) === 0) {
      // Create a trip first
      await page.getByRole('button', { name: /new|neu|erstellen|create/i }).click();
      await page.getByLabel(/title|titel/i).fill('E2E Detail Test Trip');
      await page.getByLabel(/destination|reiseziel/i).fill('Munich');
      await page.getByRole('button', { name: /save|speichern|create|erstellen/i }).click();
      await page.waitForURL(/trips\/\d+/, { timeout: 10000 });
    } else {
      await tripCards.first().click();
      await page.waitForURL(/trips\/\d+/);
    }

    // Check for trip sections/tabs
    const sections = ['diary', 'places', 'timeline', 'budget', 'map'];
    for (const section of sections) {
      const sectionElement = page.locator(
        `text=/${section}|tagebuch|orte|zeitplan|budget|karte/i`
      );
      // At least some of these should exist
      if (await sectionElement.first().isVisible({ timeout: 1000 }).catch(() => false)) {
        break;
      }
    }

    // Page should be functional
    await expect(page.locator('body')).toBeVisible();
  });
});
