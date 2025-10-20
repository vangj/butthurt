import re
from collections import defaultdict, deque

import pymupdf as pm

BLACK = (0, 0, 0)

PART_ROMANS = {
    1: "I",
    2: "II",
    3: "III",
    4: "IV",
    5: "V",
    6: "VI",
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
    "part5_narrative": "Part V, Narrative",
    "auth_whiner_name": "Part VI, Authentication, Question A, Printed Name of Whiner",
    "auth_whiner_signature": "Part VI, Authentication, Question B, Signature",
}

_TOOLTIP_QUEUE: defaultdict[str, list[str]] = defaultdict(list)


def part_label_from_field(field_name: str) -> str:
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


def inset_rect(rect: pm.Rect, dx: float = 4, dy: float = 4) -> pm.Rect:
    return pm.Rect(rect.x0 + dx, rect.y0 + dy, rect.x1 - dx, rect.y1 - dy)


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
    insert_text(
        page,
        pm.Rect(rect.x0 + 6, rect.y0 + 4, rect.x1 - 6, rect.y1 - 4),
        text,
        font="Helvetica-Bold",
        size=10,
        align=pm.TEXT_ALIGN_CENTER,
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
    part_match = re.match(r"part(\d+)", field_name)
    part_number = int(part_match.group(1)) if part_match else None
    part_label = f"Part {PART_ROMANS.get(part_number, str(part_number))}" if part_number else "Part"
    question_match = re.search(r"question(\d+)", field_name)
    question_number = question_match.group(1) if question_match else ""
    for option in options:
        box_rect = pm.Rect(x, box_y, x + box_size, box_y + box_size)
        center = (box_rect.x0 + radius, box_rect.y0 + radius)
        page.draw_circle(center, radius, color=BLACK, width=1)
        widget = pm.Widget()
        widget.field_name = field_name
        widget.field_type = pm.PDF_WIDGET_TYPE_RADIOBUTTON
        widget.rect = box_rect
        widget.field_value = False
        widget.border_color = BLACK
        widget.fill_color = (1, 1, 1)
        page.add_widget(widget)
        tooltip = f"{part_label}, Question {question_number}, Option is {option}"
        _TOOLTIP_QUEUE[field_name].append(tooltip)
        insert_text(
            page,
            pm.Rect(box_rect.x1 + 4, box_rect.y0 - 2, box_rect.x1 + 150, box_rect.y1 + 10),
            option,
            size=8,
        )
        x = box_rect.x1 + 150
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
            part_match = re.match(r"part(\d+)", field_prefix)
            part_number = int(part_match.group(1)) if part_match else None
            part_label = f"Part {PART_ROMANS.get(part_number, str(part_number))}" if part_number else "Part"
            widget.border_color = BLACK
            widget.fill_color = (1, 1, 1)
            page.add_widget(widget)
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
    top_offset: float | None = None,
    tooltip: str | None = None,
) -> None:
    if top_offset is None:
        top_offset = min(rect.height * 0.45, 20)
    field_rect = pm.Rect(rect.x0 + 8, rect.y0 + top_offset, rect.x1 - 8, rect.y1 - 8)
    if field_rect.height <= 0:
        field_rect = pm.Rect(rect.x0 + 8, rect.y0 + 12, rect.x1 - 8, rect.y1 - 8)
    widget = pm.Widget()
    widget.field_name = field_name
    widget.field_type = pm.PDF_WIDGET_TYPE_TEXT
    widget.rect = field_rect
    widget.text_font = "Helvetica"
    widget.text_fontsize = 10
    widget.text_color = BLACK
    widget.border_color = BLACK
    widget.border_width = 0
    page.add_widget(widget)
    if tooltip:
        _TOOLTIP_QUEUE[field_name].append(tooltip)


def add_textarea_widget(page: pm.Page, rect: pm.Rect, field_name: str, *, tooltip: str | None = None) -> None:
    field_rect = pm.Rect(rect.x0 + 6, rect.y0 + 6, rect.x1 - 6, rect.y1 - 6)
    widget = pm.Widget()
    widget.field_name = field_name
    widget.field_type = pm.PDF_WIDGET_TYPE_TEXT
    widget.rect = field_rect
    widget.text_font = "Helvetica"
    widget.text_fontsize = 10
    widget.text_color = BLACK
    widget.border_color = BLACK
    widget.border_width = 0
    widget.field_flags = pm.PDF_TX_FIELD_IS_MULTILINE
    page.add_widget(widget)
    if tooltip:
        _TOOLTIP_QUEUE[field_name].append(tooltip)


def build_form(page: pm.Page) -> None:
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
    page.insert_textbox(
        header_rect,
        "BUTT HURT REPORT",
        fontname="Helvetica-Bold",
        fontsize=30,
        align=pm.TEXT_ALIGN_CENTER,
        color=BLACK,
    )
    y += header_height
    page.draw_line((left, y), (right, y))

    info_height = 26
    info_rect = pm.Rect(left, y, right, y + info_height)
    page.draw_rect(info_rect, color=BLACK, width=1)
    insert_text(
        page,
        info_rect,
        "DATA REQUIRED BY THE PRIVACY ACT OF 1974",
        font="Helvetica-Bold",
        size=11,
        align=pm.TEXT_ALIGN_CENTER,
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

    y = draw_section_header(page, left, right, y, "PART III - INJURY (Mark all that apply)")
    y = draw_checkbox_line(
        page,
        left,
        right,
        y + 4,
        "1. WHICH EAR WERE THE WORDS OF HURTFULNESS SPOKEN INTO?",
        ["LEFT", "RIGHT", "BOTH"],
        "part3_question1",
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "2. IS THERE PERMANENT FEELING DAMAGE?",
        ["YES", "NO", "MAYBE"],
        "part3_question2",
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "3. DID YOU REQUIRE A \"TISSUE\" FOR TEARS?",
        ["YES", "NO", "MULTIPLE"],
        "part3_question3",
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "4. HAS THIS RESULTED IN A TRAUMATIC BRAIN INJURY?",
        ["YES", "NO", "MAYBE"],
        "part3_question4",
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
        field_prefix="part4_reason",
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
    add_textarea_widget(page, narrative_rect, "part5_narrative", tooltip=TEXT_TOOLTIPS.get("part5_narrative"))
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
        add_text_widget(page, rect, name, tooltip=TEXT_TOOLTIPS.get(name))

    apply_tooltips(page)

def main(output_path: str = "blank_form.pdf") -> None:
    doc = pm.open()
    page = doc.new_page()
    build_form(page)
    doc.save(output_path)
    doc.close()


if __name__ == "__main__":
    main()
