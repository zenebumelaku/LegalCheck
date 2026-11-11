import { expect, test } from '@playwright/test';

test('landing page renders the legal Q&A product overview', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /Ask Ethiopian labour law questions with traceable source evidence/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Ask a Legal Question/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /Browse Legal Sources/i })).toBeVisible();
});
