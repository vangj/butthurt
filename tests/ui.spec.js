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

  test('creates the correct querystring key-value pairs', async ({ page }) => {
    await page.goto('/');

    await page.fill('#part-i-a', 'Donald J Trump');
    await page.fill('#part-i-b', '11122333');
    await page.fill('#part-i-c', '2025-10-01');
    await page.fill('#part-i-d', 'White House');
    await page.fill('#part-i-e', 'President');

    await page.fill('#part-ii-a', '2025-01-01');
    await page.fill('#part-ii-b', '09:00');
    await page.fill('#part-ii-c', 'Murica');
    await page.fill('#part-ii-d', 'Muricans');
    await page.fill('#part-ii-e', 'MAGA');

    await page.check('#part-iii-1-both');
    await page.check('#part-iii-2-yes');
    await page.check('#part-iii-3-multiple');
    await page.check('#part-iii-4-yes');

    for (let index = 1; index <= 15; index += 1) {
      await page.check(`#part-iv-${index}`);
    }

    await page.fill('#part-v', 'No Kings Rally hates Murica');
    await expect(page.locator('#part-vi-a')).toHaveValue('Donald J Trump');

    const expectedParams = {
      language: 'en',
      p1a: 'Donald J Trump',
      p1b: '11122333',
      p1c: '2025-10-01',
      p1d: 'White House',
      p1e: 'President',
      p2a: '2025-01-01',
      p2b: '09:00',
      p2c: 'Murica',
      p2d: 'Muricans',
      p2e: 'MAGA',
      p31: 'both',
      p32: 'yes',
      p33: 'multiple',
      p34: 'yes',
      p5: 'No Kings Rally hates Murica',
      p5a: 'Donald J Trump'
    };

    for (let index = 1; index <= 15; index += 1) {
      expectedParams[`p4${index}`] = '1';
    }

    await expect.poll(() => {
      const url = new URL(page.url());
      const params = {};
      url.searchParams.forEach((value, key) => {
        params[key] = value;
      });
      return params;
    }).toEqual(expectedParams);
  });

  test('populates the form correctly based on querystring', async ({ page }) => {
    const query =
      'p1a=Donald%20J%20Trump&p1b=555116969&p1c=2025-10-18&p1d=White%20House&p1e=President&p2a=2025-10-19&p2b=09:00&p2c=No%20Kings%20Rally&p2d=Americans&p2e=MAGA&p31=both&p32=yes&p33=multiple&p34=yes&p41=1&p42=1&p43=1&p44=1&p45=1&p46=1&p47=1&p48=1&p49=1&p410=1&p411=1&p412=1&p413=1&p414=1&p415=1&p5=NKR%20hates%20Murica&language=en';
    await page.goto(`/?${query}`);

    const expectValue = async (selector, value) => {
      await expect(page.locator(selector)).toHaveValue(value);
    };

    await expect(page.locator('#language-select')).toHaveValue('en');

    await expectValue('#part-i-a', 'Donald J Trump');
    await expectValue('#part-i-b', '555116969');
    await expectValue('#part-i-c', '2025-10-18');
    await expectValue('#part-i-d', 'White House');
    await expectValue('#part-i-e', 'President');

    await expectValue('#part-ii-a', '2025-10-19');
    await expectValue('#part-ii-b', '09:00');
    await expectValue('#part-ii-c', 'No Kings Rally');
    await expectValue('#part-ii-d', 'Americans');
    await expectValue('#part-ii-e', 'MAGA');

    await expect(page.locator('#part-iii-1-both')).toBeChecked();
    await expect(page.locator('#part-iii-2-yes')).toBeChecked();
    await expect(page.locator('#part-iii-3-multiple')).toBeChecked();
    await expect(page.locator('#part-iii-4-yes')).toBeChecked();

    for (let index = 1; index <= 15; index += 1) {
      await expect(page.locator(`#part-iv-${index}`)).toBeChecked();
    }

    await expectValue('#part-v', 'NKR hates Murica');
    await expectValue('#part-vi-a', 'Donald J Trump');
    await expectValue('#part-vi-b', 'Donald J Trump');
  });
});
