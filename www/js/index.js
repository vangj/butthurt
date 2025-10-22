import { PDFDocument } from "https://cdn.skypack.dev/pdf-lib@1.17.1?min";
import { translations, supportedLanguages } from "./i18n.js";
import { radioGroupsDefinition } from "./radio-groups.js";
import { radioOnValueMap } from "./radio-on-values.js";

const rendererWorkerUrl = new URL("./pdf-renderer.worker.js", import.meta.url);
const pdfJsModuleUrl = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.mjs";
const pdfJsWorkerSrc = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/build/pdf.worker.mjs";
const mainThreadRenderLanguages = new Set(["zh", "ja", "ko"]);
const pdfJsStandardFontDataUrl = "https://cdn.jsdelivr.net/npm/pdfjs-dist@4.5.136/standard_fonts/";
const signatureFontFamily = '"Great Vibes", "Brush Script MT", cursive';
let signatureFontReadyPromise = null;
let pdfJsModulePromise = null;

const languageStorageKey = "butthurt:ui-language";
const fallbackLanguage = "en";
const blankPdfDirectory = "pdf";
const blankPdfBaseName = "blank_form";
const languageDisplayNames = {
  en: "English",
  es: "Español",
  zh: "中文",
  ko: "한국어",
  ja: "日本語",
  de: "Deutsch",
  fr: "Français",
  hmn: "Hmoob"
};
const loadingStateLabel = "Generating...";
const sanitizePdfOptionName = (value) => {
  if (typeof value !== "string" || !value.trim()) {
    return "Option";
  }
  return (
    value
      .normalize("NFKC")
      .trim()
      .replace(/[^A-Za-z0-9]+/g, "_")
      .replace(/^_+|_+$/g, "") || "Option"
  );
};

const languageSelect = document.getElementById("language-select");

const normalizeLanguageCode = (code) => {
  if (!code) return null;
  const lowered = code.trim().toLowerCase();
  if (translations[lowered]) {
    return lowered;
  }
  const [basePart] = lowered.split(/[-_]/);
  if (basePart && translations[basePart]) {
    return basePart;
  }
  return null;
};

const queryLanguageInfo = (() => {
  try {
    const params = new URLSearchParams(window.location.search);
    if (!params.has("language")) {
      return { language: null, isValid: false, isPresent: false, raw: null };
    }
    const raw = params.get("language");
    const normalized = normalizeLanguageCode(raw);
    if (normalized) {
      return { language: normalized, isValid: true, isPresent: true, raw };
    }
    if (raw) {
      console.warn(`Unsupported language requested via query string: ${raw}. Falling back to ${fallbackLanguage}.`);
    }
    return { language: fallbackLanguage, isValid: false, isPresent: true, raw };
  } catch (error) {
    console.warn("Unable to parse query language parameter:", error);
    return { language: null, isValid: false, isPresent: false, raw: null };
  }
})();

const shouldUseMainThreadRendering = (language) => {
  const normalized = normalizeLanguageCode(language);
  if (!normalized) {
    return false;
  }
  return mainThreadRenderLanguages.has(normalized);
};

const getStoredLanguage = () => {
  try {
    return normalizeLanguageCode(window.localStorage?.getItem(languageStorageKey));
  } catch {
    return null;
  }
};

const persistLanguage = (lang) => {
  try {
    window.localStorage?.setItem(languageStorageKey, lang);
  } catch {
    // Ignore storage failures (private mode, etc.).
  }
};

const getPreferredLanguage = () => {
  if (queryLanguageInfo.isPresent) {
    return queryLanguageInfo.language ?? fallbackLanguage;
  }

  const stored = getStoredLanguage();
  if (stored) return stored;

  const navigatorLanguages = Array.isArray(navigator.languages)
    ? navigator.languages
    : [navigator.language];

  for (const candidate of navigatorLanguages) {
    const normalized = normalizeLanguageCode(candidate);
    if (normalized) return normalized;
  }

  return fallbackLanguage;
};

const getTranslation = (lang, key) => {
  if (!key) return null;
  const langTable = translations[lang] ?? null;
  if (langTable && Object.prototype.hasOwnProperty.call(langTable, key)) {
    return langTable[key];
  }
  const fallbackTable = translations[fallbackLanguage] ?? null;
  if (fallbackTable && Object.prototype.hasOwnProperty.call(fallbackTable, key)) {
    return fallbackTable[key];
  }
  return null;
};

let activeLanguage = fallbackLanguage;

const formatDateTimeForFilename = (date) => {
  const year = String(date.getFullYear()).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const hours24 = date.getHours();
  const period = hours24 >= 12 ? "PM" : "AM";
  const hours12 = hours24 % 12 === 0 ? 12 : hours24 % 12;
  const hours = String(hours12).padStart(2, "0");
  const milliseconds = String(date.getMilliseconds()).padStart(3, "0");
  return `${year}${month}${day}_${hours}${minutes}_${milliseconds}_${period}`;
};

const getFilenameTimestamp = () => formatDateTimeForFilename(new Date());

const sanitizeForFilename = (value) => value.replace(/[^a-z0-9_-]+/gi, "_");

const buildExportFilename = ({ extension, language, timestamp, pageNum }) => {
  const normalizedLanguage = normalizeLanguageCode(language) ?? fallbackLanguage;
  const safeLanguage = sanitizeForFilename(normalizedLanguage);
  const safeTimestamp = sanitizeForFilename(timestamp ?? getFilenameTimestamp());
  let base = `butthurt_${safeLanguage}_${safeTimestamp}`;
  if (typeof pageNum === "number") {
    const paddedPage = String(pageNum).padStart(2, "0");
    base += `_page-${paddedPage}`;
  }
  return `${base}.${extension}`;
};

const applyTranslations = (lang, { skipStorage = false } = {}) => {
  const normalized = normalizeLanguageCode(lang) ?? fallbackLanguage;
  activeLanguage = normalized;

  if (!skipStorage) {
    persistLanguage(normalized);
  }

  document.documentElement.lang = normalized;

  const elements = document.querySelectorAll("[data-i18n]");
  elements.forEach((element) => {
    const key = element.getAttribute("data-i18n");
    const translation = getTranslation(normalized, key);
    if (typeof translation === "string") {
      element.textContent = translation;
    }
  });

  if (languageSelect && languageSelect.value !== normalized) {
    languageSelect.value = normalized;
  }
};

const populateLanguageSelect = (initialLanguage) => {
  if (!languageSelect) return;
  languageSelect.innerHTML = "";
  const fragment = document.createDocumentFragment();
  for (const lang of supportedLanguages) {
    const option = document.createElement("option");
    option.value = lang;
    option.textContent = languageDisplayNames[lang] ?? lang;
    fragment.append(option);
  }
  languageSelect.append(fragment);
  languageSelect.value = initialLanguage;
  languageSelect.addEventListener("change", (event) => {
    gtagLog(`language_${event.target.value}`, "web", "form");
    applyTranslations(event.target.value);
  });
};

const initializeI18n = () => {
  const initialLanguage = getPreferredLanguage();
  populateLanguageSelect(initialLanguage);
  applyTranslations(initialLanguage, { skipStorage: true });
};

initializeI18n();

const waitForSignatureFont = async () => {
  if (!signatureFontReadyPromise) {
    signatureFontReadyPromise = (async () => {
      if (document.fonts?.load) {
        try {
          await document.fonts.load(`32px ${signatureFontFamily}`, "Signature");
          await document.fonts.ready;
        } catch (error) {
          console.warn("Unable to confirm signature font load:", error);
        }
      }
    })();
  }

  try {
    await signatureFontReadyPromise;
  } catch {
    // Ignore font loading failures; canvas rendering will fall back to default font.
  }
};

const canvasToPngBytes = async (canvas) => {
  if (typeof OffscreenCanvas !== "undefined" && canvas instanceof OffscreenCanvas) {
    const blob = await canvas.convertToBlob({ type: "image/png" });
    return new Uint8Array(await blob.arrayBuffer());
  }

  if (typeof canvas.toBlob === "function") {
    const blob = await new Promise((resolve, reject) => {
      canvas.toBlob((result) => {
        if (result) {
          resolve(result);
        } else {
          reject(new Error("Canvas toBlob returned null."));
        }
      }, "image/png");
    });
    return new Uint8Array(await blob.arrayBuffer());
  }

  if (typeof canvas.toDataURL === "function") {
    const dataUrl = canvas.toDataURL("image/png");
    const response = await fetch(dataUrl);
    return new Uint8Array(await response.arrayBuffer());
  }

  throw new Error("Unsupported canvas type for signature rendering.");
};

const canvasToJpegBlob = async (canvas, quality) => {
  if (typeof OffscreenCanvas !== "undefined" && canvas instanceof OffscreenCanvas) {
    return await canvas.convertToBlob({ type: "image/jpeg", quality });
  }

  if (typeof canvas.toBlob === "function") {
    return await new Promise((resolve, reject) => {
      canvas.toBlob(
        (result) => {
          if (result) {
            resolve(result);
          } else {
            reject(new Error("Canvas toBlob returned null."));
          }
        },
        "image/jpeg",
        quality
      );
    });
  }

  if (typeof canvas.toDataURL === "function") {
    const dataUrl = canvas.toDataURL("image/jpeg", quality);
    const response = await fetch(dataUrl);
    return await response.blob();
  }

  throw new Error("Unsupported canvas type for JPG rendering.");
};

const renderSignatureToImageBytes = async (text, rect) => {
  if (!text || !rect) return null;
  if (!rect.width || !rect.height) return null;
  const trimmed = text.trim();
  if (!trimmed) return null;

  await waitForSignatureFont();

  const deviceRatio =
    typeof window !== "undefined" && window.devicePixelRatio
      ? window.devicePixelRatio
      : 1;
  const widthPx = Math.max(1, Math.round(rect.width * deviceRatio));
  const heightPx = Math.max(1, Math.round(rect.height * deviceRatio));

  let canvas;
  if (typeof OffscreenCanvas !== "undefined") {
    canvas = new OffscreenCanvas(widthPx, heightPx);
  } else {
    canvas = document.createElement("canvas");
    canvas.width = widthPx;
    canvas.height = heightPx;
  }

  const context = canvas.getContext("2d");
  if (!context) {
    console.warn("Unable to acquire canvas context for signature rendering.");
    return null;
  }

  context.clearRect(0, 0, widthPx, heightPx);
  context.scale(deviceRatio, deviceRatio);
  context.clearRect(0, 0, rect.width, rect.height);

  const padding = Math.min(8, rect.width * 0.1);
  let fontSize = Math.min(rect.height * 0.85, 48);

  const applyFont = (size) => {
    context.font = `${size}px ${signatureFontFamily}`;
  };

  applyFont(fontSize);
  let metrics = context.measureText(trimmed);
  const maxTextWidth = Math.max(rect.width - padding * 2, rect.width * 0.25);
  if (metrics.width > maxTextWidth) {
    const scaleFactor = maxTextWidth / metrics.width;
    fontSize = Math.max(rect.height * 0.4, fontSize * scaleFactor);
    applyFont(fontSize);
    metrics = context.measureText(trimmed);
  }

  context.fillStyle = "#000";
  context.textBaseline = "alphabetic";

  const ascent = metrics.actualBoundingBoxAscent ?? fontSize * 0.8;
  const descent = metrics.actualBoundingBoxDescent ?? fontSize * 0.2;
  const yPosition = rect.height / 2 + (ascent - descent) / 2;
  const xPosition = padding;

  context.fillText(trimmed, xPosition, yPosition);

  try {
    return await canvasToPngBytes(canvas);
  } catch (error) {
    console.error("Unable to convert signature canvas to PNG:", error);
    return null;
  }
};

const setTextFields = (form, mappings) => {
  for (const [fieldName, value] of Object.entries(mappings)) {
    const textField = form.getTextField(fieldName);
    textField.setText(value ?? "");
  }
};

const setCheckBoxes = (form, mappings) => {
  for (const [fieldName, checked] of Object.entries(mappings)) {
    const checkBox = form.getCheckBox(fieldName);
    if (checked) {
      checkBox.check();
    } else {
      checkBox.uncheck();
    }
  }
};

const resolveRadioOnValue = (language, fieldName, optionDef) => {
  const languageMap = radioOnValueMap[language]?.[fieldName] ?? null;
  if (languageMap && Object.prototype.hasOwnProperty.call(languageMap, optionDef.value)) {
    return languageMap[optionDef.value];
  }

  const fallbackMap = radioOnValueMap[fallbackLanguage]?.[fieldName] ?? null;
  if (fallbackMap && Object.prototype.hasOwnProperty.call(fallbackMap, optionDef.value)) {
    return fallbackMap[optionDef.value];
  }

  const translatedLabel =
    getTranslation(language, optionDef.labelKey) ??
    getTranslation(fallbackLanguage, optionDef.labelKey) ??
    "";
  if (translatedLabel) {
    return sanitizePdfOptionName(translatedLabel);
  }

  return sanitizePdfOptionName(optionDef.value);
};

const collectRadioSelections = () => {
  const selections = {};
  for (const group of radioGroupsDefinition) {
    const { fieldName, htmlName, options } = group;
    const checkedInputs = Array.from(
      document.querySelectorAll(`input[name="${htmlName}"]:checked`)
    );
    const selectedValue = checkedInputs.length ? checkedInputs[0].value : null;
    if (!selectedValue) {
      selections[fieldName] = null;
      continue;
    }

    const optionDef = options.find((option) => option.value === selectedValue);
    if (!optionDef) {
      selections[fieldName] = null;
      continue;
    }

    const onValue = resolveRadioOnValue(activeLanguage, fieldName, optionDef);
    selections[fieldName] = onValue ?? null;
  }
  return selections;
};

const applyRadioSelections = (form, selections) => {
  for (const [fieldName, onValue] of Object.entries(selections)) {
    let radioGroup;
    try {
      radioGroup = form.getRadioGroup(fieldName);
    } catch (error) {
      console.warn(`Unable to access radio group ${fieldName}:`, error);
      continue;
    }

    if (onValue) {
      try {
        radioGroup.select(onValue);
      } catch (error) {
        console.warn(`Unable to select ${onValue} for ${fieldName}:`, error);
        try {
          radioGroup.clear();
        } catch (clearError) {
          console.warn(`Unable to clear radio group ${fieldName}:`, clearError);
        }
      }
    } else {
      try {
        radioGroup.clear();
      } catch (error) {
        console.warn(`Unable to clear radio group ${fieldName}:`, error);
      }
    }
  }
};

const htmlForm = document.querySelector("form");
const whinerNameInput = document.getElementById("part-i-a");
const authWhinerNameInput = document.getElementById("part-vi-a");
const signatureInput = document.getElementById("part-vi-b");
const offenderInput = document.getElementById("part-ii-d");
const ssnInput = document.getElementById("part-i-b");
const pdfButton = document.getElementById("generate-pdf-btn");
const jpgButton = document.getElementById("generate-jpg-btn");
const isRadioNodeList = (element) =>
  typeof RadioNodeList !== "undefined" && element instanceof RadioNodeList;

const syncFieldValue = (source, target) => {
  if (!source || !target) return;
  if (target.value !== source.value) {
    target.value = source.value;
  }
};

const normalizeSignatureText = (value) =>
  value.trim().replace(/\s+/g, " ");

const updateSignatureFromName = (rawValue, { force = false } = {}) => {
  if (!signatureInput) return;
  if (!force && signatureInput.dataset.signatureSource === "explicit") {
    return;
  }
  const trimmed = rawValue ? normalizeSignatureText(rawValue) : "";
  if (!trimmed) {
    signatureInput.value = "";
    delete signatureInput.dataset.signatureSource;
    return;
  }
  signatureInput.value = trimmed;
  signatureInput.dataset.signatureSource = "derived";
};

const truthyParams = new Set(["1", "true", "yes", "on"]);
const falsyParams = new Set(["0", "false", "no", "off"]);

const setFieldValue = (fieldName, rawValue) => {
  if (!htmlForm) return false;
  if (typeof rawValue !== "string") return false;

  const element = htmlForm.elements.namedItem(fieldName);
  if (!element) return false;

  if (isRadioNodeList(element)) {
    const options = Array.from(
      htmlForm.querySelectorAll(`input[name="${fieldName}"]`)
    );
    const lowered = rawValue.toLowerCase();
    const match = options.find(
      (input) => input.value.toLowerCase() === lowered
    );
    if (match) {
      match.checked = true;
      return true;
    }
    return false;
  }

  if (element instanceof HTMLInputElement) {
    if (element.type === "checkbox") {
      const normalized = rawValue.trim().toLowerCase();
      if (
        normalized &&
        (truthyParams.has(normalized) ||
          normalized === element.value.toLowerCase())
      ) {
        element.checked = true;
        return true;
      }
      if (falsyParams.has(normalized) || normalized === "") {
        element.checked = false;
        return true;
      }
      return false;
    }

    element.value = rawValue;
    return true;
  }

  if (
    element instanceof HTMLTextAreaElement ||
    element instanceof HTMLSelectElement
  ) {
    element.value = rawValue;
    return true;
  }

  return false;
};

const applyQueryParamsToForm = () => {
  if (!htmlForm) return;

  const params = new URLSearchParams(window.location.search);
  if (!params.toString()) return;

  const aliasMap = {
    part_1_a: "part_i_a",
    part_4_a: "part_vi_a",
    part_4_b: "part_vi_b"
  };

  const registerAlias = (from, to) => {
    aliasMap[from] = to;
  };

  for (const suffix of ["a", "b", "c", "d", "e"]) {
    registerAlias(`p1${suffix}`, `part_i_${suffix}`);
    registerAlias(`p2${suffix}`, `part_ii_${suffix}`);
  }

  for (let index = 1; index <= 4; index += 1) {
    registerAlias(`p3${index}`, `part_iii_${index}`);
  }

  for (let index = 1; index <= 15; index += 1) {
    registerAlias(`p4${index}`, `part_iv_${index}`);
  }

  registerAlias("p4a", "part_vi_a");
  registerAlias("p4b", "part_vi_b");
  registerAlias("p5a", "part_vi_a");
  registerAlias("p5", "part_v");

  const seenValues = new Map();
  let hasExplicitSignature = false;

  params.forEach((value, rawKey) => {
    const normalizedKey = rawKey.toLowerCase();
    if (normalizedKey === "p5b") {
      return;
    }
    const canonicalKey =
      aliasMap[rawKey] ?? aliasMap[normalizedKey] ?? rawKey;
    seenValues.set(canonicalKey, value);
    if (canonicalKey === "part_vi_b") {
      hasExplicitSignature = true;
    }
    setFieldValue(canonicalKey, value);

    gtagLog(`querystring_${sanitizeForFilename(canonicalKey)}`, "web", "form");
  });

  const getString = (value) =>
    typeof value === "string" ? value : value != null ? String(value) : "";
  const hasContent = (value) => getString(value).trim().length > 0;

  const part1AValue = seenValues.get("part_i_a");
  const part6AValue = seenValues.get("part_vi_a");
  const resolvedName = hasContent(part1AValue)
    ? getString(part1AValue)
    : hasContent(part6AValue)
    ? getString(part6AValue)
    : "";

  if (hasContent(resolvedName)) {
    setFieldValue("part_i_a", resolvedName);
    setFieldValue("part_vi_a", resolvedName);
    seenValues.set("part_i_a", resolvedName);
    seenValues.set("part_vi_a", resolvedName);
  }

  if (hasExplicitSignature && signatureInput) {
    const explicitValue =
      seenValues.get("part_vi_b") ?? signatureInput.value ?? "";
    signatureInput.value = explicitValue;
    signatureInput.dataset.signatureSource = "explicit";
  } else {
    updateSignatureFromName(resolvedName, { force: true });
    if (hasContent(resolvedName)) {
      seenValues.set("part_vi_b", getString(resolvedName));
    }
  }
};

applyQueryParamsToForm();
doExport();

whinerNameInput?.addEventListener("input", () => {
  syncFieldValue(whinerNameInput, authWhinerNameInput);
  updateSignatureFromName(authWhinerNameInput?.value ?? "");
});

authWhinerNameInput?.addEventListener("input", () => {
  syncFieldValue(authWhinerNameInput, whinerNameInput);
  updateSignatureFromName(authWhinerNameInput.value);
});

if (whinerNameInput && authWhinerNameInput) {
  if (whinerNameInput.value && !authWhinerNameInput.value) {
    authWhinerNameInput.value = whinerNameInput.value;
  } else if (!whinerNameInput.value && authWhinerNameInput.value) {
    whinerNameInput.value = authWhinerNameInput.value;
  }
  updateSignatureFromName(authWhinerNameInput.value);
}
updateSignatureFromName(authWhinerNameInput?.value ?? "");

function validateForm() {
  if (!htmlForm) return true;

  if (whinerNameInput) {
    const whinerValue = whinerNameInput.value.trim();
    whinerNameInput.setCustomValidity(
      whinerValue ? "" : "Please enter the whiner's name."
    );
  }

  if (authWhinerNameInput && whinerNameInput) {
    const whinerValue = whinerNameInput.value.trim();
    const authValue = authWhinerNameInput.value.trim();
    let authMessage = "";

    if (!authValue) {
      authMessage = "Please enter the whiner's name.";
    } else if (whinerValue && authValue !== whinerValue) {
      authMessage = "Printed name must match whiner's name.";
    }

    authWhinerNameInput.setCustomValidity(authMessage);
  }

  if (offenderInput) {
    const offenderValue = offenderInput.value.trim();
    offenderInput.setCustomValidity(
      offenderValue
        ? ""
        : "Please enter the name of the person who hurt your feelings."
    );
  }

  if (ssnInput) {
    const ssnValue = ssnInput.value.trim();
    if (!ssnValue) {
      ssnInput.setCustomValidity("");
    } else if (/^[0-9]{9}$/.test(ssnValue)) {
      ssnInput.setCustomValidity("");
    } else {
      ssnInput.setCustomValidity(
        "Enter Social Security Number as 9 digits."
      );
    }
  }

  return htmlForm.reportValidity();
}

function setButtonsDisabled(disabled) {
  for (const btn of [pdfButton, jpgButton]) {
    if (btn) {
      btn.disabled = disabled;
    }
  }
}

const triggerDownload = (blob, filename) => {
  const downloadUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = filename;
  link.click();
  setTimeout(() => {
    URL.revokeObjectURL(downloadUrl);
  }, 0);
};

const getInputValue = (id) => document.getElementById(id)?.value ?? "";
const isChecked = (id) => document.getElementById(id)?.checked ?? false;

function formatTimeForPdf(rawValue) {
  if (!rawValue) return "";
  const [hourPart, minutePart] = rawValue.split(":");
  const hour = Number.parseInt(hourPart, 10);
  const minute = Number.parseInt(minutePart, 10);

  if (
    Number.isNaN(hour) ||
    Number.isNaN(minute) ||
    hour < 0 ||
    hour > 23 ||
    minute < 0 ||
    minute > 59
  ) {
    return rawValue;
  }

  const period = hour >= 12 ? "PM" : "AM";
  const hour12 = ((hour + 11) % 12) + 1;
  const formattedHour = String(hour12).padStart(2, "0");
  const formattedMinute = String(minute).padStart(2, "0");
  return `${formattedHour}:${formattedMinute} ${period}`;
}

function collectFormValues() {
  return {
    textFields: {
      admin_whiner_name: getInputValue("part-i-a"),
      admin_social_security: getInputValue("part-i-b"),
      admin_report_date: getInputValue("part-i-c"),
      admin_organization: getInputValue("part-i-d"),
      admin_preparer_name: getInputValue("part-i-e"),
      incident_date: getInputValue("part-ii-a"),
      incident_time: formatTimeForPdf(getInputValue("part-ii-b")),
      incident_location: getInputValue("part-ii-c"),
      incident_offender_name: getInputValue("part-ii-d"),
      incident_offender_org: getInputValue("part-ii-e"),
      narrative_text: getInputValue("part-v"),
      auth_whiner_name: getInputValue("part-vi-a")
    },
    signature: getInputValue("part-vi-b"),
    checkboxes: {
      reason_filing_1: isChecked("part-iv-1"),
      reason_filing_4: isChecked("part-iv-2"),
      reason_filing_7: isChecked("part-iv-3"),
      reason_filing_10: isChecked("part-iv-4"),
      reason_filing_13: isChecked("part-iv-5"),
      reason_filing_2: isChecked("part-iv-6"),
      reason_filing_5: isChecked("part-iv-7"),
      reason_filing_8: isChecked("part-iv-8"),
      reason_filing_11: isChecked("part-iv-9"),
      reason_filing_14: isChecked("part-iv-10"),
      reason_filing_3: isChecked("part-iv-11"),
      reason_filing_6: isChecked("part-iv-12"),
      reason_filing_9: isChecked("part-iv-13"),
      reason_filing_12: isChecked("part-iv-14"),
      reason_filing_15: isChecked("part-iv-15")
    },
    radioSelections: collectRadioSelections()
  };
}

function buildBlankPdfPath(language) {
  if (!language) {
    return `${blankPdfDirectory}/${blankPdfBaseName}.pdf`;
  }
  return `${blankPdfDirectory}/${blankPdfBaseName}_${language}.pdf`;
}

function getBlankPdfTemplatePaths(language) {
  const candidates = [];
  const normalized = normalizeLanguageCode(language);
  if (normalized) {
    candidates.push(buildBlankPdfPath(normalized));
  }
  const fallbackPath = buildBlankPdfPath(fallbackLanguage);
  if (!candidates.includes(fallbackPath)) {
    candidates.push(fallbackPath);
  }
  candidates.push(buildBlankPdfPath(null));
  return candidates;
}

async function fetchBlankPdfBytes(language) {
  const candidates = getBlankPdfTemplatePaths(language);
  let lastError = null;

  for (const path of candidates) {
    const url = new URL(path, window.location.href);
    try {
      const response = await fetch(url);
      if (response.ok) {
        return await response.arrayBuffer();
      }

      lastError = new Error(
        `Received status ${response.status} while loading PDF template: ${path}`
      );
      console.warn(lastError.message);
    } catch (error) {
      lastError = error;
      console.warn(`Error fetching PDF template ${path}:`, error);
    }
  }

  throw lastError ?? new Error("Unable to load blank PDF form.");
}

async function createFilledPdfBytes() {
  const pdfBytes = await fetchBlankPdfBytes(activeLanguage);
  const pdfDoc = await PDFDocument.load(pdfBytes, { ignoreEncryption: true });

  const form = pdfDoc.getForm();
  const { textFields, signature, checkboxes, radioSelections } = collectFormValues();

  setTextFields(form, textFields);

  let signatureRect = null;
  let signaturePageIndex = 0;

  let signatureField = null;
  try {
    signatureField = form.getTextField("auth_whiner_signature");
  } catch (error) {
    console.warn("Could not access signature field:", error);
  }

  if (signatureField) {
    if (signature) {
      try {
        const widgets = signatureField.acroField.getWidgets();
        if (widgets.length > 0) {
          const widget = widgets[0];
          const rect = widget.getRectangle();
          signatureRect = {
            x: Number(rect.x) || 0,
            y: Number(rect.y) || 0,
            width: Number(rect.width) || 0,
            height: Number(rect.height) || 0
          };
          signaturePageIndex = 0;
        }
      } catch (error) {
        console.warn("Could not get signature field rect:", error);
      }
    }

    try {
      signatureField.setText("");
    } catch (error) {
      console.warn("Could not reset signature field:", error);
    }
  }

  setCheckBoxes(form, checkboxes);
  applyRadioSelections(form, radioSelections);

  form.flatten();

  let signatureImageBytes = null;
  if (signature && signatureRect && signatureRect.width > 0 && signatureRect.height > 0) {
    try {
      signatureImageBytes = await renderSignatureToImageBytes(signature, signatureRect);
    } catch (error) {
      console.error("Could not render signature image:", error);
    }
  }

  if (signatureImageBytes && signatureRect) {
    try {
      const pages = pdfDoc.getPages();
      const page = pages[signaturePageIndex] ?? pages[0];
      if (!page) {
        throw new Error("Unable to access the signature page.");
      }
      const signatureImage = await pdfDoc.embedPng(signatureImageBytes);
      page.drawImage(signatureImage, {
        x: signatureRect.x,
        y: signatureRect.y,
        width: signatureRect.width,
        height: signatureRect.height
      });
    } catch (error) {
      console.error("Could not draw signature image:", error);
    }
  } else if (signature && signatureRect) {
    try {
      const pages = pdfDoc.getPages();
      const page = pages[signaturePageIndex] ?? pages[0];
      if (!page) {
        throw new Error("Unable to access the signature page.");
      }
      const fallbackFont = await pdfDoc.embedStandardFont("Helvetica");
      const fontSize = Math.min(16, Math.max(10, signatureRect.height * 0.75));
      const xPosition = signatureRect.x + 4;
      const yPosition = signatureRect.y + (signatureRect.height - fontSize) / 2;

      page.drawText(signature, {
        x: xPosition,
        y: yPosition,
        size: fontSize,
        font: fallbackFont,
        color: { type: "RGB", red: 0, green: 0, blue: 0 }
      });
    } catch (error) {
      console.error("Could not draw fallback signature text:", error);
    }
  } else {
    console.log("Skipping signature draw:", {
      hasValue: !!signature,
      hasImage: !!signatureImageBytes,
      hasRect: !!signatureRect
    });
  }

  const filledBytes = await pdfDoc.save();
  return filledBytes instanceof Uint8Array ? filledBytes : new Uint8Array(filledBytes);
}

async function loadPdfJsModule() {
  if (!pdfJsModulePromise) {
    pdfJsModulePromise = import(pdfJsModuleUrl)
      .then((module) => {
        module.GlobalWorkerOptions.workerSrc = pdfJsWorkerSrc;
        module.GlobalWorkerOptions.standardFontDataUrl = pdfJsStandardFontDataUrl;
        return module;
      })
      .catch((error) => {
        pdfJsModulePromise = null;
        throw error;
      });
  }
  return pdfJsModulePromise;
}

async function renderPdfToJpegsMainThread(pdfBytes, { scale = 2, quality = 0.92 } = {}) {
  const { getDocument } = await loadPdfJsModule();
  const data = pdfBytes instanceof Uint8Array ? pdfBytes : new Uint8Array(pdfBytes);
  const loadingTask = getDocument({
    data,
    disableFontFace: false,
    useSystemFonts: true,
    standardFontDataUrl: pdfJsStandardFontDataUrl
  });

  try {
    const pdf = await loadingTask.promise;
    try {
      const pages = [];
      const canvas = document.createElement("canvas");
      const context = canvas.getContext("2d", { alpha: false });
      if (!context) {
        throw new Error("Unable to initialize canvas context.");
      }

      try {
        for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
          const page = await pdf.getPage(pageNum);
          try {
            const viewport = page.getViewport({ scale });
            const width = Math.max(1, Math.floor(viewport.width));
            const height = Math.max(1, Math.floor(viewport.height));
            canvas.width = width;
            canvas.height = height;
            await page.render({ canvasContext: context, viewport }).promise;
            const blob = await canvasToJpegBlob(canvas, quality);
            pages.push({ pageNum, blob });
          } finally {
            page.cleanup?.();
          }
        }
        return pages;
      } finally {
        canvas.width = 0;
        canvas.height = 0;
        if (typeof canvas.remove === "function") {
          canvas.remove();
        }
      }
    } finally {
      pdf.cleanup?.();
    }
  } finally {
    await loadingTask.destroy().catch(() => {});
  }
}

function renderPdfToJpegsWithWorker(pdfBytes, { scale = 2, quality = 0.92 } = {}) {
  const worker = new Worker(rendererWorkerUrl, { type: "module" });
  const pdfBytesCopy = pdfBytes.slice();
  return new Promise((resolve, reject) => {
    const pages = [];

    const cleanup = () => {
      worker.removeEventListener("message", handleMessage);
      worker.removeEventListener("error", handleError);
      worker.terminate();
    };

    const handleMessage = (event) => {
      const data = event.data;
      if (!data) {
        return;
      }

      if (data.type === "page") {
        const blob = new Blob([data.buffer], { type: "image/jpeg" });
        pages.push({ pageNum: data.pageNum, blob });
      } else if (data.type === "complete") {
        cleanup();
        pages.sort((a, b) => a.pageNum - b.pageNum);
        resolve(pages);
      } else if (data.type === "error") {
        cleanup();
        reject(new Error(data.message || "Unable to render PDF as JPG."));
      }
    };

    const handleError = (event) => {
      cleanup();
      reject(event.error || new Error("Unable to render PDF as JPG."));
    };

    worker.addEventListener("message", handleMessage);
    worker.addEventListener("error", handleError);

    worker.postMessage(
      {
        type: "render",
        pdfBytes: pdfBytesCopy.buffer,
        scale,
        quality
      },
      [pdfBytesCopy.buffer]
    );
  });
}

function renderPdfToJpegs(pdfBytes, { scale = 2, quality = 0.92, language = null } = {}) {
  const renderOptions = { scale, quality };
  if (shouldUseMainThreadRendering(language)) {
    return renderPdfToJpegsMainThread(pdfBytes, renderOptions);
  }
  return renderPdfToJpegsWithWorker(pdfBytes, renderOptions);
}

async function runWithLoadingState(button, task, errorMessage) {
  if (!validateForm()) {
    return;
  }

  const labelElement = button?.querySelector("[data-i18n]");
  const originalLabelText = labelElement?.textContent ?? null;
  const originalButtonText = !labelElement && button ? button.textContent : null;

  if (button) {
    if (labelElement) {
      labelElement.textContent = loadingStateLabel;
    } else {
      button.textContent = loadingStateLabel;
    }
  }
  setButtonsDisabled(true);

  try {
    await task();
  } catch (error) {
    console.error(error);
    alert(errorMessage);
  } finally {
    setButtonsDisabled(false);
    if (button) {
      if (
        labelElement &&
        originalLabelText !== null &&
        labelElement.textContent === loadingStateLabel
      ) {
        labelElement.textContent = originalLabelText;
      } else if (
        !labelElement &&
        originalButtonText !== null &&
        button.textContent === loadingStateLabel
      ) {
        button.textContent = originalButtonText;
      }
    }
  }
}

function gtagLog(name, category, label) {
  if (window.gtag) {
    window.gtag("event", name, {
      event_category: category,
      event_label: label,
      value: 1
    });
  }
}

async function handlePdfGeneration() {
  const filledBytes = await createFilledPdfBytes();
  const blob = new Blob([filledBytes], { type: "application/pdf" });
  const languageSuffix = (activeLanguage || "unknown").toLowerCase();
  gtagLog(`generate_${languageSuffix}_pdf`, "export", "pdf");
  const timestamp = getFilenameTimestamp();
  const filename = buildExportFilename({
    extension: "pdf",
    language: activeLanguage,
    timestamp
  });
  triggerDownload(blob, filename);
}

async function handleJpgGeneration() {
  const filledBytes = await createFilledPdfBytes();
  const pages = await renderPdfToJpegs(filledBytes, {
    scale: 2,
    quality: 0.9,
    language: activeLanguage
  });
  if (!pages.length) {
    throw new Error("No pages were rendered from the PDF.");
  }

  const multiPage = pages.length > 1;
  const timestamp = getFilenameTimestamp();
  const baseFilenameOptions = {
    extension: "jpg",
    language: activeLanguage,
    timestamp
  };
  const languageSuffix = (activeLanguage || "unknown").toLowerCase();
  for (const { pageNum, blob } of pages) {
    const filename = buildExportFilename(
      multiPage ? { ...baseFilenameOptions, pageNum } : baseFilenameOptions
    );
    gtagLog(`generate_${languageSuffix}_jpg`, "export", "jpg");
    triggerDownload(blob, filename);
  }
}

function doExport() {
  const params = new URLSearchParams(window.location.search);
  const exportParamRaw = params.get("export");
  if (!exportParamRaw) {
    return;
  }

  const normalized = exportParamRaw.trim().toLowerCase();
  let task = null;
  let errorMessage = "";

  if (normalized === "pdf") {
    task = handlePdfGeneration;
    errorMessage = "We couldn't generate the PDF. Please try again.";
  } else if (normalized === "jpg") {
    task = handleJpgGeneration;
    errorMessage = "We couldn't generate the JPG. Please try again.";
  } else {
    console.warn(`Unsupported export format requested: ${exportParamRaw}`);
    return;
  }

  runWithLoadingState(null, task, errorMessage);
}

pdfButton?.addEventListener("click", () =>
  runWithLoadingState(pdfButton, handlePdfGeneration, "We couldn't generate the PDF. Please try again.")
);

jpgButton?.addEventListener("click", () =>
  runWithLoadingState(jpgButton, handleJpgGeneration, "We couldn't generate the JPG. Please try again.")
);
