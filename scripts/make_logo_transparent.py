"""
Maakt achtergrond (o.a. grijs/wit schaakbord) transparant via flood-fill vanaf de randen.
Logo-inhoud (blauw, oranje, wit binnen het kader) blijft intact zolang die niet met de rand verbindt via alleen 'achtergrond'-pixels.
"""
from __future__ import annotations

import sys
from collections import deque
from pathlib import Path

from PIL import Image


def win_long_path(path: Path) -> str:
    r"""Windows: paden >260 tekens via \\?\ prefix."""
    s = str(path.resolve())
    if sys.platform == "win32" and not s.startswith("\\\\?\\"):
        return "\\\\?\\" + s
    return s


def is_background_pixel(r: int, g: int, b: int, a: int) -> bool:
    if a < 200:
        return True
    # Wit / bijna wit
    if r > 245 and g > 245 and b > 245:
        return True
    # Lichtgrijs (typisch transparantie-preview raster)
    if 150 <= r <= 250 and 150 <= g <= 250 and 150 <= b <= 250:
        if abs(r - g) < 35 and abs(g - b) < 35:
            return True
    return False


def flood_transparent_rgba(img: Image.Image) -> Image.Image:
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    assert pixels is not None

    transparent_mask = [[False] * h for _ in range(w)]

    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))

    seen = set()
    while q:
        x, y = q.popleft()
        if (x, y) in seen:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        seen.add((x, y))
        r, g, b, a = pixels[x, y]
        if not is_background_pixel(r, g, b, a):
            continue
        transparent_mask[x][y] = True
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nx, ny = x + dx, y + dy
            if (nx, ny) not in seen and 0 <= nx < w and 0 <= ny < h:
                q.append((nx, ny))

    out = img.copy()
    op = out.load()
    assert op is not None
    for x in range(w):
        for y in range(h):
            if transparent_mask[x][y]:
                r, g, b, _ = op[x, y]
                op[x, y] = (r, g, b, 0)
    return out


def main() -> int:
    repo = Path(__file__).resolve().parent.parent
    out_path = repo / "logo-header.png"

    candidates = [
        repo / "logo-source.png",
        Path(
            r"C:\Users\maike\.cursor\projects\c-Users-maike-Documents-Cursor-projects-thuisbatterij-calculator-web\assets\c__Users_maike_AppData_Roaming_Cursor_User_workspaceStorage_5439fbc35a7f2149ab24ed7224f424a9_images_Generated_image-0d6666db-e209-47f9-8f97-11dabd27af75.png"
        ),
        repo / "assets" / "logo-source.png",
    ]

    src = None
    for p in candidates:
        check = Path(win_long_path(p)) if sys.platform == "win32" else p
        if check.is_file():
            src = p
            break
    if src is None:
        print("Geen bronbestand gevonden. Zet je logo als repo/logo-source.png en run opnieuw.", file=sys.stderr)
        return 1

    img = Image.open(win_long_path(src) if sys.platform == "win32" else str(src))
    out = flood_transparent_rgba(img)
    out.save(out_path, "PNG", optimize=True)
    print(f"OK: {src} -> {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
