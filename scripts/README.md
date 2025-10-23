# Scripts Directory

This directory contains small utility scripts that support the build pipeline.

## `build-radio-on-values.mjs`

Generates `www/js/radio-on-values.js` by inspecting the localized PDF widget metadata (`python/csv/blank_form_<lang>.csv`) and the shared radio group definition (`www/js/radio-groups.js`). The script ensures the web client uses the correct PDF on-values for every language when exporting filled forms.
