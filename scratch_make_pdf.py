"""Generate the Doc Decode pitch guide PDF using fpdf2."""
from fpdf import FPDF

class PitchPDF(FPDF):
    def header(self):
        pass
    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Doc Decode  |  Hackathon Pitch Guide  |  Page {self.page_no()}/{{nb}}", align="C")

pdf = PitchPDF("P", "mm", "A4")
pdf.alias_nb_pages()
pdf.set_auto_page_break(auto=True, margin=18)
pdf.add_page()

W = pdf.w - 20  # usable width (margins 10 each side)

# ---- Helpers ----
def title(text, size=24):
    pdf.set_font("Helvetica", "B", size)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 12, text, align="C", new_x="LMARGIN", new_y="NEXT")

def section(icon, text):
    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(30, 64, 175)
    pdf.cell(0, 9, f"{icon}  {text}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(37, 99, 235)
    pdf.set_line_width(0.6)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(4)

def body(text):
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(1)

def bold_body(label, text):
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(30, 30, 30)
    x = pdf.get_x()
    pdf.cell(pdf.get_string_width(label) + 1, 5.5, label)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(1)

def bullet(text, indent=14):
    pdf.set_x(indent)
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(30, 30, 30)
    pdf.cell(5, 5.5, "-")
    pdf.multi_cell(0, 5.5, text)
    pdf.ln(0.5)

def numbered(num, bold_text, rest=""):
    pdf.set_x(14)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(37, 99, 235)
    pdf.cell(8, 6, str(num) + ".")
    pdf.set_text_color(30, 30, 30)
    if rest:
        w = pdf.get_string_width(bold_text + " ") + 1
        pdf.cell(w, 6, bold_text + " ")
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, rest)
    else:
        pdf.multi_cell(0, 6, bold_text)
    pdf.ln(0.5)

def quote(text):
    pdf.set_fill_color(239, 246, 255)
    pdf.set_draw_color(37, 99, 235)
    y = pdf.get_y()
    pdf.set_x(14)
    pdf.set_font("Helvetica", "I", 11.5)
    pdf.set_text_color(30, 58, 95)
    pdf.multi_cell(W - 8, 6, text, fill=True)
    h = pdf.get_y() - y
    pdf.set_line_width(1)
    pdf.line(12, y, 12, y + h)
    pdf.ln(3)

def highlight(text):
    pdf.set_fill_color(254, 243, 199)
    pdf.set_draw_color(245, 158, 11)
    pdf.set_font("Helvetica", "B", 11)
    pdf.set_text_color(146, 64, 14)
    pdf.set_x(12)
    pdf.multi_cell(W - 4, 6, text, fill=True, border=1)
    pdf.ln(3)

def table_header(cols, widths):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(30, 64, 175)
    pdf.set_text_color(255, 255, 255)
    for i, col in enumerate(cols):
        pdf.cell(widths[i], 7, col, border=1, fill=True, align="C")
    pdf.ln()

def table_row(cells, widths, shade=False):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(30, 30, 30)
    if shade:
        pdf.set_fill_color(248, 250, 252)
    else:
        pdf.set_fill_color(255, 255, 255)
    max_lines = 1
    heights = []
    for i, cell in enumerate(cells):
        lines = pdf.multi_cell(widths[i], 5.5, cell, dry_run=True, output="LINES")
        heights.append(len(lines))
        max_lines = max(max_lines, len(lines))
    row_h = max_lines * 5.5
    y0 = pdf.get_y()
    for i, cell in enumerate(cells):
        x0 = pdf.get_x()
        pdf.rect(x0, y0, widths[i], row_h, style="DF" if shade else "D")
        pdf.set_xy(x0 + 1, y0 + 1)
        pdf.multi_cell(widths[i] - 2, 5.5, cell)
        pdf.set_xy(x0 + widths[i], y0)
    pdf.set_y(y0 + row_h)

# ===================== CONTENT =====================

# Title
title("DOC DECODE")
pdf.set_font("Helvetica", "", 12)
pdf.set_text_color(100, 116, 139)
pdf.cell(0, 7, "Hackathon Pitch Guide  --  Understand Before You Sign", align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)

# --- One-liner ---
section(">>", "One-Liner Pitch")
quote('"Doc Decode reads your rental agreements, loan papers, hospital bills, and government notices -- and tells you what actually matters, in plain language, before you sign."')

# --- Customer ---
section(">>", "Who Is Your Customer?")
numbered(1, "Everyday Indians", "signing rental agreements, loan documents, or hospital discharge papers -- people who can't afford a lawyer for every piece of paper")
numbered(2, "Small business owners", "dealing with tenders, purchase orders, invoices, and government notices")
numbered(3, "Senior citizens / first-time renters", "who struggle with legal jargon")
numbered(4, "Malayalam-speaking users", "in Kerala who need documents decoded in their own language")
numbered(5, "Anyone who has ever signed something they didn't fully understand", "-- that's basically everyone")
pdf.ln(2)
highlight('KEY STAT: "In India, over 90% of people sign documents they don\'t fully read. We\'re their second pair of eyes."')

# --- Why use ---
section(">>", "Why Should They Use This?")
w1, w2 = 70, W - 70
table_header(["Pain Point", "Doc Decode Solution"], [w1, w2])
rows = [
    ('"I don\'t understand legal jargon"', "Explains every risky clause in plain English or Malayalam"),
    ('"I missed a hidden penalty clause"', "Flags 12 categories of risky clauses -- auto-renewal traps, late fees, one-sided conditions, lock-ins"),
    ('"I forgot a deadline and lost money"', "Extracts all deadlines + lets you export them to your calendar (.ics)"),
    ('"I can\'t afford a lawyer for every paper"', "100% free, runs on YOUR laptop -- no subscription, no cloud"),
    ('"I don\'t trust AI with my private documents"', "Zero cloud dependency -- Ollama runs locally, no API key, no data stored"),
]
for i, (a, b) in enumerate(rows):
    table_row([a, b], [w1, w2], shade=(i % 2 == 1))

# --- What it does ---
pdf.ln(2)
section(">>", "What Does It Do? (Demo Flow -- 2 min)")
steps = [
    ("Upload", "a PDF, photo, or scan -- drag & drop"),
    ("Auto-classifies", "the document (rental, loan, hospital bill, government notice, invoice, tender)"),
    ("Extracts hard facts:", "rent amount, deposit, interest rate, EMI, due dates, totals -- with page numbers"),
    ("Flags risky clauses", "across 12 categories with attention levels"),
    ("Explains each clause", 'in plain language -- "If you leave before 6 months, you lose your entire deposit"'),
    ("Deadlines dashboard", "-- tick the ones that matter -- export to Google Calendar"),
    ("Ask questions", '-- "What happens if I pay late?" -- grounded answer with evidence sentences'),
    ("Read aloud", "-- works in Malayalam too (offline voice)"),
    ("Compare documents", "-- match invoice vs. purchase order, spot mismatches"),
    ("Tender eligibility checker", "-- check if you qualify for a government tender"),
]
for i, (b, r) in enumerate(steps, 1):
    numbered(i, b, r)

# --- Page break ---
pdf.add_page()

# --- Unique ---
section(">>", "What Makes It Attractive / Unique?")

bold_body("1. AI That Can't Hallucinate Facts -- ", "Facts come from regex + rules -- deterministic, reproducible, never invented. The LLM only explains what the rules already found. If Ollama is down, the app still works.")
pdf.ln(1)
bold_body("2. 100% Offline & Private -- ", "No cloud. No API key. No data stored. No database. Document is in memory for one request, then dropped. Perfect for sensitive financial/legal documents.")
pdf.ln(1)
bold_body("3. Bilingual -- English + Malayalam -- ", "Full Malayalam OCR, fact extraction, and UI. Handles 18,500 rupees, 11 months. Chillu character folding for OCR accuracy.")
pdf.ln(1)
bold_body("4. Works on Scans & Photos -- ", "OCR fallback with Tesseract -- only for pages that need it. Upload a photo of a government notice from WhatsApp -- it works.")
pdf.ln(1)
bullet("Calendar export for deadlines -- 'Never miss a reply-by date again'")
bullet("118 tests, including false-positive tests and prompt injection protection")

# --- Future scope ---
pdf.ln(2)
section(">>", "Future Scope")
w1, w2 = 32, W - 32
table_header(["Phase", "Features"], [w1, w2])
table_row(["Near-term", "More document types (insurance, employment contracts, property deeds)\nMore Indian languages (Hindi, Tamil, Kannada, Telugu)\nMobile app -- snap a photo, get analysis\nWhatsApp bot -- forward a document, get a summary back"], [w1, w2])
table_row(["Medium-term", "Document comparison at scale (old lease vs new lease -- what changed?)\nClause negotiation suggestions -- 'Ask your landlord to change THIS'\nCommunity-sourced clause database -- flag known predatory clauses\nIntegration with DigiLocker for verified government documents"], [w1, w2], shade=True)
table_row(["Long-term", "Legal aid marketplace -- connect flagged issues to affordable lawyers\nEnterprise version for banks/NBFCs -- compliance checking at intake\nAPI-as-a-service for fintech apps (loan origination, insurance)\nHandwriting recognition with TrOCR models"], [w1, w2])

# --- Closing ---
pdf.ln(4)
section(">>", "Closing Line for the Stage")
pdf.set_fill_color(15, 23, 42)
y0 = pdf.get_y()
pdf.set_x(12)
pdf.set_font("Helvetica", "", 12)
pdf.set_text_color(226, 232, 240)
closing = '"We\'re not replacing lawyers. We\'re making sure the 90% of Indians who can\'t access one still understand what they\'re signing. And everything -- every calculation, every flag -- stays on your machine. Your documents are nobody\'s business but yours."'
pdf.multi_cell(W - 4, 7, closing, fill=True)
pdf.ln(4)

# --- Tip ---
pdf.set_fill_color(240, 253, 244)
pdf.set_draw_color(34, 197, 94)
pdf.set_font("Helvetica", "B", 10.5)
pdf.set_text_color(22, 101, 52)
pdf.set_x(12)
pdf.multi_cell(W - 4, 6, "DEMO TIP: Drop the demo_rental_agreement.pdf first -- it triggers 9 clause categories and has an auto-renewal trap that always gets a reaction from the audience.", fill=True, border=1)

# ---- Save ----
out = r"c:\Devan\Projects\leadathon\Doc_Decode_Pitch_Guide.pdf"
pdf.output(out)
print(f"Saved: {out}")
