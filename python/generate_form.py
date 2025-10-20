import pymupdf as pm

BLACK = (0, 0, 0)


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
    rect = pm.Rect(left, y, right, y + 36)
    page.draw_rect(rect, color=BLACK)
    insert_text(
        page,
        rect,
        text,
        font="Helvetica-Bold",
        size=11,
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
    line_height: float = 34,
) -> float:
    height = line_height * len(rows)
    rect = pm.Rect(left, y, right, y + height)
    page.draw_rect(rect, color=BLACK, width=1)

    line_top = rect.y0
    for label, body in rows:
        label_rect = pm.Rect(rect.x0 + 6, line_top + 4, rect.x0 + label_width, line_top + line_height - 4)
        insert_text(page, label_rect, label, font="Helvetica-Bold", size=9)
        body_rect = pm.Rect(label_rect.x1 + 6, line_top + 4, rect.x1 - 6, line_top + line_height - 4)
        insert_text(page, body_rect, body, size=9)
        line_top += line_height

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
            pm.Rect(rect.x0 + 6, rect.y0 + 4, rect.x1 - 6, rect.y1 - 6),
            label,
            font="Helvetica-Bold",
            size=9,
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
    ) -> float:
    insert_text(
        page,
        pm.Rect(left + 4, y, right - 4, y + 26),
        question,
        font="Helvetica-Bold",
        size=9,
    )
    box_y = y + 28
    x = left + 8
    box_size = 10
    for option in options:
        box_rect = pm.Rect(x, box_y, x + box_size, box_y + box_size)
        page.draw_rect(box_rect, color=BLACK, width=1)
        insert_text(
            page,
            pm.Rect(box_rect.x1 + 4, box_rect.y0 - 2, box_rect.x1 + 150, box_rect.y1 + 10),
            option,
            size=9,
        )
        x = box_rect.x1 + 150
    return box_y + box_size + 10


def draw_checkbox_grid(
    page: pm.Page,
    left: float,
    right: float,
    y: float,
    items: list[str],
    columns: int,
    row_height: float = 28,
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
            text_rect = pm.Rect(box_rect.x1 + 8, y - 2, x + column_width - 6, y + row_height - 4)
            insert_text(page, text_rect, item, size=9)
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
) -> float:
    x = left
    for label, ratio in labels:
        block_width = width * ratio
        rect = pm.Rect(x, y, x + block_width, y + height)
        page.draw_rect(rect, color=BLACK, width=1)
        insert_text(
            page,
            pm.Rect(rect.x0 + 6, rect.y0 + 4, rect.x1 - 6, rect.y1 - 6),
            label,
            font="Helvetica-Bold",
            size=9,
        )
        x += block_width
    return y + height


def add_text_widget(page: pm.Page, rect: pm.Rect, field_name: str) -> None:
    field_rect = pm.Rect(rect.x0 + 8, rect.y0 + (rect.height * 0.45), rect.x1 - 8, rect.y1 - 8)
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


def build_form(page: pm.Page) -> None:
    width = page.rect.width
    height = page.rect.height
    margin = 36
    left = margin
    right = width - margin
    top = margin
    bottom = height - margin
    content_width = right - left

    outer_rect = pm.Rect(left, top, right, bottom)
    page.draw_rect(outer_rect, color=BLACK, width=1.5)

    y = top

    header_height = 64
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

    info_height = 36
    info_rect = pm.Rect(left, y, right, y + info_height)
    page.draw_rect(info_rect, color=BLACK, width=1)
    insert_text(
        page,
        info_rect,
        "DATA REQUIRED BY THE PRIVACY ACT OF 1974",
        font="Helvetica-Bold",
        size=12,
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
    )

    y = draw_section_header(page, left, right, y, "PART I - ADMINISTRATIVE DATA")
    y, admin_row_one = draw_field_row(
        page,
        left,
        y,
        content_width,
        44,
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
        add_text_widget(page, rect, name)

    y, admin_row_two = draw_field_row(
        page,
        left,
        y,
        content_width,
        44,
        [
            ("D. ORGANIZATION", 0.5),
            ("E. NAME & TITLE OF PERSON FILLING OUT THIS FORM", 0.5),
        ],
    )
    for (rect, _), name in zip(
        admin_row_two,
        ["admin_organization", "admin_preparer_name"],
    ):
        add_text_widget(page, rect, name)

    y = draw_section_header(page, left, right, y, "PART II - INCIDENT REPORT")
    y, _ = draw_field_row(
        page,
        left,
        y,
        content_width,
        44,
        [
            ("A. DATE FEELINGS WERE HURT", 0.33),
            ("B. TIME OF HURTFULNESS", 0.33),
            ("C. LOCATION OF HURTFUL INCIDENT", 0.34),
        ],
    )
    y, _ = draw_field_row(
        page,
        left,
        y,
        content_width,
        44,
        [
            ("D. NAME OF REAL MAN/WOMAN WHO HURT YOUR SENSITIVE FEELINGS", 0.5),
            ("E. ORGANIZATION", 0.5),
        ],
    )

    y = draw_section_header(page, left, right, y, "E. INJURY (Mark all that apply)")
    y = draw_checkbox_line(
        page,
        left,
        right,
        y + 4,
        "1. WHICH EAR WERE THE WORDS OF HURTFULNESS SPOKEN INTO?",
        ["LEFT", "RIGHT", "BOTH"],
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "2. IS THERE PERMANENT FEELING DAMAGE?",
        ["YES", "NO", "MAYBE"],
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "3. DID YOU REQUIRE A \"TISSUE\" FOR TEARS?",
        ["YES", "NO", "MULTIPLE"],
    )
    y = draw_checkbox_line(
        page,
        left,
        right,
        y,
        "4. HAS THIS RESULTED IN A TRAUMATIC BRAIN INJURY?",
        ["YES", "NO", "MAYBE"],
    )

    y = draw_section_header(
        page, left, right, y, "F. REASON FOR FILING THIS REPORT (Mark all that apply)"
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
    )

    y = draw_section_header(
        page,
        left,
        right,
        y,
        "G. NARRATIVE (Tell us in your own sissy words how your feelings were hurt.)",
    )
    narrative_height = 120
    narrative_rect = pm.Rect(left, y, right, y + narrative_height)
    page.draw_rect(narrative_rect, color=BLACK, width=1)
    y = narrative_rect.y1

    y = draw_section_header(page, left, right, y, "PART III - AUTHENTICATION")
    y = draw_signature_row(
        page,
        left,
        y,
        content_width,
        46,
        [
            ("A. PRINTED NAME OF REAL MAN/WOMAN", 0.25),
            ("B. SIGNATURE", 0.25),
            ("C. PRINTED NAME OF WHINER", 0.25),
            ("D. SIGNATURE", 0.25),
        ],
    )

    insert_text(
        page,
        pm.Rect(left, bottom - 12, right, bottom),
        "©2012 ITS Tactical",
        size=7,
        align=pm.TEXT_ALIGN_LEFT,
    )


def main(output_path: str = "blank_form.pdf") -> None:
    doc = pm.open()
    page = doc.new_page()
    build_form(page)
    doc.save(output_path)
    doc.close()


if __name__ == "__main__":
    main()
