import { expect, test } from '@playwright/test';

async function registerUser(page: any) {
  const email = `playwright-${Date.now()}-${Math.random().toString(36).slice(2)}@legalcheck.et`;
  await page.goto('/register');
  await page.locator('input[placeholder="E.g., Bethlehem Haile"]').fill('Playwright QA User');
  await page.locator('input[placeholder="E.g., Addis Agro-Industrial PLC"]').fill('Playwright QA Org');
  await page.locator('input[placeholder="hr@organization.et"]').fill(email);
  await page.locator('input[placeholder="At least 12 characters"]').fill('AveryStrongPassword123!');
  await page.getByRole('button', { name: /Complete Registration/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  return email;
}

test('user can register and reach the dashboard', async ({ page }) => {
  await registerUser(page);
  await expect(page.getByText(/Dashboard/i).first()).toBeVisible();
  await expect(page.getByText(/LegalCheck Ethiopia/i).first()).toBeVisible();
});
