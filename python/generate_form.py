import argparse
import csv
import json
import os
import re
from collections import defaultdict, deque
from pathlib import Path
from dataclasses import dataclass
import math
import pymupdf as pm

BLACK = (0, 0, 0)

DEFAULT_TEXT_FONT = "Helvetica"
DEFAULT_TEXT_SIZE = 10
DEFAULT_BOLD_FONT = "Helvetica-Bold"
FONT_DIR = Path(__file__).resolve().parent / "fonts"
SIGNATURE_FONT_PATH = FONT_DIR / "GreatVibes-Regular.ttf"
SIGNATURE_FONT_NAME = "GreatVibes"

SECTION_HEADER_HEIGHT = 28
MIN_SIGNATURE_REGION_HEIGHT = 48
MIN_TEXT_WIDGET_BOTTOM_MARGIN = 10

PART_ROMANS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
}
PART_PREFIX_PART: dict[str, int] = {
    "injury": 3,
    "reason_filing": 4,
}

DEFAULT_LANGUAGE = "en"
DEFAULT_I18N_PATH = Path(__file__).resolve().parent / "i18n.csv"

@dataclass
class FontProfile:
    regular_path: Path | None = None
    bold_path: Path | None = None
    regular_name: str = DEFAULT_TEXT_FONT
    bold_name: str = DEFAULT_BOLD_FONT


FONT_PROFILES: dict[str, FontProfile] = {
    "zh": FontProfile(
        regular_path=FONT_DIR / "SourceHanSansSC-Regular.otf",
        bold_path=FONT_DIR / "SourceHanSansSC-Bold.otf",
        regular_name="SourceHanSansSC-Regular",
        bold_name="SourceHanSansSC-Bold",
    ),
    "ja": FontProfile(
        regular_path=FONT_DIR / "NotoSansCJKjp-Regular.otf",
        bold_path=FONT_DIR / "NotoSansCJKjp-Bold.otf",
        regular_name="NotoSansCJKjp-Regular",
        bold_name="NotoSansCJKjp-Bold",
    ),
    "ko": FontProfile(
        regular_path=FONT_DIR / "NotoSansCJKkr-Regular.otf",
        bold_path=FONT_DIR / "NotoSansCJKkr-Bold.otf",
        regular_name="NotoSansCJKkr-Regular",
        bold_name="NotoSansCJKkr-Bold",
    ),
}

CURRENT_TEXT_FONT = DEFAULT_TEXT_FONT
CURRENT_BOLD_FONT = DEFAULT_BOLD_FONT


def configure_fonts_for_language(page: pm.Page, language: str) -> tuple[str, str]:
    profile = FONT_PROFILES.get(language)
    if not profile:
        return DEFAULT_TEXT_FONT, DEFAULT_BOLD_FONT

    regular_name = DEFAULT_TEXT_FONT
    bold_name = DEFAULT_BOLD_FONT

    try:
        if profile.regular_path and profile.regular_path.exists():
            page.insert_font(
                fontname=profile.regular_name,
                fontfile=str(profile.regular_path),
            )
            regular_name = profile.regular_name
        else:
            print(f"Warning: Regular font file not found for language '{language}'. Using default font.")
            regular_name = DEFAULT_TEXT_FONT
    except Exception as exc:
        print(f"Warning: Failed to load regular font for language '{language}': {exc}")
        regular_name = DEFAULT_TEXT_FONT

    try:
        if profile.bold_path and profile.bold_path.exists():
            page.insert_font(
                fontname=profile.bold_name,
                fontfile=str(profile.bold_path),
            )
            bold_name = profile.bold_name
        else:
            print(f"Warning: Bold font file not found for language '{language}'. Using default bold font.")
            bold_name = DEFAULT_BOLD_FONT
    except Exception as exc:
        print(f"Warning: Failed to load bold font for language '{language}': {exc}")
        bold_name = DEFAULT_BOLD_FONT

    return regular_name, bold_name

I18N_KEYS: dict[str, str] = {
    "title": "1",
    "privacy_statement": "2",
    "principal_purpose_label": "3",
    "principal_purpose_text": "4",
    "routine_uses_label": "5",
    "routine_uses_text": "6",
    "part_i_header": "7",
    "admin_whiner_name_label": "8",
    "admin_social_security_label": "9",
    "admin_report_date_label": "10",
    "admin_organization_label": "11",
    "admin_preparer_label": "12",
    "part_ii_header": "13",
    "incident_date_label": "14",
    "incident_time_label": "15",
    "incident_location_label": "16",
    "incident_offender_name_label": "17",
    "incident_offender_org_label": "18",
    "part_iii_header": "19",
    "injury_question1": "20",
    "left": "21",
    "right": "22",
    "both": "23",
    "injury_question2": "24",
    "yes": "25",
    "no": "26",
    "maybe": "27",
    "injury_question3": "28",
    "multiple": "29",
    "injury_question4": "30",
    "part_iv_header": "31",
    "reason_thin_skinned": "32",
    "reason_fix_problems": "33",
    "reason_two_beers": "34",
    "reason_wimp": "35",
    "reason_easily_hurt": "36",
    "reason_hands_pockets": "37",
    "reason_hormones": "38",
    "reason_not_signed_up": "39",
    "reason_not_offered_post_brief": "40",
    "reason_crybaby": "41",
    "reason_not_hero": "42",
    "reason_requested_post_brief": "43",
    "reason_want_mommy": "44",
    "reason_weather": "45",
    "reason_all_above": "46",
    "part_v_header": "47",
    "part_vi_header": "48",
    "auth_whiner_name_label": "49",
    "auth_signature_label": "50",
}

TEXT_TOOLTIPS: dict[str, str] = {
    "admin_whiner_name": "Part I, Administrative Data, Question A, Whiner's Name (Last, First, MI)",
    "admin_social_security": "Part I, Administrative Data, Question B, Social Security Number",
    "admin_report_date": "Part I, Administrative Data, Question C, Date of Report",
    "admin_organization": "Part I, Administrative Data, Question D, Organization",
    "admin_preparer_name": "Part I, Administrative Data, Question E, Name & Title of Person Filling Out This Form",
    "incident_date": "Part II, Incident Report, Question A, Date Feelings Were Hurt",
    "incident_time": "Part II, Incident Report, Question B, Time of Hurtfulness",
    "incident_location": "Part II, Incident Report, Question C, Location of Hurtful Incident",
    "incident_offender_name": "Part II, Incident Report, Question D, Name of Real Man/Woman Who Hurt Your Sensitive Feelings",
    "incident_offender_org": "Part II, Incident Report, Question E, Organization",
    "narrative_text": "Part V, Narrative",
    "auth_whiner_name": "Part VI, Authentication, Question A, Printed Name of Whiner",
    "auth_whiner_signature": "Part VI, Authentication, Question B, Signature",
}

_TOOLTIP_QUEUE: defaultdict[str, list[str]] = defaultdict(list)


def _sanitize_radio_export(value: str, used: set[str]) -> str:
    """Convert an option label into a safe PDF name and keep it unique per group."""
    sanitized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip())
    sanitized = sanitized.strip("_") or "Option"
    candidate = sanitized
    index = 1
    while candidate in used:
        candidate = f"{sanitized}_{index}"
        index += 1
    used.add(candidate)
    return candidate

WIDGET_TYPE_MAP = {
    pm.PDF_WIDGET_TYPE_BUTTON: "button",
    pm.PDF_WIDGET_TYPE_CHECKBOX: "checkbox",
    pm.PDF_WIDGET_TYPE_RADIOBUTTON: "radiobutton",
    pm.PDF_WIDGET_TYPE_TEXT: "text",
    pm.PDF_WIDGET_TYPE_LISTBOX: "listbox",
    pm.PDF_WIDGET_TYPE_COMBOBOX: "combobox",
    pm.PDF_WIDGET_TYPE_SIGNATURE: "signature",
    pm.PDF_WIDGET_TYPE_UNKNOWN: "unknown",
}

class TranslationCatalog:
    """Load translation strings from a CSV and provide language-specific access."""

    def __init__(self, csv_path: Path) -> None:
        if not csv_path.exists():
            raise FileNotFoundError(f"i18n file not found: {csv_path}")
        self._csv_path = csv_path
        self._translations: dict[str, dict[str, str]] = defaultdict(dict)
        with csv_path.open("r", newline="", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)
            if not reader.fieldnames:
                raise ValueError(f"i18n file {csv_path} is missing headers.")
            normalized_fields = [field.strip().lower() for field in reader.fieldnames]
            if "id" not in normalized_fields:
                raise ValueError(f"i18n file {csv_path} must include an 'id' column.")
            id_index = normalized_fields.index("id")
            language_columns = [
                (field, normalized_fields[idx])
                for idx, field in enumerate(reader.fieldnames)
                if idx != id_index
            ]
            for row in reader:
                row_id = (row.get(reader.fieldnames[id_index]) or "").strip()
                if not row_id:
                    continue
                for original_name, normalized_name in language_columns:
                    value = row.get(original_name, "")
                    self._translations.setdefault(normalized_name, {})[row_id] = value.strip()
        self._available_languages = {lang for lang in self._translations if lang}

    def get_translator(self, language: str) -> "Translator":
        normalized = language.strip().lower()
        if normalized not in self._available_languages:
            raise ValueError(
                f"Language '{language}' not found in {self._csv_path}. Available languages: "
                f"{', '.join(sorted(self._available_languages)) or 'none'}"
            )
        fallback = self._translations.get(DEFAULT_LANGUAGE, {})
        selected = self._translations.get(normalized, {})
        return Translator(language=normalized, translations=selected, fallback=fallback)

    @property
    def languages(self) -> set[str]:
        """Return the set of available language codes."""
        return set(self._available_languages)

class Translator:
    """Provide simple access to translation strings with fallback to English."""

    def __init__(
        self,
        *,
        language: str,
        translations: dict[str, str],
        fallback: dict[str, str],
    ) -> None:
        self.language = language
        self._translations = translations
        self._fallback = fallback

    def text(self, key: str) -> str:
        translation_id = I18N_KEYS.get(key)
        if translation_id is None:
            raise KeyError(f"Translation key '{key}' is not defined.")
        value = self._translations.get(translation_id)
        if value:
            return value
        return self._fallback.get(translation_id, "")

def part_label_from_field(field_name: str) -> str:
    for prefix, part_number in PART_PREFIX_PART.items():
        if field_name.startswith(prefix):
            return f"Part {PART_ROMANS.get(part_number, str(part_number))}"
    match = re.match(r"part(\d+)", field_name)
    if match:
        number = int(match.group(1))
        return f"Part {PART_ROMANS.get(number, str(number))}"
    return "Part"


def question_number_from_field(field_name: str) -> str:
    match = re.search(r"question(\d+)", field_name)
    return match.group(1) if match else ""


def apply_tooltips(page: pm.Page) -> None:
    queues = {name: deque(values) for name, values in _TOOLTIP_QUEUE.items()}
    for widget in page.widgets():
        name = widget.field_name or ""
        tooltip: str | None = None
        queue = queues.get(name)
        if queue:
            tooltip = queue.popleft()
        else:
            if widget.field_type == pm.PDF_WIDGET_TYPE_TEXT:
                tooltip = TEXT_TOOLTIPS.get(name)
            elif widget.field_type == pm.PDF_WIDGET_TYPE_RADIOBUTTON:
                option_label = widget.field_label or ""
                question = question_number_from_field(name)
                part_label = part_label_from_field(name)
                tooltip = f"{part_label}, Question {question}, Option is {option_label}" if question else f"{part_label}, Option is {option_label}"
            elif widget.field_type == pm.PDF_WIDGET_TYPE_CHECKBOX:
                option_label = widget.field_label or ""
                part_label = part_label_from_field(name)
                tooltip = f"{part_label}, Option is {option_label}"

        if tooltip:
            widget.field_label = tooltip
            widget.update()
    _TOOLTIP_QUEUE.clear()


def collect_metadata(doc: pm.Document) -> list[dict[str, object]]:
    metadata: list[dict[str, object]] = []
    for page_index in range(len(doc)):
        page = doc[page_index]
        widgets = list(page.widgets())
        if not widgets:
            continue
        for widget in widgets:
            rect = widget.rect
            widget_type = WIDGET_TYPE_MAP.get(widget.field_type, str(widget.field_type))
            flags = widget.field_flags
            readonly = bool(flags & 1)
            tooltip = widget.field_label or ""
            on_value = ""
            export_values = ""

            if widget.field_type in (
                pm.PDF_WIDGET_TYPE_BUTTON,
                pm.PDF_WIDGET_TYPE_CHECKBOX,
                pm.PDF_WIDGET_TYPE_RADIOBUTTON,
            ):
                try:
                    on_state = widget.on_state()
                    if on_state not in (None, False, "Off"):
                        on_value = str(on_state)
                except Exception:
                    on_value = ""
                try:
                    states = widget.button_states()
                    if states:
                        export_values = json.dumps(states)
                except Exception:
                    export_values = ""
            elif widget.field_type in (
                pm.PDF_WIDGET_TYPE_COMBOBOX,
                pm.PDF_WIDGET_TYPE_LISTBOX,
            ):
                values = getattr(widget, "choice_values", None)
                if values:
                    export_values = json.dumps(values)

            metadata.append(
                {
                    "page": page_index + 1,
                    "name": widget.field_name,
                    "type": widget_type,
                    "x0": rect.x0,
                    "y0": rect.y0,
                    "x1": rect.x1,
                    "y1": rect.y1,
                    "flags": flags,
                    "readonly": readonly,
                    "tooltip": tooltip,
                    "on_value": on_value,
                    "export_values": export_values,
                    "xref": widget.xref,
                }
            )
    return metadata


def export_metadata(metadata: list[dict[str, object]], pdf_path: str) -> None:
    csv_path = Path(pdf_path).with_suffix(".csv")
    header = [
        "page",
        "name",
        "type",
        "x0",
        "y0",
        "x1",
        "y1",
        "flags",
        "readonly",
        "tooltip",
        "on_value",
        "export_values",
        "xref",
    ]
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        writer.writerow(header)
        for row in metadata:
            writer.writerow(
                [
                    row["page"],
                    row["name"],
                    row["type"],
                    f"{row['x0']:.2f}",
                    f"{row['y0']:.2f}",
                    f"{row['x1']:.2f}",
                    f"{row['y1']:.2f}",
                    row["flags"],
                    row["readonly"],
                    row["tooltip"],
                    row["on_value"],
                    row["export_values"],
                    row["xref"],
                ]
            )


def _ensure_acroform_xref(doc: pm.Document) -> int:
    catalog_xref = doc.pdf_catalog()
    acroform_ref = doc.xref_get_key(catalog_xref, "AcroForm")
    if not acroform_ref or acroform_ref[0] is None:
        raise RuntimeError("Document is missing an AcroForm dictionary.")
    if acroform_ref[0] == "dict":
        new_xref = doc.get_new_xref()
        doc.update_object(new_xref, acroform_ref[1])
        doc.xref_set_key(catalog_xref, "AcroForm", f"{new_xref} 0 R")
        return new_xref
    if acroform_ref[0] == "xref":
        return int(acroform_ref[1].split()[0])
    raise RuntimeError(f"Unsupported AcroForm reference type: {acroform_ref[0]}")


def _parse_ref_array(array_str: str) -> list[str]:
    return re.findall(r"\d+\s+\d+\s+R", array_str)


def _format_ref_array(refs: list[str]) -> str:
    return f"[{' '.join(refs)}]" if refs else "[]"


def _replace_on_state_in_dict(ap_dict_str: str, new_state: str) -> tuple[str, bool]:
    match = re.search(r"(/N\s*<<)(.*?)(>>)", ap_dict_str, re.DOTALL)
    if not match:
        return ap_dict_str, False
    prefix, inner, suffix = match.groups()
    replaced = False

    def repl(m: re.Match) -> str:
        nonlocal replaced
        name, ref = m.group(1), m.group(2)
        if name == "Off" or replaced:
            return m.group(0)
        replaced = True
        return f"/{new_state} {ref}"

    updated_inner = re.sub(r"/([^/\s]+)\s+(\d+\s+\d+\s+R)", repl, inner)
    if not replaced:
        return ap_dict_str, False
    updated = f"{prefix}{updated_inner}{suffix}"
    return ap_dict_str[: match.start()] + updated + ap_dict_str[match.end():], True


def _rename_widget_on_state(doc: pm.Document, widget_xref: int, new_state: str) -> None:
    ap_ref = doc.xref_get_key(widget_xref, "AP")
    if not ap_ref or ap_ref[0] is None:
        return
    if ap_ref[0] == "dict":
        updated, changed = _replace_on_state_in_dict(ap_ref[1], new_state)
        if changed:
            doc.xref_set_key(widget_xref, "AP", updated)
    elif ap_ref[0] == "xref":
        ap_xref = int(ap_ref[1].split()[0])
        ap_dict = doc.xref_object(ap_xref)
        updated, changed = _replace_on_state_in_dict(ap_dict, new_state)
        if changed:
            doc.update_object(ap_xref, updated)


def _rects_close(rect: pm.Rect, stored_rect: tuple[float, float, float, float], tol: float = 0.05) -> bool:
    x0, y0, x1, y1 = stored_rect
    return (
        abs(rect.x0 - x0) <= tol
        and abs(rect.y0 - y0) <= tol
        and abs(rect.x1 - x1) <= tol
        and abs(rect.y1 - y1) <= tol
    )


def _pop_matching_update(
    entries: list[dict[str, object]] | None, rect: pm.Rect, page_index: int
) -> dict[str, object] | None:
    if not entries:
        return None
    for idx, entry in enumerate(entries):
        stored_rect = entry.get("rect")
        entry_page = entry.get("page_index")
        if stored_rect and _rects_close(rect, stored_rect) and (
            entry_page is None or entry_page == page_index
        ):
            return entries.pop(idx)
    return entries.pop(0) if entries else None


def fix_radio_button_groups(doc: pm.Document, updates: list[dict[str, object]]) -> None:
    if not updates:
        return

    updates_by_field: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    fallback_updates: list[dict[str, object]] = []
    for index, entry in enumerate(updates):
        if not isinstance(entry, dict):
            continue
        normalized = dict(entry)
        normalized.setdefault("order", index)
        rect = normalized.get("rect")
        if rect:
            normalized["rect"] = tuple(float(value) for value in rect)
        else:
            normalized["rect"] = None
        page_idx = normalized.get("page_index")
        normalized["page_index"] = int(page_idx) if isinstance(page_idx, int) else None
        field_name = normalized.get("field_name") or ""
        if field_name:
            updates_by_field[field_name].append(normalized)
        else:
            fallback_updates.append(normalized)

    for entries in updates_by_field.values():
        entries.sort(key=lambda item: item.get("order", 0))
    fallback_updates.sort(key=lambda item: item.get("order", 0))

    try:
        acroform_xref = _ensure_acroform_xref(doc)
    except RuntimeError:
        return

    fields_ref = doc.xref_get_key(acroform_xref, "Fields")
    if not fields_ref or fields_ref[0] != "array":
        fields_entries: list[str] = []
    else:
        fields_entries = _parse_ref_array(fields_ref[1])

    groups: defaultdict[str, list[tuple[pm.Widget, dict[str, object], int]]] = defaultdict(list)
    for page_index, page in enumerate(doc):
        for widget in page.widgets():
            if widget.field_type != pm.PDF_WIDGET_TYPE_RADIOBUTTON:
                continue
            initial_field = widget.field_name or ""
            entry = _pop_matching_update(updates_by_field.get(initial_field), widget.rect, page_index)
            resolved_field = initial_field

            if entry is None:
                for candidate_field, candidate_entries in updates_by_field.items():
                    if candidate_field == initial_field:
                        continue
                    candidate_entry = _pop_matching_update(candidate_entries, widget.rect, page_index)
                    if candidate_entry:
                        entry = candidate_entry
                        resolved_field = candidate_field
                        break

            if entry is None:
                entry = _pop_matching_update(fallback_updates, widget.rect, page_index)

            if entry is None:
                entry = {"export": "", "order": 0, "field_name": resolved_field or f"field_{widget.xref}"}

            resolved_field = resolved_field or entry.get("field_name") or f"field_{widget.xref}"
            groups[resolved_field].append((widget, entry, page_index))

    fields_modified = False
    for field_name, items in groups.items():
        if not items:
            continue
        items.sort(
            key=lambda item: (
                item[1].get("order", 0),
                round(item[0].rect.y0, 2),
                round(item[0].rect.x0, 2),
                item[0].xref,
            )
        )

        child_refs = [f"{widget.xref} 0 R" for widget, _, _ in items]
        remove_refs = set(child_refs)
        for widget, _, _ in items:
            parent_ref = doc.xref_get_key(widget.xref, "Parent")
            if parent_ref and parent_ref[0] == "xref":
                remove_refs.add(parent_ref[1])

        parent_xref = doc.get_new_xref()
        parent_ref_str = f"{parent_xref} 0 R"

        indices = [i for i, ref in enumerate(fields_entries) if ref in remove_refs]
        insert_at = min(indices) if indices else len(fields_entries)
        if remove_refs:
            fields_entries = [ref for ref in fields_entries if ref not in remove_refs]
        fields_entries.insert(insert_at, parent_ref_str)

        first_widget = items[0][0]
        field_flags = int(getattr(first_widget, "field_flags", 0))
        da_ref = doc.xref_get_key(first_widget.xref, "DA")
        da_value = da_ref[1] if da_ref and da_ref[0] == "string" else None

        kids_array = _format_ref_array(child_refs)
        parent_parts = [
            "/FT /Btn",
            f"/T ({field_name})",
            f"/Ff {field_flags}",
            f"/Kids {kids_array}",
            "/V /Off",
            "/DV /Off",
        ]
        if da_value:
            parent_parts.append(f"/DA ({da_value})")
        doc.update_object(parent_xref, f"<< {' '.join(parent_parts)} >>")
        fields_modified = True

        for widget, entry, _ in items:
            export_name = str(entry.get("export", "") or "")
            if export_name:
                _rename_widget_on_state(doc, widget.xref, export_name)
            doc.xref_set_key(widget.xref, "Parent", parent_ref_str)
            doc.xref_set_key(widget.xref, "T", "null")
            doc.xref_set_key(widget.xref, "V", "null")
            doc.xref_set_key(widget.xref, "DV", "null")
            doc.xref_set_key(widget.xref, "Kids", "null")
            doc.xref_set_key(widget.xref, "AS", "/Off")

    if fields_modified:
        doc.xref_set_key(acroform_xref, "Fields", _format_ref_array(fields_entries))


def inset_rect(rect: pm.Rect, dx: float = 4, dy: float = 4) -> pm.Rect:
    return pm.Rect(rect.x0 + dx, rect.y0 + dy, rect.x1 - dx, rect.y1 - dy)


def insert_center_text(
    page: pm.Page,
    rect: pm.Rect,
    text: str,
    *,
    font: str | None = None,
    size: float = 10,
    color=BLACK,
) -> None:
    if font is None:
        font = CURRENT_BOLD_FONT
    page.insert_textbox(
        rect,
        text,
        fontname=font,
        fontsize=size,
        align=pm.TEXT_ALIGN_CENTER,
        color=color,
    )


def insert_text(
    page: pm.Page,
    rect: pm.Rect,
    text: str,
    *,
    font: str | None = None,
    size: float = 10,
    align: int = pm.TEXT_ALIGN_LEFT,
    color=BLACK,
) -> None:
    if font is None:
        font = CURRENT_TEXT_FONT
    page.insert_textbox(rect, text, fontname=font, fontsize=size, align=align, color=color)


def measure_text_width(text: str, font_name: str, font_size: float) -> float:
    try:
        return pm.get_text_length(text, fontname=font_name, fontsize=font_size)
    except Exception:
        # Fallback approximation assumes average character width at 0.6 * font size
        return len(text) * font_size * 0.6


def draw_section_header(page: pm.Page, left: float, right: float, y: float, text: str) -> float:
    rect = pm.Rect(left, y, right, y + SECTION_HEADER_HEIGHT)
    page.draw_rect(rect, color=BLACK)
    insert_center_text(
        page,
        pm.Rect(rect.x0 + 6, rect.y0 + 4, rect.x1 - 6, rect.y1 - 4),
        text,
        size=10,
    )
    return rect.y1


def draw_labeled_box(
    page: pm.Page,
    left: float,
    right: float,
    y: float,
    rows: list[tuple[str, str]],
    label_width: float = 160,
    line_height: float = 22,
    row_gap: float | None = None,
) -> float:
    gap = row_gap if row_gap is not None else line_height
    height = line_height + max(0, (len(rows) - 1) * gap)
    rect = pm.Rect(left, y, right, y + height)
    page.draw_rect(rect, color=BLACK, width=1)

    line_top = rect.y0
    for label, body in rows:
        label_rect = pm.Rect(rect.x0 + 6, line_top + 4, rect.x0 + label_width, line_top + line_height - 4)
        insert_text(page, label_rect, label, font=CURRENT_BOLD_FONT, size=8)
        body_rect = pm.Rect(label_rect.x1 + 6, line_top + 4, rect.x1 - 6, line_top + line_height - 4)
        insert_text(page, body_rect, body, size=8)
        line_top += gap

    return rect.y1


def draw_field_row(
    page: pm.Page,
    left: float,
    y: float,
    width: float,
    height: float,
    fields: list[tuple[str, float]],
) -> tuple[float, list[tuple[pm.Rect, str]]]:
    x = left
    rects: list[tuple[pm.Rect, str]] = []
    for label, ratio in fields:
        field_width = width * ratio
        rect = pm.Rect(x, y, x + field_width, y + height)
        page.draw_rect(rect, color=BLACK, width=1)
        insert_text(
            page,
            pm.Rect(rect.x0 + 4, rect.y0 + 4, rect.x1 - 4, rect.y1 - 6),
            label,
            font=CURRENT_BOLD_FONT,
            size=7,
        )
        x += field_width
        rects.append((rect, label))
    return y + height, rects


def draw_checkbox_line(
    page: pm.Page,
    left: float,
    right: float,
    y: float,
    question: str,
    options: list[str],
    field_name: str,
) -> float:
    insert_text(
        page,
        pm.Rect(left + 4, y, right - 4, y + 26),
        question,
        font=CURRENT_BOLD_FONT,
        size=8,
    )
    box_y = y + 22
    x = left + 8
    box_size = 10
    radius = box_size / 2
    part_label = part_label_from_field(field_name)
    question_match = re.search(r"question(\d+)", field_name)
    question_number = question_match.group(1) if question_match else ""
    # Store widget info to update after all are added
    widgets_to_update = []
    export_names_used: set[str] = set()
    
    # Create the first radio button - this establishes the parent field
    first_option = options[0]
    box_rect = pm.Rect(x, box_y, x + box_size, box_y + box_size)
    center = (box_rect.x0 + radius, box_rect.y0 + radius)
    page.draw_circle(center, radius, color=BLACK, width=1)
    widget = pm.Widget()
    widget.field_name = field_name
    widget.field_type = pm.PDF_WIDGET_TYPE_RADIOBUTTON
    widget.button_caption = first_option
    widget.rect = box_rect
    widget.field_value = False
    widget.border_color = BLACK
    widget.fill_color = (1, 1, 1)
    page.add_widget(widget)
    first_export = _sanitize_radio_export(first_option, export_names_used)
    widgets_to_update.append((widget, first_export, first_option))
    
    tooltip = f"{part_label}, Question {question_number}, Option is {first_option}"
    _TOOLTIP_QUEUE[field_name].append(tooltip)
    insert_text(
        page,
        pm.Rect(box_rect.x1 + 4, box_rect.y0 - 2, box_rect.x1 + 150, box_rect.y1 + 10),
        first_option,
        size=8,
    )
    x = box_rect.x1 + 150
    
    # Now add the remaining options to the same field by creating widget annotations
    # that reference the parent field
    for idx, option in enumerate(options[1:], start=1):
        box_rect = pm.Rect(x, box_y, x + box_size, box_y + box_size)
        center = (box_rect.x0 + radius, box_rect.y0 + radius)
        page.draw_circle(center, radius, color=BLACK, width=1)
        widget = pm.Widget()
        widget.field_name = field_name
        widget.field_type = pm.PDF_WIDGET_TYPE_RADIOBUTTON
        widget.button_caption = option
        widget.rect = box_rect
        widget.field_value = False
        widget.border_color = BLACK
        widget.fill_color = (1, 1, 1)
        page.add_widget(widget)
        
        # Store the widget and its desired on-state value for later update
        export_name = _sanitize_radio_export(option, export_names_used)
        widgets_to_update.append((widget, export_name, option))
        
        tooltip = f"{part_label}, Question {question_number}, Option is {option}"
        _TOOLTIP_QUEUE[field_name].append(tooltip)
        insert_text(
            page,
            pm.Rect(box_rect.x1 + 4, box_rect.y0 - 2, box_rect.x1 + 150, box_rect.y1 + 10),
            option,
            size=8,
        )
        x = box_rect.x1 + 150
    
    # Store the radio button info for post-processing (we'll fix the on-states after saving)
    doc = page.parent
    if not hasattr(doc, '_radio_button_updates'):
        doc._radio_button_updates = []
    
    page_index = page.number
    for widget, export_name, label in widgets_to_update:
        order = len(doc._radio_button_updates)
        rect_tuple = (float(widget.rect.x0), float(widget.rect.y0), float(widget.rect.x1), float(widget.rect.y1))
        doc._radio_button_updates.append(
            {
                "widget_xref": widget.xref,
                "field_name": field_name,
                "export": export_name,
                "label": label,
                "order": order,
                "page_index": page_index,
                "rect": rect_tuple,
            }
        )
    
    return box_y + box_size + 4


def draw_checkbox_grid(
    page: pm.Page,
    left: float,
    right: float,
    y: float,
    items: list[str],
    columns: int,
    row_height: float = 18,
    field_prefix: str = "checkbox",
    font_size: float = 8,
    font_name: str | None = None,
) -> float:
    if font_name is None:
        font_name = CURRENT_TEXT_FONT
    content_width = right - left
    column_width = content_width / columns
    box_size = 10
    field_index = 0
    idx = 0
    base_row_height = row_height
    text_width_available = max(column_width - (box_size + 8 + 6 + 4), 1)

    while idx < len(items):
        row_items = items[idx : idx + columns]
        line_counts: list[int] = []
        max_lines = 1
        for item in row_items:
            if not item:
                lines = 1
            else:
                text_width = measure_text_width(item, font_name, font_size)
                lines = max(1, math.ceil(text_width / text_width_available))
            line_counts.append(lines)
            if lines > max_lines:
                max_lines = lines

        row_height_actual = base_row_height + (max_lines - 1) * (font_size + 4)
        x = left
        for item, lines in zip(row_items, line_counts):
            box_rect = pm.Rect(x + 4, y, x + 4 + box_size, y + box_size)
            page.draw_rect(box_rect, color=BLACK, width=1)
            widget = pm.Widget()
            widget.field_name = f"{field_prefix}_{field_index + 1}"
            widget.field_type = pm.PDF_WIDGET_TYPE_CHECKBOX
            widget.rect = box_rect
            widget.field_value = False
            widget.border_color = BLACK
            widget.fill_color = (1, 1, 1)
            page.add_widget(widget)
            part_label = part_label_from_field(field_prefix)
            tooltip = f"{part_label}, Option is {item}"
            _TOOLTIP_QUEUE[widget.field_name].append(tooltip)
            text_rect = pm.Rect(box_rect.x1 + 8, y - 2, x + column_width - 6, y + row_height_actual - 4)
            insert_text(page, text_rect, item, size=font_size, font=font_name)
            x += column_width
            field_index += 1
        y += row_height_actual
        idx += columns
    return y


def draw_signature_row(
    page: pm.Page,
    left: float,
    y: float,
    width: float,
    height: float,
    labels: list[tuple[str, float]],
    draw_bottom: bool = True,
) -> tuple[float, list[tuple[pm.Rect, str]]]:
    x = left
    rects: list[tuple[pm.Rect, str]] = []
    
    # First draw the top border across the entire width
    if not draw_bottom:
        page.draw_line((left, y), (left + width, y), color=BLACK, width=1)
    
    for i, (label, ratio) in enumerate(labels):
        block_width = width * ratio
        rect = pm.Rect(x, y, x + block_width, y + height)
        
        if draw_bottom:
            # Draw complete rectangle
            page.draw_rect(rect, color=BLACK, width=1)
        else:
            # Only draw vertical divider between boxes (not on edges)
            if i > 0:  # Draw left divider for all boxes except the first
                # Divider should stop well before the bottom to not overlap outer border
                # The outer border is 1.5px thick, so stop at least 2px before
                page.draw_line((rect.x0, rect.y0), (rect.x0, rect.y1 - 2), color=BLACK, width=1)
        
        insert_text(
            page,
            pm.Rect(rect.x0 + 4, rect.y0 + 4, rect.x1 - 4, rect.y1 - 6),
            label,
            font=CURRENT_BOLD_FONT,
            size=7,
        )
        x += block_width
        rects.append((rect, label))
    return y + height, rects


def add_text_widget(
    page: pm.Page,
    rect: pm.Rect,
    field_name: str,
    *,
    font_name: str | None = None,
    font_size: float = DEFAULT_TEXT_SIZE,
    top_offset: float | None = None,
    tooltip: str | None = None,
    font_xref: int | None = None,
) -> pm.Widget:
    if top_offset is None:
        # Increase offset for taller boxes to add more space from label
        if rect.height > 45:
            top_offset = 24  # More space for tall signature boxes
        else:
            top_offset = min(rect.height * 0.45, 20)
    
    # For tall boxes (>45px), use a fixed widget height instead of filling to bottom
    # This prevents text widgets from becoming too thin in signature boxes
    if rect.height > 45:
        widget_height = 18  # Fixed comfortable height for text input, with margin from bottom
        min_top = rect.y0 + 12
        target_bottom = rect.y1 - MIN_TEXT_WIDGET_BOTTOM_MARGIN
        proposed_top = rect.y0 + top_offset
        field_top = min(proposed_top, target_bottom - widget_height)
        field_top = max(field_top, min_top)
        field_bottom = field_top + widget_height
        field_rect = pm.Rect(rect.x0 + 8, field_top, rect.x1 - 8, field_bottom)
    else:
        field_rect = pm.Rect(rect.x0 + 8, rect.y0 + top_offset, rect.x1 - 8, rect.y1 - 8)
    
    if field_rect.height <= 0:
        field_rect = pm.Rect(rect.x0 + 8, rect.y0 + 12, rect.x1 - 8, rect.y1 - 8)
    widget = pm.Widget()
    widget.field_name = field_name
    widget.field_type = pm.PDF_WIDGET_TYPE_TEXT
    widget.rect = field_rect
    widget.text_font = font_name or CURRENT_TEXT_FONT
    widget.text_fontsize = font_size
    widget.text_color = BLACK
    widget.border_color = None
    widget.border_width = 0
    page.add_widget(widget)
    widget.update()
    if tooltip:
        _TOOLTIP_QUEUE[field_name].append(tooltip)
    return widget


def add_textarea_widget(page: pm.Page, rect: pm.Rect, field_name: str, *, tooltip: str | None = None) -> None:
    field_rect = pm.Rect(rect.x0 + 6, rect.y0 + 6, rect.x1 - 6, rect.y1 - 6)
    widget = pm.Widget()
    widget.field_name = field_name
    widget.field_type = pm.PDF_WIDGET_TYPE_TEXT
    widget.rect = field_rect
    widget.text_font = CURRENT_TEXT_FONT
    widget.text_fontsize = 10
    widget.text_color = BLACK
    widget.border_color = None
    widget.border_width = 0
    widget.field_flags = pm.PDF_TX_FIELD_IS_MULTILINE
    page.add_widget(widget)
    widget.update()
    if tooltip:
        _TOOLTIP_QUEUE[field_name].append(tooltip)


def build_form(page: pm.Page, translator: Translator) -> tuple[int | None, str, float] | None:
    doc = page.parent
    global CURRENT_TEXT_FONT, CURRENT_BOLD_FONT

    previous_text_font = CURRENT_TEXT_FONT
    previous_bold_font = CURRENT_BOLD_FONT
    CURRENT_TEXT_FONT, CURRENT_BOLD_FONT = configure_fonts_for_language(page, translator.language)

    signature_font_name = CURRENT_TEXT_FONT
    signature_font_xref: int | None = None
    signature_font_size = 16
    text = translator.text

    try:
        if SIGNATURE_FONT_PATH.exists():
            try:
                signature_font_xref = page.insert_font(
                    fontname=SIGNATURE_FONT_NAME,
                    fontfile=str(SIGNATURE_FONT_PATH),
                )
                signature_font_name = SIGNATURE_FONT_NAME
            except Exception as e:
                print(f"Failed to load signature font: {e}")
                signature_font_name = CURRENT_TEXT_FONT
                signature_font_xref = None

        width = page.rect.width
        height = page.rect.height
        margin = 26
        left = margin
        right = width - margin
        top = margin
        bottom = height - margin
        content_width = right - left

        outer_rect = pm.Rect(left, top, right, bottom)
        page.draw_rect(outer_rect, color=BLACK, width=1.5)

        y = top

        header_height = 56
        header_rect = pm.Rect(left, y, right, y + header_height)
        insert_center_text(page, header_rect, text("title"), size=30, color=BLACK)
        y += header_height
        page.draw_line((left, y), (right, y))

        info_height = 26
        info_rect = pm.Rect(left, y, right, y + info_height)
        page.draw_rect(info_rect, color=BLACK, width=1)
        insert_center_text(page, info_rect, text("privacy_statement"), size=11)
        y += info_height

        y = draw_labeled_box(
            page,
            left,
            right,
            y,
            [
                (text("principal_purpose_label"), text("principal_purpose_text")),
                (text("routine_uses_label"), text("routine_uses_text")),
            ],
            row_gap=10,
        )

        y = draw_section_header(page, left, right, y, text("part_i_header"))
        y, admin_row_one = draw_field_row(
            page,
            left,
            y,
            content_width,
            40,
            [
                (text("admin_whiner_name_label"), 0.45),
                (text("admin_social_security_label"), 0.27),
                (text("admin_report_date_label"), 0.28),
            ],
        )
        for (rect, _), name in zip(
            admin_row_one,
            ["admin_whiner_name", "admin_social_security", "admin_report_date"],
        ):
            add_text_widget(page, rect, name, tooltip=TEXT_TOOLTIPS.get(name))

        y, admin_row_two = draw_field_row(
            page,
            left,
            y,
            content_width,
            40,
            [
                (text("admin_organization_label"), 0.5),
                (text("admin_preparer_label"), 0.5),
            ],
        )
        for (rect, _), name in zip(
            admin_row_two,
            ["admin_organization", "admin_preparer_name"],
        ):
            add_text_widget(page, rect, name, tooltip=TEXT_TOOLTIPS.get(name))

        y = draw_section_header(page, left, right, y, text("part_ii_header"))
        y, incident_row_one = draw_field_row(
            page,
            left,
            y,
            content_width,
            40,
            [
                (text("incident_date_label"), 0.33),
                (text("incident_time_label"), 0.33),
                (text("incident_location_label"), 0.34),
            ],
        )
        for (rect, _), name in zip(
            incident_row_one,
            [
                "incident_date",
                "incident_time",
                "incident_location",
            ],
        ):
            add_text_widget(page, rect, name, tooltip=TEXT_TOOLTIPS.get(name))

        y, incident_row_two = draw_field_row(
            page,
            left,
            y,
            content_width,
            40,
            [
                (text("incident_offender_name_label"), 0.5),
                (text("incident_offender_org_label"), 0.5),
            ],
        )
        for (rect, _), name in zip(
            incident_row_two,
            [
                "incident_offender_name",
                "incident_offender_org",
            ],
        ):
            add_text_widget(page, rect, name, tooltip=TEXT_TOOLTIPS.get(name))

        y = draw_section_header(page, left, right, y, text("part_iii_header"))
        y = draw_checkbox_line(
            page,
            left,
            right,
            y + 4,
            text("injury_question1"),
            [text("left"), text("right"), text("both")],
            "injury_question1",
        )
        y = draw_checkbox_line(
            page,
            left,
            right,
            y,
            text("injury_question2"),
            [text("yes"), text("no"), text("maybe")],
            "injury_question2",
        )
        y = draw_checkbox_line(
            page,
            left,
            right,
            y,
            text("injury_question3"),
            [text("yes"), text("no"), text("multiple")],
            "injury_question3",
        )
        y = draw_checkbox_line(
            page,
            left,
            right,
            y,
            text("injury_question4"),
            [text("yes"), text("no"), text("maybe")],
            "injury_question4",
        )

        y = draw_section_header(page, left, right, y, text("part_iv_header"))
        y = draw_checkbox_grid(
            page,
            left,
            right,
            y + 6,
            [text(key) for key in [
                "reason_thin_skinned",
                "reason_fix_problems",
                "reason_two_beers",
                "reason_wimp",
                "reason_easily_hurt",
                "reason_hands_pockets",
                "reason_hormones",
                "reason_not_signed_up",
                "reason_not_offered_post_brief",
                "reason_crybaby",
                "reason_not_hero",
                "reason_requested_post_brief",
                "reason_want_mommy",
                "reason_weather",
                "reason_all_above",
            ]],
            columns=3,
            field_prefix="reason_filing",
        )

        y = draw_section_header(page, left, right, y, text("part_v_header"))
        footer_space = SECTION_HEADER_HEIGHT + MIN_SIGNATURE_REGION_HEIGHT
        available_for_narrative = max(0.0, bottom - y - footer_space)
        narrative_height = min(64.0, available_for_narrative)
        if narrative_height > 0:
            narrative_rect = pm.Rect(left, y, right, y + narrative_height)
            page.draw_rect(narrative_rect, color=BLACK, width=1)
            add_textarea_widget(
                page,
                narrative_rect,
                "narrative_text",
                tooltip=TEXT_TOOLTIPS.get("narrative_text"),
            )
            y = narrative_rect.y1

        y = draw_section_header(page, left, right, y, text("part_vi_header"))
        remaining_space = bottom - y
        signature_height = max(remaining_space, 0.0)
        y, auth_rects = draw_signature_row(
            page,
            left,
            y,
            content_width,
            signature_height,
            [
                (text("auth_whiner_name_label"), 0.5),
                (text("auth_signature_label"), 0.5),
            ],
            draw_bottom=False,  # Don't draw bottom border - use outer border instead
        )
        for (rect, _), name in zip(
            auth_rects,
            [
                "auth_whiner_name",
                "auth_whiner_signature",
            ],
        ):
            kwargs = {"tooltip": TEXT_TOOLTIPS.get(name)}
            add_text_widget(page, rect, name, **kwargs)

        apply_tooltips(page)

        radio_button_updates = getattr(doc, '_radio_button_updates', [])

        signature_info = None
        if signature_font_name == SIGNATURE_FONT_NAME and isinstance(signature_font_xref, int):
            signature_info = (signature_font_xref, signature_font_name, signature_font_size)

        return signature_info, radio_button_updates
    finally:
        CURRENT_TEXT_FONT = previous_text_font
        CURRENT_BOLD_FONT = previous_bold_font


def remove_text_widget_borders(doc: pm.Document) -> None:
    for page in doc:
        for widget in page.widgets():
            if widget.field_type == pm.PDF_WIDGET_TYPE_TEXT:
                try:
                    doc.xref_set_key(widget.xref, "Border", "[0 0 0]")
                    doc.xref_set_key(widget.xref, "BS", "<< /S /S /W 0 >>")
                except Exception:
                    continue


def configure_signature_font(
    doc: pm.Document,
    signature_font_xref: int,
    signature_font_name: str,
    signature_font_size: float,
) -> None:
    """Configure the signature field to use a custom font.
    
    This function:
    1. Adds the custom font to the AcroForm's default resources (DR)
    2. Sets the signature field's default appearance (DA) to use the custom font
    3. Removes the appearance stream (AP) so PDF readers regenerate it with the new font
    
    Args:
        doc: The PDF document
        signature_font_xref: The xref number of the embedded font
        signature_font_name: The name of the font (e.g., "GreatVibes")
        signature_font_size: The font size to use
    """
    # Find the signature widget
    page = doc[0]
    signature_widget = None
    for widget in page.widgets():
        if widget.field_name == "auth_whiner_signature":
            signature_widget = widget
            break
    
    if not signature_widget:
        return
    
    try:
        # Step 1: Add the font to the AcroForm's DR (Default Resources)
        # This is critical - PDF readers look here for available fonts
        catalog_xref = doc.pdf_catalog()
        acroform_ref = doc.xref_get_key(catalog_xref, "AcroForm")
        
        if acroform_ref[0] == "dict":
            # AcroForm is inline - we need to make it an indirect object
            fields_str = acroform_ref[1]
            
            # Find the /Fields array in the inline dict
            import re
            fields_match = re.search(r'/Fields\[(.*?)\]', fields_str)
            if fields_match:
                fields_content = fields_match.group(1)
                
                # Create new AcroForm object with DR including our custom font
                new_acroform_xref = doc.get_new_xref()
                acroform_dict = (
                    f"<< /Fields [{fields_content}] "
                    f"/DR << /Font << /Helv /Helvetica /{signature_font_name} {signature_font_xref} 0 R >> >> >>"
                )
                
                doc.update_object(new_acroform_xref, acroform_dict)
                
                # Update catalog to point to new AcroForm
                doc.xref_set_key(catalog_xref, "AcroForm", f"{new_acroform_xref} 0 R")
        
        # Step 2: Set the DA (default appearance) string on the widget
        # This tells the PDF reader which font to use for THIS field
        doc.xref_set_key(
            signature_widget.xref,
            "DA",
            f"(0 0 0 rg /{signature_font_name} {signature_font_size} Tf)",
        )
        
        # Step 3: Remove the /AP (appearance stream) - it caches the old font
        # The PDF reader will regenerate it from the DA string
        doc.xref_set_key(signature_widget.xref, "AP", "null")
        
        # DO NOT call widget.update() here - it will reset everything!
        
    except Exception as e:
        print(f"Error configuring signature font: {e}")
        import traceback
        traceback.print_exc()


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Butt Hurt Report PDF form.")
    parser.add_argument(
        "-l",
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language code to render (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Path to write the generated PDF (default: blank_form_<language>.pdf)",
    )
    parser.add_argument(
        "--i18n-path",
        default=str(DEFAULT_I18N_PATH),
        help=f"Path to the i18n CSV file (default: {DEFAULT_I18N_PATH})",
    )
    parser.add_argument(
        "--export-widget-data",
        action="store_true",
        help="Export widget metadata CSV alongside the PDF.",
    )
    args = parser.parse_args()

    language = (args.language or DEFAULT_LANGUAGE).strip()
    i18n_path = Path(args.i18n_path)
    catalog = TranslationCatalog(i18n_path)

    def render_language(translator: Translator, output_path: Path) -> None:
        doc = pm.open()
        page = doc.new_page()
        signature_info, radio_button_updates = build_form(page, translator)
        doc.save(str(output_path))
        doc.close()

        post_doc = pm.open(str(output_path))
        remove_text_widget_borders(post_doc)
        
        # Apply signature font settings after document is saved and reopened
        if signature_info:
            signature_font_xref, signature_font_name, signature_font_size = signature_info
            if signature_font_xref and signature_font_name == SIGNATURE_FONT_NAME:
                configure_signature_font(
                    post_doc,
                    signature_font_xref,
                    signature_font_name,
                    signature_font_size,
                )
        
        fix_radio_button_groups(post_doc, radio_button_updates)
        
        # Save to temporary file then replace the original
        temp_path = output_path.with_suffix(output_path.suffix + ".tmp")
        post_doc.save(str(temp_path))
        
        # Collect metadata AFTER all post-processing
        metadata = collect_metadata(post_doc)
        
        post_doc.close()
        
        # Replace the original with the temp file
        os.replace(str(temp_path), str(output_path))
        
        if args.export_widget_data:
            export_metadata(metadata, str(output_path))

    if language.lower() == "all":
        if args.output:
            parser.error("Cannot use --output when generating all languages.")
        available_languages = sorted(
            catalog.languages,
            key=lambda code: (code != DEFAULT_LANGUAGE, code),
        )
        if not available_languages:
            parser.error(f"No languages found in {i18n_path}.")
        for lang_code in available_languages:
            translator = catalog.get_translator(lang_code)
            output_path = Path(f"blank_form_{translator.language}.pdf")
            render_language(translator, output_path)
    else:
        translator = catalog.get_translator(language)
        if args.output:
            output_path = Path(args.output)
        else:
            output_path = Path(f"blank_form_{translator.language}.pdf")
        render_language(translator, output_path)


if __name__ == "__main__":
    main()
