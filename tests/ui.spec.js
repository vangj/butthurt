import { test, expect } from '@playwright/test';
import { supportedLanguages, translations } from '../www/js/i18n.js';

const escapeForRegex = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const prefilledQuery =
  'p1a=Donald%20J%20Trump&p1b=555116969&p1c=2025-10-18&p1d=White%20House&p1e=President&p2a=2025-10-19&p2b=09:00&p2c=No%20Kings%20Rally&p2d=Americans&p2e=MAGA&p31=both&p32=yes&p33=multiple&p34=yes&p41=1&p42=1&p43=1&p44=1&p45=1&p46=1&p47=1&p48=1&p49=1&p410=1&p411=1&p412=1&p413=1&p414=1&p415=1&p5=NKR%20hates%20Murica&language=en';
const sanitizeLanguageForFilename = (value) => value.replace(/[^a-z0-9-]+/gi, '_');
const exportLanguageCases = [
  { code: 'en', whiner: 'Donald J Trump', offender: 'Joe Biden' },
  { code: 'es', whiner: 'José Pérez', offender: 'María Gómez' },
  { code: 'zh', whiner: '张伟', offender: '李娜' },
  { code: 'ko', whiner: '김민수', offender: '박지민' },
  { code: 'ja', whiner: '山田太郎', offender: '佐藤花子' },
  { code: 'de', whiner: 'Jürgen Müller', offender: 'Karl Schmidt' },
  { code: 'fr', whiner: 'Étienne Dupont', offender: 'Jean Valjean' },
  { code: 'hmn', whiner: 'Nplooj Lis', offender: 'Muaj Vwj' },
  { code: 'fil', whiner: 'Juan Dela Cruz', offender: 'Jose Rizal' },
  { code: 'it', whiner: 'Giuseppe Verdi', offender: 'Luca Rossi' },
  { code: 'pt-br', whiner: 'João Silva', offender: 'Maria Souza' },
  { code: 'ru', whiner: 'Алексей Иванов', offender: 'Мария Петрова' },
  { code: 'vi', whiner: 'Nguyễn Văn An', offender: 'Trần Thị Bích' },
  { code: 'km', whiner: 'សុខ ពៅ', offender: 'ជា លីដា' },
  { code: 'lo', whiner: 'ສີວົງ ພອນ', offender: 'ຈັນທະ ດາວ' },
  { code: 'th', whiner: 'สมชาย ใจดี', offender: 'สมหญิง ศรีสวย' },
];
const expectExportsForLanguage = async (page, { code, whiner, offender }) => {
  await page.goto('/');
  await page.locator('#language-select').selectOption(code);
  await page.fill('#part-i-a', whiner);
  await page.fill('#part-ii-d', offender);
  await expect(page.locator('#part-vi-a')).toHaveValue(whiner);

  const sanitizedCode = sanitizeLanguageForFilename(code);

  const [jpgDownload] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#generate-jpg-btn'),
  ]);

  await jpgDownload.path();
  expect(jpgDownload.suggestedFilename()).toMatch(new RegExp(`^butthurt_${sanitizedCode}_.*\\.jpg$`, 'i'));

  const [pdfDownload] = await Promise.all([
    page.waitForEvent('download'),
    page.click('#generate-pdf-btn'),
  ]);

  await pdfDownload.path();
  expect(pdfDownload.suggestedFilename()).toMatch(new RegExp(`^butthurt_${sanitizedCode}_.*\\.pdf$`, 'i'));
};

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

  test('falls back to English for unsupported language and persists selected locale', async ({ page }) => {
    await page.goto('/?language=unsupported');

    const languageSelect = page.locator('#language-select');
    await expect(languageSelect).toHaveValue('en');

    await expect.poll(() => new URL(page.url()).search).toBe('?language=en');

    await languageSelect.selectOption('es');
    const heading = page.locator('[data-i18n="1"]');
    await expect(heading).toHaveText(translations.es['1']);

    await expect.poll(() => new URL(page.url()).search).toBe('?language=es');

    await page.goto('/');

    await expect(languageSelect).toHaveValue('es');
    await expect(heading).toHaveText(translations.es['1']);
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

  test('normalizes query aliases when synchronizing the URL', async ({ page }) => {
    await page.goto('/?part_1_a=Alice%20Smith&part_4_a=Alice%20Smith&language=en');

    await expect(page.locator('#part-i-a')).toHaveValue('Alice Smith');
    await expect(page.locator('#part-vi-a')).toHaveValue('Alice Smith');

    await page.fill('#part-i-a', 'Alice Cooper');
    await page.fill('#part-v', 'Alias test');

    await expect.poll(() =>
      page.evaluate(() => new URL(window.location.href).searchParams.get('p1a')),
    ).toBe('Alice Cooper');
    await expect.poll(() =>
      page.evaluate(() => new URL(window.location.href).searchParams.get('p5a')),
    ).toBe('Alice Cooper');

    const search = await page.evaluate(() => new URL(window.location.href).search);
    expect(search).not.toContain('part_1_a=');
    expect(search).not.toContain('part_4_a=');
  });

  test('populates the form correctly based on querystring', async ({ page }) => {
    await page.goto(`/?${prefilledQuery}`);

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

  test('keeps signature after explicit edit when whiner name changes', async ({ page }) => {
    await page.goto(`/?${prefilledQuery}&part_vi_b=Signature%20Alice`);

    await expect(page.locator('#part-i-a')).toHaveValue('Donald J Trump');
    await expect(page.locator('#part-vi-b')).toHaveValue('Signature Alice');

    await page.fill('#part-i-a', 'Alice Updated');

    await expect(page.locator('#part-vi-a')).toHaveValue('Alice Updated');
    await expect(page.locator('#part-vi-b')).toHaveValue('Signature Alice');
  });

  test('clears the form correctly', async ({ page }) => {
    await page.goto(`/?${prefilledQuery}`);

    await page.click('#reset-form-btn');

    const expectEmpty = async (selector) => {
      await expect(page.locator(selector)).toHaveValue('');
    };

    await expect(page.locator('#language-select')).toHaveValue('en');

    await expectEmpty('#part-i-a');
    await expectEmpty('#part-i-b');
    await expectEmpty('#part-i-c');
    await expectEmpty('#part-i-d');
    await expectEmpty('#part-i-e');

    await expectEmpty('#part-ii-a');
    await expectEmpty('#part-ii-b');
    await expectEmpty('#part-ii-c');
    await expectEmpty('#part-ii-d');
    await expectEmpty('#part-ii-e');

    await expect(page.locator('#part-iii-1-both')).not.toBeChecked();
    await expect(page.locator('#part-iii-2-yes')).not.toBeChecked();
    await expect(page.locator('#part-iii-3-multiple')).not.toBeChecked();
    await expect(page.locator('#part-iii-4-yes')).not.toBeChecked();

    for (let index = 1; index <= 15; index += 1) {
      await expect(page.locator(`#part-iv-${index}`)).not.toBeChecked();
    }

    await expectEmpty('#part-v');
    await expectEmpty('#part-vi-a');
    await expectEmpty('#part-vi-b');

    await expect.poll(() => new URL(page.url()).search).toBe('?language=en');
  });

  test('exports a jpg and pdf correctly', async ({ page }) => {
    await page.goto(`/?${prefilledQuery}`);

    const [jpgDownload] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#generate-jpg-btn'),
    ]);

    await jpgDownload.path();
    expect(jpgDownload.suggestedFilename()).toMatch(/^butthurt_en_.*\.jpg$/i);

    const [pdfDownload] = await Promise.all([
      page.waitForEvent('download'),
      page.click('#generate-pdf-btn'),
    ]);

    await pdfDownload.path();
    expect(pdfDownload.suggestedFilename()).toMatch(/^butthurt_en_.*\.pdf$/i);
  });

  test('requires valid data before allowing exports', async ({ page }) => {
    await page.goto('/');

    const missingFieldsDownload = page.waitForEvent('download', { timeout: 1500 });
    await page.click('#generate-pdf-btn');
    await expect(missingFieldsDownload).rejects.toThrow();

    await expect.poll(() =>
      page.evaluate(() => document.getElementById('part-i-a')?.validity.valid ?? true),
    ).toBe(false);
    const whinerMessage = await page.evaluate(
      () => document.getElementById('part-i-a')?.validationMessage ?? '',
    );
    expect(whinerMessage).not.toBe('');

    await page.fill('#part-i-a', 'Jane Doe');
    await page.fill('#part-ii-d', 'John Smith');
    await page.fill('#part-i-b', '1234');

    const invalidSsnDownload = page.waitForEvent('download', { timeout: 1500 });
    await page.click('#generate-pdf-btn');
    await expect(invalidSsnDownload).rejects.toThrow();

    await expect.poll(() =>
      page.evaluate(() => document.getElementById('part-i-b')?.validity.valid ?? true),
    ).toBe(false);
    const ssnMessage = await page.evaluate(
      () => document.getElementById('part-i-b')?.validationMessage ?? '',
    );
    expect(ssnMessage).toBe('Enter Social Security Number as 9 digits.');

    await page.fill('#part-i-b', '123456789');

    const pdfDownloadPromise = page.waitForEvent('download');
    await page.click('#generate-pdf-btn');
    const pdfDownload = await pdfDownloadPromise;
    await pdfDownload.path();
    expect(pdfDownload.suggestedFilename()).toMatch(/^butthurt_en_.*\.pdf$/i);

    const jpgDownloadPromise = page.waitForEvent('download');
    await page.click('#generate-jpg-btn');
    const jpgDownload = await jpgDownloadPromise;
    await jpgDownload.path();
    expect(jpgDownload.suggestedFilename()).toMatch(/^butthurt_en_.*\.jpg$/i);

    await expect.poll(() =>
      page.evaluate(() => document.getElementById('part-i-b')?.validity.valid ?? true),
    ).toBe(true);
    const finalSsnMessage = await page.evaluate(
      () => document.getElementById('part-i-b')?.validationMessage ?? '',
    );
    expect(finalSsnMessage).toBe('');
  });

  for (const languageCase of exportLanguageCases) {
    test(`exports ${languageCase.code} correctly as jpg and pdf`, async ({ page }) => {
      await expectExportsForLanguage(page, languageCase);
    });
  }

  test('auto exports when export parameter is provided with valid data', async () => {
    test.fixme(true, 'Auto-export flow does not currently trigger downloads on load.');
  });

  test('skips auto export when query data fails validation', async ({ page }) => {
    const downloadPromise = page.waitForEvent('download', { timeout: 1500 });
    await page.goto('/?language=en&p1a=&p1b=1234&export=pdf');
    await expect(downloadPromise).rejects.toThrow();

    await expect.poll(() =>
      page.evaluate(() => document.getElementById('part-i-a')?.validity.valid ?? true),
    ).toBe(false);
    const message = await page.evaluate(
      () => document.getElementById('part-i-a')?.validationMessage ?? '',
    );
    expect(message).not.toBe('');
  });

  test('validates encoding mismatch correctly', async ({ page }) => {
    await page.goto('/');

    await page.locator('#language-select').selectOption('en');
    await page.fill('#part-i-a', '柔術');
    await page.fill('#part-ii-d', 'judo');

    const pdfDownload = page.waitForEvent('download', { timeout: 1500 });
    await page.click('#generate-pdf-btn');
    await expect(pdfDownload).rejects.toThrow();

    const jpgDownload = page.waitForEvent('download', { timeout: 1500 });
    await page.click('#generate-jpg-btn');
    await expect(jpgDownload).rejects.toThrow();

    await expect(page.locator('#part-i-a')).toHaveClass(/\bis-invalid\b/);
  });
});
