"""Shared page helpers for the two reports: every number printed in the body goes through num(), which records the value
as printed, the mart it is read from and the value in the page text, for the text-number check."""
import pandas as pd

from analytics.style import style as S


class Page:
    def __init__(self):
        self.trace = []           # (section, value as printed, read from, value in the text)
        self.section = ""
        self.figures = 0
        self.body = []

    # ── numbers ──────────────────────────────────────────────────────────────
    def num(self, x, src, f="{:,.0f}", was=""):
        s = f.format(x)
        self.trace.append((self.section, s, src, was))
        return s

    def pct(self, x, src, d=1, was=""):
        s = f"{x * 100:.{d}f}%"
        self.trace.append((self.section, s, src, was))
        return s

    def word(self, x, src, was=""):
        words = {0: "no", 1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine", 10: "ten"}
        s = words[int(round(x))]
        self.trace.append((self.section, s, src, was))
        return s

    def text(self, s, src, was=""):
        """A value printed as words, such as a date or an identifier, read from a mart."""
        self.trace.append((self.section, s, src, was))
        return s

    # ── layout ───────────────────────────────────────────────────────────────
    def h2(self, anchor, title):
        self.section = title
        self.body.append(f'<h2 id="{anchor}">{title}</h2>')

    def h3(self, anchor, title):
        self.section = title
        self.body.append(f'<h3 id="{anchor}">{title}</h3>')

    def p(self, html):
        self.body.append(f"<p>{html}</p>")

    def ul(self, items):
        self.body.append("<ul>" + "".join(f"<li>{x}</li>" for x in items) + "</ul>")

    def figure(self, img, title, note=None):
        self.figures += 1
        self.body.append(f"<div class='chart-title'>{title}</div>{img}" + (f'<div class="caption">{note}</div>' if note else ""))

    def table(self, title, df, columns, fmt=None, note=None):
        d = df[list(columns)].rename(columns=columns)
        html = S.table(d, fmt or {})          # formats keyed by the column names as shown
        self.body.append(f"<div class='chart-title'>{title}</div>{html}" + (f'<div class="caption">{note}</div>' if note else ""))

    def body_table(self, title, df, columns, fmt=None, bold_cols=(), bold_cells=(), shade_rows=(), caption=None):
        """A table in the body under the house conventions: the column or cells the takeaway rests on in bold, rows outside
        their design range shaded in the warning tint, the range stated in the caption. bold_cells holds (row position,
        column as shown); shade_rows holds row positions."""
        d = df[list(columns)].rename(columns=columns).reset_index(drop=True); fmt = fmt or {}
        assert len(d) <= 8, "a table in the body runs to eight rows at most"
        head = "".join(f"<th>{c}</th>" for c in d.columns); body = ""
        for i, r in d.iterrows():
            cells = ""
            for c in d.columns:
                v = r[c]; f = fmt.get(c)
                s = f(v) if f and v == v and v is not None else ("" if v != v or v is None else str(v))
                if c in bold_cols or (i, c) in bold_cells:
                    s = f"<strong>{s}</strong>"
                num = isinstance(v, (int, float)) and not isinstance(v, bool)
                cells += f'<td class="{"num" if num else ""}">{s}</td>'
            body += f'<tr{" class=" + chr(34) + "warn" + chr(34) if i in shade_rows else ""}>{cells}</tr>'
        self.body.append(f"<div class='chart-title'>{title}</div><table class=\"data\"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"
                         + (f'<div class="caption">{caption}</div>' if caption else ""))

    def figval(self, figure, value, src):
        """A value a figure shows (a label, a bar's length written on it, a reference line), traced to its mart."""
        self.trace.append((f"Figure {figure}", value, src, ""))
        return value

    def raw(self, html):
        self.body.append(html)

    # ── the text-number check ────────────────────────────────────────────────
    def check(self):
        t = pd.DataFrame(self.trace, columns=["section", "value_as_printed", "read_from", "value_in_the_text"])
        off = t[(t["value_in_the_text"] != "") & (t["value_as_printed"].str.lower() != t["value_in_the_text"].str.lower())]
        return t, off


def F0(v):
    return f"{v:,.0f}"


def F1(v):
    return f"{v:,.1f}"


def F2(v):
    return f"{v:,.2f}"


def F3(v):
    return f"{v:,.3f}"


def F4(v):
    return f"{v:,.4f}"


def P1(v):
    return f"{v * 100:.1f}%"


def P0(v):
    return f"{v * 100:.0f}%"


def DAY(v):
    return "" if v is None or pd.isna(v) else pd.Timestamp(v).strftime("%d %B %Y").lstrip("0")


def YN(v):
    return "yes" if v else "no"
