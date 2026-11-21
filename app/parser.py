import re

# English and Russian labels
ALIASES = {
    "title": ("title", "название", "имя"),
    "description": ("description", "описание"),
    "genre": ("genre", "жанр"),
    "language": ("language", "язык"),
    "censorship": ("censorship", "цензура"),
}
LOOKUP = {a: k for k, names in ALIASES.items() for a in names}
KEY = re.compile(r"^\s*(\w+)\s*[:：]\s*(.*)$")
MORE = re.compile(r"^\W*(more files|ещ[её] файлы|дополнительные файлы)\W*$", re.I)
VERSION = re.compile(r"\[\s*(?:v|ver|version|версия)?\s*(\d[\w.\-]*)\s*\]", re.I)


def parse(caption: str):
    """Caption -> dict, or None when there is no Title line."""
    out, cur = {}, None
    for line in caption.splitlines():
        m = KEY.match(line)
        if m and m[1].lower() in LOOKUP:
            cur = LOOKUP[m[1].lower()]
            out[cur] = m[2].strip()
        elif cur and line.strip() and not MORE.match(line):
            out[cur] += "\n" + line.strip()
    if "title" not in out:
        return None
    raw = out["title"]
    v = VERSION.search(raw)
    return {
        "title": re.sub(r"\s*\[.*?\]\s*", " ", raw).strip(),
        "version": v[1] if v else "",
        "description": out.get("description", ""),
        "genre": out.get("genre", "Other"),
        "language": out.get("language", ""),
        "censorship": out.get("censorship", ""),
    }
