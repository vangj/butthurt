import { test, expect } from '@playwright/test';
import { supportedLanguages, translations } from '../www/js/i18n.js';

const escapeForRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

test.describe('Butt Hurt Report UI', () => {
  test('renders the landing page', async ({ page }) => {
    await page.goto('/');

    await expect(page).toHaveTitle('Butt Hurt Report');
    await expect(page.getByRole('heading', { level: 1, name: 'Butt Hurt Report' })).toBeVisible();
    await expect(page.getByLabel('Select language')).toBeVisible();
  });

  test('updates the form labels when the language changes', async ({ page }) => {
    await page.goto('/');

    const languageSelect = page.locator('#language-select');
    await expect(languageSelect).toBeVisible();

    const heading = page.locator('[data-i18n="1"]');

    for (const language of supportedLanguages) {
      const expectedHeading = translations[language]?.['1'];
      if (!expectedHeading) {
        throw new Error(`Missing heading translation for language: ${language}`);
      }

      await languageSelect.selectOption(language);
      await expect(languageSelect).toHaveValue(language);
      await expect(heading).toHaveText(expectedHeading);
      const translatedLabels = page.locator('label[data-i18n]');
      const labelCount = await translatedLabels.count();
      for (let index = 0; index < labelCount; index += 1) {
        const label = translatedLabels.nth(index);
        const translationKey = await label.getAttribute('data-i18n');
        if (!translationKey) {
          continue;
        }
        const expectedLabel = translations[language]?.[translationKey];
        if (!expectedLabel) {
          throw new Error(`Missing label translation for key "${translationKey}" in language: ${language}`);
        }
        await expect(label).toHaveText(expectedLabel);
      }
      const languageMatcher = new RegExp(`[?&]language=${escapeForRegex(language)}(?:[&#]|$)`);
      await expect(page).toHaveURL(languageMatcher);
    }
  });
});
