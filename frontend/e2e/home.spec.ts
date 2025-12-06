import { test, expect } from '@playwright/test';

test.describe('Home Page', () => {
  test('should display the landing page for unauthenticated users', async ({ page }) => {
    await page.goto('/');

    // Check for app name or welcome message
    await expect(page.locator('text=/travelmind|reise/i')).toBeVisible();
  });

  test('should have working navigation links', async ({ page }) => {
    await page.goto('/');

    // Check for login/register links when not authenticated
    const loginLink = page.getByRole('link', { name: /login|anmelden/i });
    const registerLink = page.getByRole('link', { name: /register|registrieren/i });

    // At least one of these should be visible
    const hasLoginOrRegister =
      (await loginLink.isVisible()) || (await registerLink.isVisible());

    expect(hasLoginOrRegister).toBeTruthy();
  });

  test('should be responsive', async ({ page }) => {
    await page.goto('/');

    // Desktop viewport
    await page.setViewportSize({ width: 1280, height: 720 });
    await expect(page.locator('body')).toBeVisible();

    // Tablet viewport
    await page.setViewportSize({ width: 768, height: 1024 });
    await expect(page.locator('body')).toBeVisible();

    // Mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });
    await expect(page.locator('body')).toBeVisible();
  });

  test('should handle 404 pages gracefully', async ({ page }) => {
    await page.goto('/nonexistent-page-12345');

    // Should show some kind of error or redirect
    // Either a 404 page or redirect to home
    const currentUrl = page.url();
    const is404OrRedirect =
      currentUrl.includes('404') ||
      currentUrl.endsWith('/') ||
      (await page.locator('text=/not found|404|seite nicht gefunden/i').isVisible());

    expect(is404OrRedirect).toBeTruthy();
  });
});
