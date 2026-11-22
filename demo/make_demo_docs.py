"""Generate the synthetic demo documents used for testing and demos.

Run:  python demo/make_demo_docs.py

Every name, address, amount and date below is invented. No real person,
property, bank, hospital or office is involved.
"""
import sys
from pathlib import Path

import pymupdf as fitz

OUT_DIR = Path(__file__).resolve().parent

BANNER = "SYNTHETIC DEMO DOCUMENT - FICTIONAL DATA - NOT A REAL AGREEMENT"

RENTAL = """RESIDENTIAL RENTAL AGREEMENT

{banner}

This Rental Agreement is made on 1st April 2025 at Kochi, Kerala between
Mr. Anil Varma, residing at 12 Example Road, Kakkanad (hereinafter the
"Landlord") and Ms. Reema Joseph, residing at 7 Sample Lane, Edappally
(hereinafter the "Tenant").

1. PREMISES
The Landlord lets to the Tenant Flat No. 4B, Demo Residency, Kakkanad, Kochi,
for residential use only.

2. TERM
The agreement is for a period of 11 months commencing from 1st April 2025 and
expires on 28th February 2026.

3. RENT
The Tenant shall pay a monthly rent of Rs. 18,500/- on or before the 5th day of
every English calendar month.

4. SECURITY DEPOSIT
The Tenant has paid an interest free security deposit of Rs. 1,10,000/- to the
Landlord. The security deposit shall be refunded at the time of vacating the
premises after deduction of arrears of rent, unpaid electricity charges and the
cost of repairs for any damage beyond normal wear and tear, as assessed solely
by the Landlord.

5. MAINTENANCE AND ADDITIONAL CHARGES
In addition to the rent, the Tenant shall pay society maintenance charges of
Rs. 2,400/- per month, and electricity and water charges as per actual meter
readings. Any additional charge levied by the association shall be borne by the
Tenant.

6. LATE PAYMENT
If the rent is not paid on or before the 5th day of the month, the Tenant shall
pay a late payment penalty of Rs. 250/- per day of delay until the rent is paid
in full.

7. LOCK-IN PERIOD
There shall be a lock-in period of 6 months from the date of commencement. If
the Tenant vacates before the expiry of the lock-in period, the Tenant shall
forfeit two months rent from the security deposit.

8. NOTICE PERIOD AND EARLY TERMINATION
Either party may terminate this agreement after the lock-in period by giving
2 months prior written notice. In case of early termination by the Tenant
without such notice, an amount equal to one month rent shall be deducted from
the security deposit.

9. RENEWAL
Unless either party gives written notice of its intention not to continue at
least 30 days before 28th February 2026, this agreement shall stand renewed
automatically for a further term of 11 months with an escalation of 7% in the
monthly rent.

10. ENTRY
The Landlord shall have the right to enter the premises for inspection at any
time without prior notice in case of a suspected breach of this agreement.

11. SUBLETTING
The Tenant shall not sublet, assign or part with possession of the premises.

12. OBLIGATIONS
The Tenant shall maintain the premises in good condition at their own cost and
shall be responsible for minor repairs up to Rs. 1,000/- per occurrence.

13. DISPUTES
Any decision of the Landlord regarding deductions from the security deposit
shall be final and binding on the Tenant.

{banner}
"""

LOAN = """PERSONAL LOAN AGREEMENT

{banner}

This Loan Agreement is executed on 15th May 2025 between Demo Finance Limited,
a fictional non-banking finance company (the "Lender") and Mr. Sabu Thomas
(the "Borrower").

1. LOAN AMOUNT
The Lender sanctions a loan amount of Rs. 4,50,000/- to the Borrower.

2. RATE OF INTEREST
The loan shall carry a floating rate of interest at the rate of 14.5% per annum,
compounded monthly. The Lender may revise the interest rate at its sole
discretion on giving 15 days notice to the Borrower.

3. REPAYMENT
The loan is repayable in 48 equated monthly instalments. The EMI is Rs. 12,380/-
and the first instalment is due on 10th July 2025. Repayment shall commence from
that date.

4. PROCESSING FEE
A processing fee of 2% of the loan amount plus applicable taxes shall be
deducted from the disbursed amount. The processing fee is non-refundable.

5. DEFAULT AND PENAL INTEREST
If the Borrower fails to pay any instalment on its due date, penal interest at
the rate of 3% per month shall be charged on the overdue amount, in addition to
a late fee of Rs. 600/- per instalment.

6. PREPAYMENT
The Borrower may prepay the loan after 12 months subject to a foreclosure charge
of 4% of the outstanding principal.

7. RECALL
The Lender may recall the entire outstanding amount at any time without
assigning any reason, and the Borrower shall pay the same within 7 days of such
demand.

8. SECURITY
The Borrower undertakes to provide a post dated cheque for each instalment and
shall indemnify the Lender against all costs of recovery.

9. STATEMENTS
Any statement of account issued by the Lender shall be final and binding on the
Borrower.

{banner}
"""

HOSPITAL = """DEMO MULTISPECIALITY HOSPITAL (FICTIONAL)
Example Junction, Thrissur, Kerala

{banner}

INPATIENT BILL

Patient Name   : Mr. Joshy Mathew (fictional)
UHID           : DEMO-554120
IP No          : IP/2025/00871
Date of Admission : 3rd June 2025
Date of Discharge : 8th June 2025
Bill Date      : 8th June 2025

CHARGE SUMMARY

Room rent (5 days)                      Rs. 17,500.00
Consultation charges                    Rs.  6,000.00
Nursing charges                         Rs.  4,500.00
Investigation charges (laboratory)      Rs. 11,250.00
Pharmacy                                Rs. 14,870.00
Surgery charges                         Rs. 32,000.00
Consumables                             Rs.  3,980.00

Gross amount                            Rs. 90,100.00
Insurance approved (Demo Insurance)     Rs. 60,000.00
Total amount payable by patient         Rs. 30,100.00

PAYMENT TERMS
The total payable amount is due on or before 18th June 2025. If the amount is
not paid by the due date, a late payment charge of 1.5% per month shall be
added to the outstanding balance.

Mode of payment: cash, card or UPI at the billing counter. Insurance claim
queries must be submitted within 15 days of discharge, failing which the claim
may be treated as closed.

{banner}
"""

NOTICE = """OFFICE OF THE DEMO MUNICIPAL CORPORATION (FICTIONAL)
Revenue Department, Example Nagar

{banner}

PUBLIC NOTICE - PROPERTY TAX DEMAND

Reference No : DMC/REV/2025/4471
Notice Date  : 20th June 2025

To,
Smt. Leela Krishnan (fictional)
Door No. 18/221, Example Nagar Ward 9

Subject: Demand notice for unpaid property tax for assessment year 2024-25.

1. As per the records of this office, property tax dues of Rs. 24,780/- in
respect of the above property remain unpaid for the assessment year 2024-25.

2. You are hereby directed to remit the said amount on or before 15th July 2025
at the Revenue Department counter or through the official payment portal.

3. Failing which, interest at the rate of 12% per annum shall be levied from the
original due date and recovery proceedings shall be initiated under the
applicable municipal rules without further notice.

4. If you dispute this demand, you are required to submit a written objection
with supporting documents within 15 days of receipt of this notice and appear
before the competent authority on 10th July 2025 at 11.00 AM.

5. Any decision of the competent authority in this matter shall be final.

Assistant Revenue Officer
Demo Municipal Corporation

{banner}
"""

DOCUMENTS = {
    "demo_rental_agreement.pdf": ("Synthetic Rental Agreement (Demo)", RENTAL),
    "demo_loan_agreement.pdf": ("Synthetic Loan Agreement (Demo)", LOAN),
    "demo_hospital_bill.pdf": ("Synthetic Hospital Bill (Demo)", HOSPITAL),
    "demo_government_notice.pdf": ("Synthetic Government Notice (Demo)", NOTICE),
}


# ---------------------------------------------------------------------------
# Structured samples for the invoice, purchase order, tender, GST, insurance and
# loan checks. Every party, number and reference is invented. The loan EMI is
# computed here from the stated principal, rate and tenure, so the stated figure
# is exact and the verification check has something real to agree with.
# ---------------------------------------------------------------------------

def _emi_text(principal: str, annual_percent: str, months: int) -> str:
    from decimal import ROUND_HALF_UP, Decimal, localcontext

    with localcontext() as context:
        context.prec = 28
        p = Decimal(principal)
        r = Decimal(annual_percent) / Decimal(100) / Decimal(12)
        growth = (Decimal(1) + r) ** months
        emi = p * r * growth / (growth - Decimal(1))
    value = emi.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return "{:,.2f}".format(value)


INVOICE_MISMATCH = """TAX INVOICE

{banner}

Supplier: Sample Traders Pvt Ltd (FICTIONAL)
Supplier GSTIN: 00SYNTH0000X1Z0 (synthetic, not a real registration)
Buyer: Demo Buyer Company (FICTIONAL)
Invoice No: SYN-INV-1001
Invoice Date: 05/03/2026

Description        Qty  Unit  Rate      Amount
Steel bolts         10  Nos   120.00    1200.00
Copper wire          5  Mtr   300.00    1500.00
Cable clips         20  Nos    15.00     350.00

Subtotal: 3050.00
CGST @ 9%: 274.50
SGST @ 9%: 274.50
Grand Total: 3599.00

Payment terms: Net 30 days from the invoice date.
"""

PURCHASE_ORDER = """PURCHASE ORDER

{banner}

PO No: SYN-PO-5501
PO Date: 01/03/2026
Buyer: Demo Buyer Company (FICTIONAL)
Supplier: Sample Traders Pvt Ltd (FICTIONAL)

Description        Qty  Unit  Rate      Amount
Steel bolts         10  Nos   120.00    1200.00
Copper wire          5  Mtr   300.00    1500.00
Cable clips         20  Nos    15.00     300.00

Subtotal: 3000.00
CGST @ 9%: 270.00
SGST @ 9%: 270.00
Total: 3540.00
"""

TENDER = """TENDER NOTICE (SYNTHETIC)

{banner}

Tender No: SYN-NIT-2026-17
Issued by: Office of the Demo Public Works Department (FICTIONAL)
Estimated value: Rs. 12,50,000.00
EMD (Earnest Money Deposit): Rs. 25,000.00 (2% of estimated value)
The bidder must have a minimum average annual turnover of Rs. 50,00,000 in the last three financial years.
Last date for bid submission: 15/12/2026
Bid opening date: 17/12/2026

Eligibility criteria
1. The bidder must have a minimum average annual turnover of Rs. 50,00,000 (mandatory).
2. The bidder must hold a valid ISO 9001:2015 certificate (mandatory).
3. The bidder must have completed at least two similar works in the last five years.
4. Registration with the GST portal is required.

Documents to be submitted
- Copy of PAN card
- Copy of GST registration certificate
- Audited balance sheet for the last three years
- Self-attested affidavit as per the format in Annexure A
"""

GST_NOTICE = """OFFICE OF THE DEMO GST OFFICER (FICTIONAL)

{banner}

Reference No: SYN-GST-2026-0042
Date of issue: 20/10/2026
Section 73 of the CGST Act, 2017 (synthetic reference)
Tax period: April 2025 to March 2026
Tax demanded: Rs. 45,000.00
Interest: Rs. 6,200.00
Penalty: Rs. 4,500.00
Reply by: 15/12/2026

The taxpayer is asked to file a reply, with any supporting documents, within the time stated above.
"""

INSURANCE_POLICY = """HEALTH INSURANCE POLICY SCHEDULE (SYNTHETIC)

{banner}

Policy number: SYN-POL-778812
Insurer: Demo General Insurance Co (FICTIONAL)
Policy start date: 01/04/2026
Policy end date: 31/03/2027
Sum insured: Rs. 5,00,000.00
Base premium: Rs. 10,508.47
GST @ 18%: Rs. 1,891.53
Total premium: Rs. 12,400.00
Deductible: Rs. 5,000.00
"""

LOAN_SAMPLE = (
    """PERSONAL LOAN SANCTION LETTER (SYNTHETIC)

{banner}

Loan amount (principal): Rs. 5,00,000.00
Annual interest rate: 12% per annum
Tenure: 36 months
Monthly EMI: Rs. """
    + _emi_text("500000", "12", 36)
    + """

The EMI above is a synthetic figure computed from the principal, rate and tenure stated in this letter.
"""
)

AMBIGUOUS_DATES = """NOTICE TO PAY (SYNTHETIC)

{banner}

Reference: SYN-AMB-7
Please pay the outstanding amount of Rs. 8,000.00 by 03/04/2026 or 04/03/2026 as previously agreed.
The second instalment is due 2 weeks after the date of this notice, subject to any written extension.
A late fee applies from the 5th day of every month if payment is not received.
"""

NO_DEADLINES = """GENERAL LETTER (SYNTHETIC)

{banner}

Dear Sample Customer,

Thank you for your interest in our products. This letter is a plain example with no dates or payment obligations stated.

We look forward to working with you.

Regards,
Demo Team (FICTIONAL)
"""

SAMPLES = {
    "sample_invoice_mismatch.pdf": ("Synthetic Invoice With One Wrong Line (Sample)", INVOICE_MISMATCH),
    "sample_purchase_order.pdf": ("Synthetic Purchase Order (Sample)", PURCHASE_ORDER),
    "sample_tender.pdf": ("Synthetic Tender Notice (Sample)", TENDER),
    "sample_gst_notice.pdf": ("Synthetic GST Notice (Sample)", GST_NOTICE),
    "sample_insurance_policy.pdf": ("Synthetic Insurance Policy Schedule (Sample)", INSURANCE_POLICY),
    "sample_loan.pdf": ("Synthetic Loan Sanction Letter (Sample)", LOAN_SAMPLE),
    "sample_ambiguous_dates.pdf": ("Synthetic Notice With Ambiguous Dates (Sample)", AMBIGUOUS_DATES),
    "sample_no_deadlines.pdf": ("Synthetic Letter With No Deadlines (Sample)", NO_DEADLINES),
}
DOCUMENTS.update(SAMPLES)

PAGE_WIDTH, PAGE_HEIGHT = fitz.paper_size("a4")
MARGIN = 56
FONT = "helv"
FONT_SIZE = 10.5
LINE_HEIGHT = 14.5


def write_pdf(path: Path, title: str, body: str) -> None:
    doc = fitz.open()
    doc.set_metadata({"title": title, "author": "Doc Decode demo generator"})
    lines = body.format(banner=BANNER).split("\n")
    page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    y = MARGIN
    for line in lines:
        if y > PAGE_HEIGHT - MARGIN:
            page = doc.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
            y = MARGIN
        if line.strip():
            page.insert_text(
                (MARGIN, y), line, fontname=FONT, fontsize=FONT_SIZE, color=(0.1, 0.1, 0.15)
            )
        y += LINE_HEIGHT
    doc.save(str(path))
    doc.close()


# ---------------------------------------------------------------------------
# A Malayalam notice, rendered as an image so it exercises the OCR path the way
# a photographed document would. Needs a Malayalam-capable font; on Windows
# Nirmala UI ships with the operating system.
# ---------------------------------------------------------------------------

MALAYALAM_LINES = [
    "വാടക കരാർ അറിയിപ്പ് (മാതൃക രേഖ)",
    "",
    "പ്രതിമാസ വാടക: 18,500 രൂപ",
    "സെക്യൂരിറ്റി ഡിപ്പോസിറ്റ്: 1,10,000 രൂപ",
    "കരാർ കാലാവധി: 11 മാസം",
    "നോട്ടീസ് കാലാവധി: 2 മാസം",
    "വാടക മാസം അഞ്ചാം തീയതിക്ക് മുൻപ് നൽകണം.",
    "വൈകിയാൽ ദിവസം 250 രൂപ പിഴ ഈടാക്കും.",
    "",
    "SYNTHETIC DEMO DOCUMENT - FICTIONAL DATA",
]

MALAYALAM_FONTS = [
    r"C:\Windows\Fonts\Nirmala.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansMalayalam-Regular.ttf",
    "/System/Library/Fonts/Supplemental/Malayalam Sangam MN.ttc",
    "/Library/Fonts/Malayalam Sangam MN.ttc",
]


def find_malayalam_font():
    for candidate in MALAYALAM_FONTS:
        if Path(candidate).exists():
            return candidate
    return None


def write_malayalam_image(path: Path) -> bool:
    """Render a Malayalam notice as a PNG. False if no suitable font is present."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow is not installed; skipping the Malayalam demo image.")
        return False

    font_path = find_malayalam_font()
    if not font_path:
        print("No Malayalam font found; skipping the Malayalam demo image.")
        return False

    font = ImageFont.truetype(font_path, 34)
    image = Image.new("RGB", (1120, 560), "white")
    draw = ImageDraw.Draw(image)
    y = 30
    for line in MALAYALAM_LINES:
        draw.text((40, y), line, font=font, fill=(15, 15, 25))
        y += 52
    image.save(path)
    return True


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, (title, body) in DOCUMENTS.items():
        target = OUT_DIR / filename
        write_pdf(target, title, body)
        print("wrote %s" % target)
    image_target = OUT_DIR / "demo_malayalam_notice.png"
    if write_malayalam_image(image_target):
        print("wrote %s" % image_target)
    return 0


if __name__ == "__main__":
    sys.exit(main())
