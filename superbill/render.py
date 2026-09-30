"""Render SuperbillData to a one-file PDF (fpdf2, core Helvetica font, US Letter).

Layout, top to bottom: practice block + title, patient / provider blocks, diagnosis codes,
itemized visits table (auto page breaks, header repeated), totals, payment statement,
signature line, footer with statement date and page numbers.
"""

from __future__ import annotations

import os
from datetime import date
from typing import Any, Dict, Optional

from fpdf import FPDF
from fpdf.enums import XPos, YPos

from .build import SuperbillData

PAGE_W = 215.9  # US Letter, mm
MARGIN = 18.0
CONTENT_W = PAGE_W - 2 * MARGIN
COL_W = {"date": 26.0, "desc": 86.0, "proc": 40.0, "charge": CONTENT_W - 26.0 - 86.0 - 40.0}
INK = (25, 25, 25)
MUTED = (95, 95, 95)
RULE = (170, 170, 170)
SHADE = (238, 240, 243)
ZEBRA = (249, 249, 251)


def money(v: float) -> str:
    sign = "-" if v < 0 else ""
    return f"{sign}${abs(v):,.2f}"


def fmt_date(d: Optional[date]) -> str:
    return f"{d.month}/{d.day}/{d.year}" if d else ""


def _latin(s: Any) -> str:
    return str(s if s is not None else "").encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def __init__(self, data: SuperbillData, cfg: Dict[str, Any]):
        super().__init__(orientation="P", unit="mm", format="Letter")
        self.data = data
        self.cfg = cfg
        self._in_table = False
        self.set_margins(MARGIN, MARGIN, MARGIN)
        self.set_auto_page_break(auto=True, margin=22)
        self.alias_nb_pages()
        self.set_title(_latin(f"Superbill - {data.client_name}"))
        self.set_author(_latin(cfg["practice"]["name"]))

    # fpdf2 calls this on every page
    def footer(self) -> None:
        self.set_y(-16)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*MUTED)
        left = _latin(f"{self.cfg['practice']['name']}  |  Superbill for {self.data.client_name}  |  Statement date {fmt_date(self.data.statement_date)}")
        self.cell(CONTENT_W * 0.8, 5, left, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(CONTENT_W * 0.2, 5, f"Page {self.page_no()} of {{nb}}", align="R")
        self.set_text_color(*INK)

    def header(self) -> None:
        if self.page_no() > 1:
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*MUTED)
            self.cell(CONTENT_W, 6, _latin(f"Superbill - {self.data.client_name} (continued)"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            self.set_text_color(*INK)
            self.ln(2)
            if self._in_table:
                self._table_header()

    # ---- blocks ----------------------------------------------------------------------

    def label_value(self, label: str, value: str, w: float, label_w: float = 26.0, h: float = 5.2) -> None:
        x = self.get_x()
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*MUTED)
        self.cell(label_w, h, _latin(label), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_text_color(*INK)
        self.set_font("Helvetica", "B" if label.startswith("Patient") else "", 9.5)
        self.multi_cell(w - label_w, h, _latin(value) or "-", new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_x(x)

    def practice_and_title(self) -> None:
        p = self.cfg["practice"]
        top = self.get_y()
        self.set_font("Helvetica", "B", 13)
        self.cell(CONTENT_W * 0.6, 7, _latin(p["name"]), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 9.5)
        for line in p.get("address_lines") or []:
            self.cell(CONTENT_W * 0.6, 4.8, _latin(line), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if p.get("phone"):
            self.cell(CONTENT_W * 0.6, 4.8, _latin(f"Phone: {p['phone']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        if p.get("ein"):
            self.cell(CONTENT_W * 0.6, 4.8, _latin(f"Tax ID (EIN): {p['ein']}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        pos = p.get("place_of_service_code")
        if pos:
            self.cell(CONTENT_W * 0.6, 4.8, _latin(f"Place of Service: {pos} - {p.get('place_of_service_name', '')}"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        left_end = self.get_y()

        # title block on the right
        self.set_xy(MARGIN + CONTENT_W * 0.6, top)
        self.set_font("Helvetica", "B", 20)
        self.cell(CONTENT_W * 0.4, 9, _latin(self.cfg["text"]["title"]), align="R", new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_font("Helvetica", "", 8.5)
        self.set_text_color(*MUTED)
        self.multi_cell(CONTENT_W * 0.4, 4, _latin(self.cfg["text"]["subtitle"]), align="R", new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.ln(1.5)
        self.set_text_color(*INK)
        self.set_font("Helvetica", "", 9)
        d = self.data
        for lab, val in (
            ("Statement date", fmt_date(d.statement_date)),
            ("Dates of service", f"{fmt_date(d.episode_start)} - {fmt_date(d.episode_end)}"),
            ("Patient ID", str(d.client_id)),
        ):
            self.set_x(MARGIN + CONTENT_W * 0.6)
            self.set_text_color(*MUTED)
            self.cell(CONTENT_W * 0.22, 4.6, _latin(lab), align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*INK)
            self.cell(CONTENT_W * 0.18, 4.6, _latin(val), align="R", new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_y(max(left_end, self.get_y()) + 3)
        self.rule()

    def rule(self, gap: float = 3.0) -> None:
        self.set_draw_color(*RULE)
        y = self.get_y()
        self.line(MARGIN, y, MARGIN + CONTENT_W, y)
        self.ln(gap)

    def patient_and_provider(self) -> None:
        d = self.data
        half = CONTENT_W / 2
        top = self.get_y()
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*MUTED)
        self.cell(half, 5, "PATIENT", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*INK)
        self.label_value("Patient:", d.client_name, half - 4)
        self.label_value("Date of birth:", fmt_date(d.client_dob), half - 4)
        if d.client_address:
            self.label_value("Address:", d.client_address, half - 4)
        if d.client_phone:
            self.label_value("Phone:", d.client_phone, half - 4)
        left_end = self.get_y()

        self.set_xy(MARGIN + half, top)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*MUTED)
        self.cell(half, 5, "RENDERING PROVIDER", new_x=XPos.LEFT, new_y=YPos.NEXT)
        self.set_text_color(*INK)
        prov = d.provider
        name = prov.get("name", "")
        if prov.get("credentials"):
            name = f"{name}, {prov['credentials']}"
        self.set_x(MARGIN + half)
        self.label_value("Provider:", name, half, label_w=22)
        for lab, key in (("NPI:", "npi"), ("License:", "license"), ("Taxonomy:", "taxonomy")):
            if prov.get(key):
                self.set_x(MARGIN + half)
                self.label_value(lab, str(prov[key]), half, label_w=22)
        self.set_y(max(left_end, self.get_y()) + 1.5)

        self.set_x(MARGIN)
        codes = ", ".join(d.diagnosis_codes) if d.diagnosis_codes else "Not on file - see treatment notes"
        self.label_value("ICD-10 diagnosis:", codes, CONTENT_W, label_w=32)
        self.ln(1.5)
        self.rule()

    def _table_header(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(*SHADE)
        self.set_draw_color(*RULE)
        self.cell(COL_W["date"], 6.5, "Date of service", border="B", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(COL_W["desc"], 6.5, "Description", border="B", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(COL_W["proc"], 6.5, "CPT code x units", border="B", fill=True, new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(COL_W["charge"], 6.5, "Charge", border="B", fill=True, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    def visits_table(self) -> None:
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*MUTED)
        self.cell(CONTENT_W, 5, _latin(f"SERVICES RENDERED ({len(self.data.lines)} visits)"), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(*INK)
        self._table_header()
        self._in_table = True
        self.set_font("Helvetica", "", 9)
        for i, line in enumerate(self.data.lines):
            fill = i % 2 == 1
            self.set_fill_color(*ZEBRA)
            self.cell(COL_W["date"], 6, fmt_date(line.date), fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(COL_W["desc"], 6, _latin(line.description)[:60], fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(COL_W["proc"], 6, _latin(line.procedure_label()), fill=fill, new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.cell(COL_W["charge"], 6, money(line.charge), fill=fill, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self._in_table = False
        self.set_draw_color(*RULE)
        self.line(MARGIN, self.get_y(), MARGIN + CONTENT_W, self.get_y())
        self.ln(3)

    def totals(self) -> None:
        d = self.data
        if self.get_y() > self.h - 75:  # keep totals + statement together
            self.add_page()
        label_w, val_w = 52.0, 32.0
        x0 = MARGIN + CONTENT_W - label_w - val_w
        # Charges and payments only: amount billed / discount / balance cannot be right for
        # payment-plan patients whose later installments are not invoiced yet.
        rows = [("Total charges", money(d.total_charges), False)]
        # Paid in full (no plan, nothing owed): charges - discount = payments, so the discount is exact.
        if not d.payment_plan and d.balance <= 0.005 and d.provider_discount > 0.005:
            rows.append(("Provider discount", money(-d.provider_discount), False))
        rows.append(("Payments received to date", money(d.total_payments), True))
        for lab, val, bold in rows:
            self.set_x(x0)
            self.set_font("Helvetica", "B" if bold else "", 9.5)
            if bold:
                self.set_draw_color(*INK)
                self.cell(label_w, 6.2, lab, border="T", new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.cell(val_w, 6.2, val, border="T", align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
            else:
                self.cell(label_w, 5.6, lab, new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.cell(val_w, 5.6, val, align="R", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(4)

    def statement(self) -> None:
        d = self.data
        t = self.cfg["text"]
        practice = self.cfg["practice"]["name"]
        if d.payment_plan:
            text = t["payment_plan"]
        elif d.balance > 0.005:
            text = t["balance_due"]
        else:
            text = t["paid_in_full"]
        text = text.format(practice=practice, paid=money(d.total_payments), balance=money(d.balance))
        self.set_fill_color(*SHADE)
        self.set_font("Helvetica", "", 10)
        self.multi_cell(CONTENT_W, 5.4, _latin(text), fill=True, padding=(2, 3, 2, 3), new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(2)
        self.set_font("Helvetica", "B", 11)
        self.cell(CONTENT_W, 7, _latin(t["reimburse_line"]), align="C", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(3)

    def signature(self) -> None:
        d = self.data
        if self.get_y() > self.h - 40:
            self.add_page()
        sig = self.cfg.get("signature_image") or ""
        self.set_font("Helvetica", "", 9)
        y = self.get_y()
        if sig and os.path.exists(sig):
            self.image(sig, x=MARGIN + 30, y=y - 2, h=14)
            self.set_y(y + 12)
        else:
            self.set_y(y + 8)
        self.set_draw_color(*INK)
        self.line(MARGIN + 30, self.get_y(), MARGIN + 100, self.get_y())
        self.line(MARGIN + 120, self.get_y(), MARGIN + CONTENT_W, self.get_y())
        self.ln(1)
        self.set_text_color(*MUTED)
        self.cell(30, 5, "Provider signature", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_text_color(*INK)
        prov = d.provider
        name = prov.get("name", "")
        if prov.get("credentials"):
            name = f"{name}, {prov['credentials']}"
        self.cell(70, 5, _latin(name), new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.cell(20, 5, "", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_text_color(*MUTED)
        self.cell(12, 5, "Date", new_x=XPos.RIGHT, new_y=YPos.TOP)
        self.set_text_color(*INK)
        self.cell(CONTENT_W - 132, 5, fmt_date(d.statement_date), new_x=XPos.LMARGIN, new_y=YPos.NEXT)


def render_pdf(data: SuperbillData, cfg: Dict[str, Any]) -> bytes:
    pdf = _PDF(data, cfg)
    pdf.add_page()
    pdf.practice_and_title()
    pdf.patient_and_provider()
    pdf.visits_table()
    pdf.totals()
    pdf.statement()
    if cfg.get("show_signature", False):
        pdf.signature()
    return bytes(pdf.output())
