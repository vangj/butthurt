import csv
import json
import re
from collections import defaultdict, deque
from pathlib import Path

import pymupdf as pm

BLACK = (0, 0, 0)

DEFAULT_TEXT_FONT = "Helvetica"
DEFAULT_TEXT_SIZE = 10
FONT_DIR = Path(__file__).resolve().parent / "fonts"
SIGNATURE_FONT_PATH = FONT_DIR / "GreatVibes-Regular.ttf"
SIGNATURE_FONT_NAME = "GreatVibes"

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

def inset_rect(rect: pm.Rect, dx: float = 4, dy: float = 4) -> pm.Rect:
    return pm.Rect(rect.x0 + dx, rect.y0 + dy, rect.x1 - dx, rect.y1 - dy)


def insert_center_text(
    page: pm.Page,
    rect: pm.Rect,
    text: str,
    *,
    font: str = "Helvetica",
    size: float = 10,
    color=BLACK,
) -> None:
    text_width = pm.get_text_length(text, fontname=font, fontsize=size)
    x = rect.x0 + (rect.width - text_width) / 2
    # approximate baseline position for vertical centering
    baseline = rect.y0 + (rect.height + size) / 2 - size * 0.3
    page.insert_text((x, baseline), text, fontname=font, fontsize=size, color=color)


def insert_text(
    page: pm.Page,
    rect: pm.Rect,
    text: str,
    *,
    font: str = "Helvetica",
    size: float = 10,
    align: int = pm.TEXT_ALIGN_LEFT,
    color=BLACK,
) -> None:
    page.insert_textbox(rect, text, fontname=font, fontsize=size, align=align, color=color)


def draw_section_header(page: pm.Page, left: float, right: float, y: float, text: str) -> float:
    rect = pm.Rect(left, y, right, y + 28)
    page.draw_rect(rect, color=BLACK)
    insert_center_text(
        page,
        pm.Rect(rect.x0 + 6, rect.y0 + 4, rect.x1 - 6, rect.y1 - 4),
        text,
        font="Helvetica-Bold",
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
        insert_text(page, label_rect, label, font="Helvetica-Bold", size=8)
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
            font="Helvetica-Bold",
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
        font="Helvetica-Bold",
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
    
    for idx, option in enumerate(options):
        box_rect = pm.Rect(x, box_y, x + box_size, box_y + box_size)
        center = (box_rect.x0 + radius, box_rect.y0 + radius)
        page.draw_circle(center, radius, color=BLACK, width=1)
        widget = pm.Widget()
        widget.field_name = field_name
        widget.field_type = pm.PDF_WIDGET_TYPE_RADIOBUTTON
        widget.rect = box_rect
        widget.field_value = False  # Not selected by default
        widget.border_color = BLACK
        widget.fill_color = (1, 1, 1)
        page.add_widget(widget)
        
        # Store the widget and its desired on-state value for later update
        widgets_to_update.append((widget, option))
        
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
    
    for widget, on_state_value in widgets_to_update:
        doc._radio_button_updates.append((widget.xref, on_state_value))
    
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
) -> float:
    content_width = right - left
    column_width = content_width / columns
    box_size = 10
    total_rows = (len(items) + columns - 1) // columns
    idx = 0
    for _ in range(total_rows):
        x = left
        for _ in range(columns):
            if idx >= len(items):
                break
            item = items[idx]
            box_rect = pm.Rect(x + 4, y, x + 4 + box_size, y + box_size)
            page.draw_rect(box_rect, color=BLACK, width=1)
            widget = pm.Widget()
            widget.field_name = f"{field_prefix}_{idx + 1}"
            widget.field_type = pm.PDF_WIDGET_TYPE_CHECKBOX
            widget.rect = box_rect
            widget.field_value = False
            widget.border_color = BLACK
            widget.fill_color = (1, 1, 1)
            page.add_widget(widget)
            part_label = part_label_from_field(field_prefix)
            tooltip = f"{part_label}, Option is {item}"
            _TOOLTIP_QUEUE[widget.field_name].append(tooltip)
            text_rect = pm.Rect(box_rect.x1 + 8, y - 2, x + column_width - 6, y + row_height - 4)
            insert_text(page, text_rect, item, size=8)
            x += column_width
            idx += 1
        y += row_height
    return y


def draw_signature_row(
    page: pm.Page,
    left: float,
    y: float,
    width: float,
    height: float,
    labels: list[tuple[str, float]],
) -> tuple[float, list[tuple[pm.Rect, str]]]:
    x = left
    rects: list[tuple[pm.Rect, str]] = []
    for label, ratio in labels:
        block_width = width * ratio
        rect = pm.Rect(x, y, x + block_width, y + height)
        page.draw_rect(rect, color=BLACK, width=1)
        insert_text(
            page,
            pm.Rect(rect.x0 + 4, rect.y0 + 4, rect.x1 - 4, rect.y1 - 6),
            label,
            font="Helvetica-Bold",
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
    font_name: str = DEFAULT_TEXT_FONT,
    font_size: float = DEFAULT_TEXT_SIZE,
    top_offset: float | None = None,
    tooltip: str | None = None,
    font_xref: int | None = None,
) -> pm.Widget:
    if top_offset is None:
        top_offset = min(rect.height * 0.45, 20)
    field_rect = pm.Rect(rect.x0 + 8, rect.y0 + top_offset, rect.x1 - 8, rect.y1 - 8)
    if field_rect.height <= 0:
        field_rect = pm.Rect(rect.x0 + 8, rect.y0 + 12, rect.x1 - 8, rect.y1 - 8)
    widget = pm.Widget()
    widget.field_name = field_name
    widget.field_type = pm.PDF_WIDGET_TYPE_TEXT
    widget.rect = field_rect
    widget.text_font = font_name
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
    widget.text_font = "Helvetica"
    widget.text_fontsize = 10
    widget.text_color = BLACK
    widget.border_color = None
    widget.border_width = 0
    widget.field_flags = pm.PDF_TX_FIELD_IS_MULTILINE
    page.add_widget(widget)
    widget.update()
    if tooltip:
        _TOOLTIP_QUEUE[field_name].append(tooltip)


def build_form(page: pm.Page) -> tuple[int | None, str, float] | None:
    doc = page.parent
    signature_font_name = DEFAULT_TEXT_FONT
    signature_font_xref: int | None = None
    signature_font_size = 16
    
    # Insert the custom font at the document level, not page level
    if SIGNATURE_FONT_PATH.exists():
        try:
            # Use insert_font to embed the font
            signature_font_xref = page.insert_font(
                fontname=SIGNATURE_FONT_NAME, fontfile=str(SIGNATURE_FONT_PATH)
            )
            signature_font_name = SIGNATURE_FONT_NAME
        except Exception as e:
            print(f"Failed to load signature font: {e}")
            signature_font_name = DEFAULT_TEXT_FONT
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
    insert_center_text(
        page,
        header_rect,
        "BUTT HURT REPORT",
        font="Helvetica-Bold",
        size=30,
        color=BLACK,
    )
    y += header_height
    page.draw_line((left, y), (right, y))

    info_height = 26
    info_rect = pm.Rect(left, y, right, y + info_height)
    page.draw_rect(info_rect, color=BLACK, width=1)
    insert_center_text(
        page,
        info_rect,
        "DATA REQUIRED BY THE PRIVACY ACT OF 1974",
        font="Helvetica-Bold",
        size=11,
    )
    y += info_height

    y = draw_labeled_box(
        page,
        left,
        right,
        y,
        [
            ("PRINCIPAL PURPOSE:", "To assist whiners in documenting hurt feelings."),
            ("ROUTINE USES:", "Leaders & whiners should use this form as necessary."),
        ],
        row_gap=10,
    )

    y = draw_section_header(page, left, right, y, "PART I - ADMINISTRATIVE DATA")
    y, admin_row_one = draw_field_row(
        page,
        left,
        y,
        content_width,
        40,
        [
            ("A. WHINER'S NAME (Last, First, MI)", 0.45),
            ("B. SOCIAL SECURITY NUMBER", 0.27),
            ("C. DATE OF REPORT", 0.28),
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
            ("D. ORGANIZATION", 0.5),
            ("E. NAME & TITLE OF PERSON FILLING OUT THIS FORM", 0.5),
        ],
    )
    for (rect, _), name in zip(
        admin_row_two,
        ["admin_organization", "admin_preparer_name"],
    ):
        add_text_widget(page, rect, name, tooltip=TEXT_TOOLTIPS.get(name))

    y = draw_section_header(page, left, right, y, "PART II - INCIDENT REPORT")
    y, incident_row_one = draw_field_row(
        page,
        left,
        y,
        content_width,
        40,
        [
            ("A. DATE FEELINGS WERE HURT", 0.33),
            ("B. TIME OF HURTFULNESS", 0.33),
            ("C. LOCATION OF HURTFUL INCIDENT", 0.34),
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
            ("D. NAME OF REAL MAN/WOMAN WHO HURT YOUR SENSITIVE FEELINGS", 0.5),
            ("E. ORGANIZATION", 0.5),
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

    y = draw_section_header(page, left, right, y, "PART III - INJURY")
    y = draw_checkbox_line(
        page,
        left,
        right,
        y + 4,
        "1. WHICH EAR WERE THE WORDS OF HURTFULNESS SPOKEN INTO?",
        ["LEFT", "RIGHT", "BOTH"],
        "injury_question1",
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "2. IS THERE PERMANENT FEELING DAMAGE?",
        ["YES", "NO", "MAYBE"],
        "injury_question2",
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "3. DID YOU REQUIRE A \"TISSUE\" FOR TEARS?",
        ["YES", "NO", "MULTIPLE"],
        "injury_question3",
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "4. HAS THIS RESULTED IN A TRAUMATIC BRAIN INJURY?",
        ["YES", "NO", "MAYBE"],
        "injury_question4",
    )

    y = draw_section_header(
        page, left, right, y, "PART IV - REASON FOR FILING THIS REPORT (Mark all that apply)"
    )
    y = draw_checkbox_grid(
        page,
        left,
        right,
        y + 6,
        [
            "I am thin skinned",
            "Someone needs to fix my problems",
            "Two beers is not enough",
            "I am a wimp",
            "My feelings are easily hurt",
            "My hands should be in pockets",
            "I have woman/man-like hormones",
            "I didn't sign up for this",
            "I was not offered a post brief",
            "I am a crybaby",
            "I was told that I am not a hero",
            "Someone requested a post brief",
            "I want my mommy",
            "The weather is too cold/hot",
            "All of the above and more",
        ],
        columns=3,
        field_prefix="reason_filing",
    )

    y = draw_section_header(
        page,
        left,
        right,
        y,
        "PART V - NARRATIVE (Tell us in your own sissy words how your feelings were hurt.)",
    )
    narrative_height = 64
    narrative_rect = pm.Rect(left, y, right, y + narrative_height)
    page.draw_rect(narrative_rect, color=BLACK, width=1)
    add_textarea_widget(page, narrative_rect, "narrative_text", tooltip=TEXT_TOOLTIPS.get("narrative_text"))
    y = narrative_rect.y1

    y = draw_section_header(page, left, right, y, "PART VI - AUTHENTICATION")
    signature_height = 40
    y, auth_rects = draw_signature_row(
        page,
        left,
        y,
        content_width,
        signature_height,
        [
            ("A. PRINTED NAME OF WHINER", 0.5),
            ("B. SIGNATURE", 0.5),
        ],
    )
    for (rect, _), name in zip(
        auth_rects,
        [
            "auth_whiner_name",
            "auth_whiner_signature",
        ],
    ):
        kwargs = {"tooltip": TEXT_TOOLTIPS.get(name)}
        # Don't set custom font here - we'll do it after saving
        # because widget.update() resets it
        add_text_widget(page, rect, name, **kwargs)

    apply_tooltips(page)
    
    # Collect radio button updates that need to be applied after saving
    radio_button_updates = getattr(doc, '_radio_button_updates', [])
    
    # Always return signature info and radio button info for post-processing
    # We need to set these AFTER saving because widget.update() resets them
    signature_info = None
    if signature_font_name == SIGNATURE_FONT_NAME and isinstance(signature_font_xref, int):
        signature_info = (signature_font_xref, signature_font_name, signature_font_size)
    
    return signature_info, radio_button_updates


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


def main(output_path: str = "blank_form.pdf") -> None:
    from pathlib import Path
    import os
    
    doc = pm.open()
    page = doc.new_page()
    signature_info, radio_button_updates = build_form(page)
    doc.save(output_path)
    doc.close()

    post_doc = pm.open(output_path)
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
    
    # Fix radio button on-states after document is saved and reopened
    # We need to match widgets by their position/index since xrefs change
    page = post_doc[0]
    radio_widgets = [w for w in page.widgets() if w.field_type == pm.PDF_WIDGET_TYPE_RADIOBUTTON]
    
    if len(radio_widgets) == len(radio_button_updates):
        for widget, (_, on_state_value) in zip(radio_widgets, radio_button_updates):
            try:
                # Get the current AP (appearance) dictionary
                ap_ref = post_doc.xref_get_key(widget.xref, "AP")
                if ap_ref[0] == "dict":
                    # Parse the appearance dict and replace "Yes" with the custom on-state
                    ap_dict_str = ap_ref[1]
                    # Replace /Yes with /{on_state_value}
                    updated_ap = ap_dict_str.replace("/Yes", f"/{on_state_value}")
                    post_doc.xref_set_key(widget.xref, "AP", updated_ap)
            except Exception as e:
                print(f"Failed to update radio button on-state: {e}")
    
    # Save to temporary file then replace the original
    temp_path = f"{output_path}.tmp"
    post_doc.save(temp_path)
    
    # Collect metadata AFTER all post-processing
    metadata = collect_metadata(post_doc)
    
    post_doc.close()
    
    # Replace the original with the temp file
    os.replace(temp_path, output_path)
    
    export_metadata(metadata, output_path)


if __name__ == "__main__":
    main()
