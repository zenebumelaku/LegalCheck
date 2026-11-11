import { expect, test } from '@playwright/test';

async function registerUser(page: any) {
  const email = `qa-chat-${Date.now()}-${Math.random().toString(36).slice(2)}@legalcheck.et`;
  await page.goto('/register');
  await page.locator('input[placeholder="E.g., Bethlehem Haile"]').fill('Chat QA User');
  await page.locator('input[placeholder="E.g., Addis Agro-Industrial PLC"]').fill('Chat QA Org');
  await page.locator('input[placeholder="hr@organization.et"]').fill(email);
  await page.locator('input[placeholder="At least 12 characters"]').fill('AveryStrongPassword123!');
  await page.getByRole('button', { name: /Complete Registration/i }).click();
  await expect(page).toHaveURL(/\/dashboard/);
  return email;
}

test('legal chat page loads for an authenticated user', async ({ page }) => {
  await registerUser(page);
  await page.goto('/legal-chat');

  await expect(page.locator('#legal-question-input')).toBeVisible();
  await expect(page.getByText(/Ask questions with source citations/i)).toBeVisible();
  await expect(page.getByText(/Redis cache/i)).toBeVisible();

  await page.locator('#legal-question-input').fill('What are the statutory rules for probation in Ethiopia?');
  await expect(page.locator('#legal-question-input')).toHaveValue(/probation/i);
});
