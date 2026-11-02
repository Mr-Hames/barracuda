"""Builds the example submission in examples/submission/ (already committed; rerun to rebuild).

  python examples/make_examples.py

The files meet most of examples/assignment.txt but hide five typical mistakes:
the report is missing the Conclusion section, a reviewer comment was left in, the file name
doesn't follow the required pattern, the deck has 12 slides instead of at most 10, and the
spreadsheet has a #DIV/0! error.
"""
import os

import docx
import openpyxl
from docx.shared import Mm, Pt
from pptx import Presentation

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "submission")

BODY = [
    ("Bean & Brick is a small coffee roaster that wants to open its first café in the city centre. "
     "This report looks at who drinks speciality coffee nearby, what they pay today and how a new brand "
     "can win a place in their morning routine."),
    ("The area has eleven cafés within a ten minute walk. Most of them are chains with similar menus and "
     "prices between 3 and 4.5 euros for a flat white. Only two roast their own beans, and neither tells "
     "customers where the coffee comes from."),
    ("We surveyed 120 people near the planned location. Students and office workers make up most of the "
     "morning traffic. They care about speed first, taste second and price third. Almost half said they "
     "would try a new place if a friend recommended it."),
    ("Bean & Brick should open with a short menu, a loyalty card from day one and a weekly cupping session "
     "where customers taste new beans for free. Local partnerships with two coworking spaces would bring "
     "steady weekday orders."),
]


def report(path):
    d = docx.Document()
    normal = d.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(12)
    s = d.sections[0]
    s.page_width, s.page_height = Mm(210), Mm(297)
    for side in ("left", "right", "top", "bottom"):
        setattr(s, f"{side}_margin", Mm(25))
    d.add_heading("Launching Bean & Brick coffee", level=0)
    sections = ["Introduction", "Market Analysis", "Recommendations"]  # "Conclusion" is missing on purpose
    for title, text in zip(sections + ["Next steps"], BODY):
        d.add_heading(title, level=1)
        for _ in range(4):
            d.add_paragraph(text)
    first = d.paragraphs[2]
    d.add_comment(first.runs, text="Add a source for the survey numbers", author="Reviewer")
    d.core_properties.author = d.core_properties.last_modified_by = "Student"
    d.save(path)


def deck(path):
    prs = Presentation()
    titles = ["Bean & Brick", "The problem", "Who we surveyed", "What they want", "Competition",
              "Prices nearby", "Our idea", "Menu", "Loyalty card", "Partners", "Budget", "Thank you"]
    for t in titles:  # 12 slides; the assignment allows 10
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        slide.shapes.title.text = t
        slide.placeholders[1].text = "Key points for this part of the pitch."
    prs.core_properties.author = prs.core_properties.last_modified_by = "Student"
    prs.save(path)


def workbook(path):
    wb = openpyxl.Workbook()
    data = wb.active
    data.title = "Data"
    data.append(["Month", "Cups sold", "Revenue, EUR"])
    for m, cups in zip(["Jan", "Feb", "Mar", "Apr", "May", "Jun"], [2100, 2300, 2650, 2800, 3100, 3300]):
        data.append([m, cups, cups * 3.6])
    forecast = wb.create_sheet("Forecast")
    forecast.append(["Month", "Cups", "Growth"])
    forecast.append(["Jul", 3500, 0.06])
    forecast.append(["Aug", 0, "#DIV/0!"])  # a broken growth formula, saved with its error value
    wb.properties.creator = wb.properties.lastModifiedBy = "Student"
    wb.save(path)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    report(os.path.join(OUT, "Report_final.docx"))  # should be <Surname>_Marketing_Report.docx
    deck(os.path.join(OUT, "Pitch.pptx"))
    workbook(os.path.join(OUT, "Calculations.xlsx"))
    print("example files written to", OUT)
