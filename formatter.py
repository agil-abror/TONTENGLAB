"""Logika pemformatan daftar pustaka (APA 7, IEEE, MLA 9, Harvard).
Teks miring ditandai dengan *tanda bintang*."""
import re
from datetime import date

MONTHS = {
    "id": ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus",
           "September", "Oktober", "November", "Desember"],
    "en": ["January", "February", "March", "April", "May", "June", "July", "August",
           "September", "October", "November", "December"],
}
LABELS = {
    "id": dict(nd="t.t.", and_="dan", pp="hlm.", vol="vol.", no="no.", acc="Diakses", avail="Tersedia di"),
    "en": dict(nd="n.d.", and_="and", pp="pp.", vol="vol.", no="no.", acc="Accessed", avail="Available at"),
}
STYLES = ["APA 7", "IEEE", "MLA 9", "Harvard"]
TYPES = {"buku": "Buku", "jurnal": "Artikel jurnal", "website": "Situs web", "skripsi": "Skripsi / Tesis / Disertasi"}


# ───────── util ─────────
def s(e, k):
    return str(e.get(k) or "").strip()


def ensure_period(t):
    t = t.strip()
    core = t.rstrip("*")
    return t if (not core or core[-1] in ".?!") else t + "."


def join(*parts):
    return " ".join(p for p in parts if p)


def en_dash(p):
    return re.sub(r"\s*[-–—]+\s*", "–", p)


def clean_doi(d):
    d = (d or "").strip()
    d = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", d, flags=re.I)
    return d


def link_of(e):
    d = clean_doi(s(e, "doi"))
    if d:
        return f"https://doi.org/{d}"
    return s(e, "url")


def parse_authors(text, org=False):
    out = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line:
            continue
        if org:
            out.append({"last": line, "first": ""})
        elif "," in line:
            last, first = [x.strip() for x in line.split(",", 1)]
            out.append({"last": last, "first": first})
        else:
            parts = line.split()
            if len(parts) == 1:
                out.append({"last": line, "first": ""})
            else:
                out.append({"last": parts[-1], "first": " ".join(parts[:-1])})
    return out


def initials(first, sep=" "):
    out = []
    for tok in first.replace(".", ". ").split():
        tok = tok.strip(".")
        if tok:
            out.append("-".join(p[0].upper() + "." for p in tok.split("-") if p))
    return sep.join(out)


def pub_date(e, L, lang, apa=False):
    y = s(e, "year") or L["nd"]
    m = int(e.get("month") or 0)
    d = int(e.get("day") or 0)
    mon = MONTHS[lang][m - 1] if 1 <= m <= 12 else ""
    if apa:
        if mon:
            return f"{y}, {d} {mon}" if d else f"{y}, {mon}"
        return y
    return " ".join(x for x in [str(d) if (d and mon) else "", mon, y] if x)


def accessed_text(e, lang):
    a = s(e, "accessed")
    if not a:
        return ""
    try:
        dt = date.fromisoformat(a)
        return f"{dt.day} {MONTHS[lang][dt.month - 1]} {dt.year}"
    except ValueError:
        return a


# ───────── penulis per gaya ─────────
def _names(authors, fn):
    return [fn(a) for a in authors]


def authors_apa(au):
    n = _names(au, lambda a: f"{a['last']}, {initials(a['first'])}" if a["first"] else a["last"])
    if not n:
        return ""
    if len(n) == 1:
        return n[0]
    if len(n) == 2:
        return f"{n[0]}, & {n[1]}"
    if len(n) <= 20:
        return ", ".join(n[:-1]) + ", & " + n[-1]
    return ", ".join(n[:19]) + ", . . . " + n[-1]


def authors_ieee(au, L):
    n = _names(au, lambda a: f"{initials(a['first'])} {a['last']}" if a["first"] else a["last"])
    if not n:
        return ""
    if len(n) > 6:
        return n[0] + " et al."
    if len(n) == 1:
        return n[0]
    if len(n) == 2:
        return f"{n[0]} {L['and_']} {n[1]}"
    return ", ".join(n[:-1]) + f", {L['and_']} " + n[-1]


def authors_mla(au, L):
    if not au:
        return ""
    a0 = au[0]
    first = f"{a0['last']}, {a0['first']}" if a0["first"] else a0["last"]
    if len(au) == 1:
        return first
    if len(au) == 2:
        a1 = au[1]
        second = f"{a1['first']} {a1['last']}".strip()
        return f"{first}, {L['and_']} {second}"
    return first + ", et al."


def authors_harvard(au, L):
    n = _names(au, lambda a: f"{a['last']}, {initials(a['first'], '')}" if a["first"] else a["last"])
    if not n:
        return ""
    if len(n) > 3:
        return n[0] + " et al."
    if len(n) == 1:
        return n[0]
    return ", ".join(n[:-1]) + f" {L['and_']} " + n[-1]


# ───────── APA 7 ─────────
def apa(e, L, lang):
    au = authors_apa(e["authors"])
    ds = pub_date(e, L, lang, apa=True)
    t, typ, link = s(e, "title"), e["type"], link_of(e)
    ed = s(e, "edition")

    def lead(title_part):
        if au:
            return [ensure_period(au), f"({ds}).", ensure_period(title_part)]
        return [ensure_period(title_part), f"({ds})."]

    if typ == "buku":
        tp = f"*{t}*" + (f" ({ed})" if ed else "")
        return join(*lead(tp), ensure_period(s(e, "publisher")), link)
    if typ == "jurnal":
        vol, iss, pg = s(e, "volume"), s(e, "issue"), en_dash(s(e, "pages"))
        vi = (f"*{vol}*" if vol else "") + (f"({iss})" if iss else "")
        cont = f"*{s(e, 'journal')}*" + (f", {vi}" if vi else "") + (f", {pg}" if pg else "")
        return join(*lead(t), ensure_period(cont), link)
    if typ == "website":
        site = s(e, "site")
        author_name = au.rstrip(".") if au else ""
        site_part = ensure_period(site) if site and site != author_name else ""
        return join(*lead(f"*{t}*"), site_part, link)
    if typ == "skripsi":
        tp = f"*{t}* [{s(e, 'degree')}, {s(e, 'university')}]"
        return join(*lead(tp), link)
    return t


# ───────── IEEE ─────────
def ieee(e, L, lang):
    au = authors_ieee(e["authors"], L)
    t, typ = s(e, "title"), e["type"]
    y = s(e, "year") or L["nd"]
    pre = f"{au}, " if au else ""
    if typ == "jurnal":
        parts = [f"*{s(e, 'journal')}*"]
        if s(e, "volume"):
            parts.append(f"{L['vol']} {s(e, 'volume')}")
        if s(e, "issue"):
            parts.append(f"{L['no']} {s(e, 'issue')}")
        if s(e, "pages"):
            parts.append(f"{L['pp']} {en_dash(s(e, 'pages'))}")
        parts.append(y)
        d = clean_doi(s(e, "doi"))
        if d:
            parts.append(f"doi: {d}")
        base = f'{pre}"{t}," ' + ", ".join(parts) + "."
        return join(base, "" if d else s(e, "url"))
    if typ == "buku":
        ed = s(e, "edition")
        place = f"{s(e, 'city')}: {s(e, 'publisher')}" if s(e, "city") else s(e, "publisher")
        return f"{pre}*{t}*" + (f", {ed.rstrip('.')}." if ed else ".") + f" {place}, {y}."
    if typ == "website":
        acc = accessed_text(e, lang)
        site = s(e, "site")
        return join(f'{pre}"{t},"', ensure_period(site) if site else "", s(e, "url"),
                    f"({L['acc']}: {acc})." if acc else "")
    if typ == "skripsi":
        bits = [s(e, "degree"), s(e, "university"), s(e, "city"), y]
        return f'{pre}"{t}," ' + ", ".join(b for b in bits if b) + "."
    return t


# ───────── MLA 9 ─────────
def mla(e, L, lang):
    au = authors_mla(e["authors"], L)
    t, typ = s(e, "title"), e["type"]
    y = s(e, "year") or L["nd"]
    a = ensure_period(au) if au else ""
    if typ == "jurnal":
        parts = [f"*{s(e, 'journal')}*"]
        if s(e, "volume"):
            parts.append(f"{L['vol']} {s(e, 'volume')}")
        if s(e, "issue"):
            parts.append(f"{L['no']} {s(e, 'issue')}")
        parts.append(y)
        if s(e, "pages"):
            parts.append(f"{L['pp']} {en_dash(s(e, 'pages'))}")
        lk = link_of(e)
        return join(a, f'"{ensure_period(t)}"', ", ".join(parts) + ".", ensure_period(lk) if lk else "")
    if typ == "buku":
        ed = s(e, "edition")
        return join(a, ensure_period(f"*{t}*"), f"{ed}," if ed else "", f"{s(e, 'publisher')}, {y}.")
    if typ == "website":
        dt = pub_date(e, L, lang)
        site = s(e, "site")
        bits = [x for x in [f"*{site}*" if site else "", dt] if x]
        url = s(e, "url")
        acc = accessed_text(e, lang)
        return join(a, f'"{ensure_period(t)}"', ", ".join(bits) + ("," if url else "."),
                    (ensure_period(url) if url else ""), f"{L['acc']} {acc}." if acc else "")
    if typ == "skripsi":
        return join(a, ensure_period(f"*{t}*"), f"{y}.", f"{s(e, 'university')}, {s(e, 'degree')}.")
    return t


# ───────── Harvard ─────────
def harvard(e, L, lang):
    au = authors_harvard(e["authors"], L)
    t, typ = s(e, "title"), e["type"]
    y = s(e, "year") or L["nd"]
    head = f"{au} ({y})" if au else f"({y})"
    if typ == "jurnal":
        vol, iss = s(e, "volume"), s(e, "issue")
        vi = vol + (f"({iss})" if iss else "")
        cont = f"*{s(e, 'journal')}*" + (f", {vi}" if vi else "") + (f", {L['pp']} {en_dash(s(e, 'pages'))}" if s(e, "pages") else "")
        lk = link_of(e)
        return join(head, f"'{t}',", ensure_period(cont), f"{L['avail']}: {lk}" if lk else "")
    if typ == "buku":
        ed = s(e, "edition")
        place = f"{s(e, 'city')}: {s(e, 'publisher')}" if s(e, "city") else s(e, "publisher")
        return join(head, ensure_period(f"*{t}*"), ensure_period(ed) if ed else "", ensure_period(place))
    if typ == "website":
        acc = accessed_text(e, lang)
        url = s(e, "url")
        return join(head, ensure_period(f"*{t}*"), f"{L['avail']}: {url}" if url else "",
                    f"({L['acc']}: {acc})." if acc else "")
    if typ == "skripsi":
        return join(head, ensure_period(f"*{t}*"), ensure_period(s(e, "degree")), ensure_period(s(e, "university")))
    return t


def format_entry(e, style, lang="id"):
    L = LABELS[lang]
    fn = {"APA 7": apa, "IEEE": ieee, "MLA 9": mla, "Harvard": harvard}[style]
    return fn(e, L, lang)


def format_list(entries, style, lang="id"):
    """Kembalikan [(indeks_asli, teks)]. IEEE urut sesuai sitasi, lainnya alfabetis."""
    idx = list(range(len(entries)))
    if style != "IEEE":
        def key(i):
            e = entries[i]
            first = e["authors"][0]["last"] if e["authors"] else s(e, "title")
            return (first.lower(), s(e, "year"), s(e, "title").lower())
        idx.sort(key=key)
    out = []
    for n, i in enumerate(idx, 1):
        txt = format_entry(entries[i], style, lang)
        out.append((i, f"[{n}] {txt}" if style == "IEEE" else txt))
    return out


def check_entry(e):
    """Peringatan kelengkapan (tidak memblokir)."""
    w = []
    if not s(e, "title"):
        w.append("Judul belum diisi.")
    if not e["authors"]:
        w.append("Penulis kosong. Judul akan dipakai sebagai pengganti penulis.")
    if not s(e, "year"):
        w.append("Tahun kosong, akan ditulis sebagai t.t. / n.d.")
    need = {"buku": ["publisher"], "jurnal": ["journal"], "website": ["url"], "skripsi": ["university", "degree"]}
    names = {"publisher": "penerbit", "journal": "nama jurnal", "url": "URL", "university": "universitas", "degree": "jenis tugas akhir"}
    for k in need.get(e["type"], []):
        if not s(e, k):
            w.append(f"Kolom {names[k]} belum diisi.")
    return w
