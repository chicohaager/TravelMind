import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '../.auth/user.json');

/**
 * Global setup for authenticated tests
 * Creates a test user and saves the authentication state
 */
setup('authenticate', async ({ page }) => {
  // Check if we have a test user configured
  const testUser = process.env.E2E_TEST_USER || 'e2e-test';
  const testPassword = process.env.E2E_TEST_PASSWORD || 'e2e-test-password';
  const testEmail = process.env.E2E_TEST_EMAIL || 'e2e@test.local';

  // Go to login page
  await page.goto('/login');

  // Try to login first (user might already exist)
  await page.getByLabel(/username/i).fill(testUser);
  await page.getByLabel(/password/i).fill(testPassword);
  await page.getByRole('button', { name: /login|anmelden/i }).click();

  // Check if login was successful or if we need to register
  try {
    await page.waitForURL('**/trips', { timeout: 5000 });
  } catch {
    // Login failed, try to register
    await page.goto('/register');

    await page.getByLabel(/username/i).fill(testUser);
    await page.getByLabel(/email/i).fill(testEmail);
    await page.getByLabel(/password/i).first().fill(testPassword);

    // Some forms have password confirmation
    const confirmPassword = page.getByLabel(/confirm|wiederholen/i);
    if (await confirmPassword.isVisible()) {
      await confirmPassword.fill(testPassword);
    }

    await page.getByRole('button', { name: /register|registrieren/i }).click();

    // Wait for successful registration (redirects to trips or dashboard)
    await page.waitForURL('**/trips', { timeout: 10000 });
  }

  // Verify we're logged in
  await expect(page.locator('text=/trips|reisen/i')).toBeVisible();

  // Save authentication state
  await page.context().storageState({ path: authFile });
});
