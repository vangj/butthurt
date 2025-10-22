#!/usr/bin/env node

import { promises as fs } from "node:fs";
import path from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";

import { translations } from "../www/js/i18n.js";
import { radioGroupsDefinition } from "../www/js/radio-groups.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const projectRoot = path.resolve(__dirname, "..");
const csvDirectory = path.join(projectRoot, "python", "pdf");
const outputPath = path.join(projectRoot, "www", "js", "radio-on-values.js");
const fallbackLanguage = "en";

const normalizeLabel = (label) =>
  typeof label === "string"
    ? label
        .normalize("NFKC")
        .replace(/\s+/g, " ")
        .trim()
        .toLowerCase()
    : "";

const sanitizePdfName = (value) => {
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

const parseCsv = (content) => {
  const rows = [];
  const lines = content.split(/\r?\n/).filter((line) => line.length > 0);
  if (!lines.length) {
    return rows;
  }

  const parseLine = (line) => {
    const values = [];
    let current = "";
    let inQuotes = false;

    for (let i = 0; i < line.length; i += 1) {
      const char = line[i];
      if (char === '"') {
        if (inQuotes && line[i + 1] === '"') {
          current += '"';
          i += 1;
        } else {
          inQuotes = !inQuotes;
        }
      } else if (char === "," && !inQuotes) {
        values.push(current);
        current = "";
      } else {
        current += char;
      }
    }
    values.push(current);
    return values;
  };

  const header = parseLine(lines[0]).map((value) => value.trim());
  for (let i = 1; i < lines.length; i += 1) {
    const values = parseLine(lines[i]);
    if (!values.length) continue;
    const row = {};
    header.forEach((key, index) => {
      row[key] = values[index] ?? "";
    });
    rows.push(row);
  }
  return rows;
};

const extractOptionLabel = (tooltip) => {
  if (typeof tooltip !== "string") {
    return "";
  }
  const marker = "Option is";
  const index = tooltip.lastIndexOf(marker);
  if (index === -1) {
    return tooltip.trim();
  }
  return tooltip.slice(index + marker.length).trim();
};

const buildLanguageMapping = (entries) => {
  const mapping = new Map();
  for (const row of entries) {
    if ((row.type || "").toLowerCase() !== "radiobutton") {
      continue;
    }
    const fieldName = row.name;
    if (!fieldName) continue;
    const optionLabel = extractOptionLabel(row.tooltip);
    const normalizedLabel = normalizeLabel(optionLabel);
    if (!normalizedLabel) continue;
    if (!mapping.has(fieldName)) {
      mapping.set(fieldName, new Map());
    }
    const fieldMap = mapping.get(fieldName);
    if (fieldMap && !fieldMap.has(normalizedLabel)) {
      fieldMap.set(normalizedLabel, row.on_value);
    }
  }
  return mapping;
};

const loadCsvData = async () => {
  const files = await fs.readdir(csvDirectory);
  const csvFiles = files
    .filter((file) => file.startsWith("blank_form_") && file.endsWith(".csv"))
    .sort((a, b) => a.localeCompare(b));

  const result = new Map();

  for (const fileName of csvFiles) {
    const language = fileName.slice("blank_form_".length, -4);
    const content = await fs.readFile(path.join(csvDirectory, fileName), "utf8");
    const rows = parseCsv(content);
    const mapping = buildLanguageMapping(rows);
    result.set(language, mapping);
  }

  return result;
};

const getTranslationForOption = (language, labelKey) => {
  const langTable = translations[language] ?? null;
  if (langTable && Object.prototype.hasOwnProperty.call(langTable, labelKey)) {
    return langTable[labelKey];
  }
  const fallbackTable = translations[fallbackLanguage] ?? null;
  if (fallbackTable && Object.prototype.hasOwnProperty.call(fallbackTable, labelKey)) {
    return fallbackTable[labelKey];
  }
  return "";
};

const buildRadioOnValueMap = (csvMappings) => {
  const output = {};
  const sortedLanguages = Array.from(csvMappings.keys()).sort((a, b) => a.localeCompare(b));
  const fallbackFieldMappings = csvMappings.get(fallbackLanguage) ?? new Map();

  for (const language of sortedLanguages) {
    const fieldLabelMap = csvMappings.get(language) ?? new Map();
    output[language] = {};
    for (const group of radioGroupsDefinition) {
      const { fieldName, options } = group;
      const optionMap = {};
      const languageFieldMap = fieldLabelMap.get(fieldName) ?? new Map();
      const fallbackFieldMap = fallbackFieldMappings.get(fieldName) ?? new Map();

      for (const option of options) {
        const translation = getTranslationForOption(language, option.labelKey);
        const normalizedLabel = normalizeLabel(translation);
        let onValue = languageFieldMap.get(normalizedLabel);

        if (!onValue) {
          // Attempt to reuse the fallback (English) on-state if available.
          const fallbackTranslation = getTranslationForOption(fallbackLanguage, option.labelKey);
          const fallbackNormalized = normalizeLabel(fallbackTranslation);
          if (fallbackFieldMap instanceof Map && fallbackFieldMap.has(fallbackNormalized)) {
            onValue = fallbackFieldMap.get(fallbackNormalized);
          }
        }

        if (!onValue) {
          onValue = sanitizePdfName(translation || option.value);
        }

        optionMap[option.value] = onValue;
      }
      output[language][fieldName] = optionMap;
    }
  }

  return output;
};

const writeOutputFile = async (mapping) => {
  const header = `// This file is auto-generated by scripts/build-radio-on-values.mjs. Do not edit manually.\n`;
  const body = `export const radioOnValueMap = ${JSON.stringify(mapping, null, 2)};\n`;
  await fs.writeFile(outputPath, `${header}${body}`, "utf8");
};

const main = async () => {
  try {
    const csvMappings = await loadCsvData();
    if (csvMappings.size === 0) {
      throw new Error(`No radio button metadata CSV files found in ${csvDirectory}`);
    }
    const radioOnValueMap = buildRadioOnValueMap(csvMappings);
    await writeOutputFile(radioOnValueMap);
  } catch (error) {
    console.error("[build-radio-on-values] Failed:", error);
    process.exitCode = 1;
  }
};

await main();
