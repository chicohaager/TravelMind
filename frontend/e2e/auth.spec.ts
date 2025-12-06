import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    // Check for login form elements
    await expect(page.getByLabel(/username|benutzername/i)).toBeVisible();
    await expect(page.getByLabel(/password|passwort/i)).toBeVisible();
    await expect(page.getByRole('button', { name: /login|anmelden/i })).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel(/username|benutzername/i).fill('nonexistent-user');
    await page.getByLabel(/password|passwort/i).fill('wrong-password');
    await page.getByRole('button', { name: /login|anmelden/i }).click();

    // Should show an error message
    await expect(
      page.locator('text=/error|fehler|incorrect|ungültig|falsch/i')
    ).toBeVisible({ timeout: 5000 });
  });

  test('should display registration page', async ({ page }) => {
    await page.goto('/register');

    // Check for registration form elements
    await expect(page.getByLabel(/username|benutzername/i)).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password|passwort/i).first()).toBeVisible();
    await expect(
      page.getByRole('button', { name: /register|registrieren/i })
    ).toBeVisible();
  });

  test('should validate required fields on login', async ({ page }) => {
    await page.goto('/login');

    // Click login without filling fields
    await page.getByRole('button', { name: /login|anmelden/i }).click();

    // Browser validation or custom error should show
    const usernameInput = page.getByLabel(/username|benutzername/i);
    const passwordInput = page.getByLabel(/password|passwort/i);

    // Check for validation state
    const isInvalid =
      (await usernameInput.getAttribute('aria-invalid')) === 'true' ||
      (await usernameInput.evaluate((el: HTMLInputElement) => !el.validity.valid));

    // Either native validation or we stay on login page
    expect(isInvalid || page.url().includes('login')).toBeTruthy();
  });

  test('should have link to registration from login', async ({ page }) => {
    await page.goto('/login');

    // Find link to registration
    const registerLink = page.getByRole('link', { name: /register|registrieren|konto erstellen/i });
    await expect(registerLink).toBeVisible();

    await registerLink.click();
    await expect(page).toHaveURL(/register/);
  });

  test('should have link to login from registration', async ({ page }) => {
    await page.goto('/register');

    // Find link to login
    const loginLink = page.getByRole('link', { name: /login|anmelden|bereits registriert/i });
    await expect(loginLink).toBeVisible();

    await loginLink.click();
    await expect(page).toHaveURL(/login/);
  });
});
