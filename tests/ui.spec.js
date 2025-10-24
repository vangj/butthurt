import { test, expect } from '@playwright/test';

test.describe('Butt Hurt Report UI', () => {
  test('renders the landing page', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle('Butt Hurt Report');
    await expect(page.getByRole('heading', { level: 1, name: 'Butt Hurt Report' })).toBeVisible();
    await expect(page.getByLabel('Select language')).toBeVisible();
  });
});
