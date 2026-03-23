"""
Maakt achtergrond (o.a. grijs/wit schaakbord) transparant via flood-fill vanaf de randen.
Logo-inhoud (blauw, oranje, wit binnen het kader) blijft intact zolang die niet met de rand verbindt via alleen 'achtergrond'-pixels.
"""
from __future__ import annotations

import argparse
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter


def win_long_path(path: Path) -> str:
    r"""Windows: paden >260 tekens via \\?\ prefix."""
    s = str(path.resolve())
    if sys.platform == "win32" and not s.startswith("\\\\?\\"):
        return "\\\\?\\" + s
    return s


def is_neutral_background(r: int, g: int, b: int) -> bool:
    """
    Wit, bijna-wit, en alle grijze schaakbordvlakken (laag kleurverschil).
    Licht getint blauw-wit (anti-alias in de 'o' van Eco) telt ook mee als gat.
    """
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn > 42:
        if mx >= 218 and mx - mn <= 65:
            return True
        return False
    # Te donker = geen typische rastercel (behalve zwart in lijnwerk — blijft staan)
    if mx < 72:
        return False
    return True


def is_chromatic(r: int, g: int, b: int) -> bool:
    """
    Logo-inkt: blauw, oranje, geel, groen, donkere contouren — moet beschermd blijven.
    """
    mx, mn = max(r, g, b), min(r, g, b)
    if mx - mn >= 34:
        return True
    # Blauw (tekst, omlijning batterij, heuvels)
    if b >= 75 and b > r + 12 and b > g + 8:
        return True
    # Oranje / geel (zon, dak)
    if r >= 95 and r > b + 22 and g >= 40:
        return True
    # Groen (bomen)
    if g >= 70 and g > r + 12 and g > b + 10:
        return True
    # Zeer donker (deur, details)
    if mx < 55:
        return True
    return False


def remove_neutral_background_rgba(img: Image.Image, dilate_size: int = 55) -> Image.Image:
    """
    Verwijdert schaakbord + witte vlakken overal, ook ONDER het logo,
    door chromatische pixels te dilateren tot 'beschermzone' (wit huis binnen batterij blijft staan).
    """
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    assert px is not None

    chrom = Image.new("L", (w, h), 0)
    cp = chrom.load()
    assert cp is not None

    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            if is_chromatic(r, g, b):
                cp[x, y] = 255

    # Groot genoeg om wit vlak binnen de batterij mee te nemen (grenst aan blauw/oranje)
    size = dilate_size if dilate_size % 2 == 1 else dilate_size + 1
    chrom = chrom.filter(ImageFilter.MaxFilter(size=size))

    out = img.copy()
    op = out.load()
    assert op is not None
    cpx = chrom.load()
    assert cpx is not None

    for y in range(h):
        for x in range(w):
            r, g, b, a = op[x, y]
            if a < 128:
                continue
            if cpx[x, y] > 0:
                continue  # beschermd (logo + omgeving na dilatie)
            if is_neutral_background(r, g, b):
                op[x, y] = (r, g, b, 0)

    return out


def exterior_reachable_low_alpha(
    px, w: int, h: int, alpha_threshold: int
) -> list[list[bool]]:
    """
    Pixels met alpha < threshold die via alleen zulke pixels met de beeldrand verbonden zijn.
    Afgesloten transparantie (bv. midden van een 'o' waar stap 2 al doorheen heeft gehaald)
    telt niet mee als 'buiten' — anders blijft de witte anti-alias-ring rond het gat staan.
    """
    ext = [[False] * h for _ in range(w)]
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))
    while q:
        x, y = q.popleft()
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        if ext[x][y]:
            continue
        _, _, _, a = px[x, y]
        if a >= alpha_threshold:
            continue
        ext[x][y] = True
        for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            q.append((x + dx, y + dy))
    return ext


def remove_enclosed_neutral_holes(
    img: Image.Image,
    *,
    max_area: int = 8000,
    max_bbox_side: int = 140,
    max_area_text_region: int = 95000,
    max_bbox_side_text_region: int = 400,
    text_region_min_x_frac: float = 0.30,
    transparent_neighbor_alpha: int = 48,
) -> Image.Image:
    """
    Verwijdert kleine afgesloten neutrale vlakken (wit in de letter-o, -e, enz.) die nergens
    aan transparantie grenzen. Grote witte vlakken (huis in batterij) vallen buiten de
    area/bbox-limiet en blijven staan.

    In het woordgedeelte (rechts, x >= frac*breedte) zijn ruimere limieten: de 'o' in Eco
    kan groter zijn dan andere holtes. Anti-aliasing (alpha ~50–120) telt niet als
    'verbinding met transparant buiten'.

    Transparante buren tellen alleen als 'buiten' als ze met de beeldrand verbonden zijn.
    Zo worden ringen rond lettergaten verwijderd terwijl het echte binnengat al transparant is.
    """
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    assert px is not None

    exterior_transp = exterior_reachable_low_alpha(px, w, h, transparent_neighbor_alpha)

    neutral_on = [[False] * h for _ in range(w)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            if is_neutral_background(r, g, b):
                neutral_on[x][y] = True

    text_x0 = int(w * text_region_min_x_frac)

    visited = [[False] * h for _ in range(w)]
    for sx in range(w):
        for sy in range(h):
            if not neutral_on[sx][sy] or visited[sx][sy]:
                continue
            stack = [(sx, sy)]
            visited[sx][sy] = True
            comp: list[tuple[int, int]] = []
            touches_transparent = False
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        continue
                    if exterior_transp[nx][ny]:
                        touches_transparent = True
                        continue
                    if neutral_on[nx][ny]:
                        if not visited[nx][ny]:
                            visited[nx][ny] = True
                            stack.append((nx, ny))

            if touches_transparent:
                continue
            npx = len(comp)
            xs = [p[0] for p in comp]
            ys = [p[1] for p in comp]
            min_cx = min(xs)
            # Tekst staat rechts; holtes in "Eco/Metric" krijgen ruimere limieten
            if min_cx >= text_x0:
                m_area, m_bb = max_area_text_region, max_bbox_side_text_region
            else:
                m_area, m_bb = max_area, max_bbox_side
            if npx > m_area:
                continue
            bw = max(xs) - min(xs) + 1
            bh = max(ys) - min(ys) + 1
            if max(bw, bh) > m_bb:
                continue
            for cx, cy in comp:
                r, g, b, _ = px[cx, cy]
                px[cx, cy] = (r, g, b, 0)

    return img


def is_dark_hole_fill(r: int, g: int, b: int, *, max_rgb: int) -> bool:
    """Donkere achtergrondkleur die in gesloten letterholtes blijft hangen."""
    return max(r, g, b) <= max_rgb


def remove_enclosed_dark_holes(
    img: Image.Image,
    *,
    hole_max_rgb: int,
    max_area: int = 28000,
    max_bbox_side: int = 220,
    max_area_text_region: int = 110000,
    max_bbox_side_text_region: int = 480,
    text_region_min_x_frac: float = 0.28,
    transparent_neighbor_alpha: int = 48,
) -> Image.Image:
    """
    Na flood_black blijven holtes in 'o', 'e', ruimte tussen 't' en 'r' soms donker
    omdat ze niet met de buitenrand verbonden zijn. Zelfde principe als bij witte holtes.
    """
    img = img.convert("RGBA")
    w, h = img.size
    px = img.load()
    assert px is not None

    exterior_transp = exterior_reachable_low_alpha(px, w, h, transparent_neighbor_alpha)

    dark_on = [[False] * h for _ in range(w)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128:
                continue
            if is_dark_hole_fill(r, g, b, max_rgb=hole_max_rgb):
                dark_on[x][y] = True

    text_x0 = int(w * text_region_min_x_frac)

    visited = [[False] * h for _ in range(w)]
    for sx in range(w):
        for sy in range(h):
            if not dark_on[sx][sy] or visited[sx][sy]:
                continue
            stack = [(sx, sy)]
            visited[sx][sy] = True
            comp: list[tuple[int, int]] = []
            touches_transparent = False
            while stack:
                cx, cy = stack.pop()
                comp.append((cx, cy))
                for dx, dy in ((0, 1), (0, -1), (1, 0), (-1, 0)):
                    nx, ny = cx + dx, cy + dy
                    if nx < 0 or nx >= w or ny < 0 or ny >= h:
                        continue
                    if exterior_transp[nx][ny]:
                        touches_transparent = True
                        continue
                    if dark_on[nx][ny]:
                        if not visited[nx][ny]:
                            visited[nx][ny] = True
                            stack.append((nx, ny))

            if touches_transparent:
                continue
            npx = len(comp)
            xs = [p[0] for p in comp]
            ys = [p[1] for p in comp]
            min_cx = min(xs)
            if min_cx >= text_x0:
                m_area, m_bb = max_area_text_region, max_bbox_side_text_region
            else:
                m_area, m_bb = max_area, max_bbox_side
            if npx > m_area:
                continue
            bw = max(xs) - min(xs) + 1
            bh = max(ys) - min(ys) + 1
            if max(bw, bh) > m_bb:
                continue
            for cx, cy in comp:
                r, g, b, _ = px[cx, cy]
                px[cx, cy] = (r, g, b, 0)

    return img


def flood_transparent_rgba(img: Image.Image) -> Image.Image:
    """Rand-flood: verwijdert achtergrond die met de buitenrand verbonden is (oude aanpak)."""
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    assert pixels is not None

    def is_edge_bg(r: int, g: int, b: int, a: int) -> bool:
        if a < 200:
            return True
        return is_neutral_background(r, g, b)

    transparent_mask = [[False] * h for _ in range(w)]

    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))

    seen: set[tuple[int, int]] = set()
    while q:
        x, y = q.popleft()
        if (x, y) in seen:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        seen.add((x, y))
        r, g, b, a = pixels[x, y]
        if not is_edge_bg(r, g, b, a):
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


def flood_black_background_rgba(img: Image.Image, *, max_rgb: int = 52) -> Image.Image:
    """
    Rand-flood voor effen (bijna) zwarte achtergrond (zoals PNG met #000 rond het logo).
    Alles wat met de beeldrand verbonden is en donker genoeg is, wordt transparant.
    Logo-inkt (blauw/oranje) blijft staan: die heeft hogere RGB-waarden.
    """
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()
    assert pixels is not None

    def is_edge_blackish(r: int, g: int, b: int, a: int) -> bool:
        if a < 200:
            return True
        return max(r, g, b) <= max_rgb

    transparent_mask = [[False] * h for _ in range(w)]
    q: deque[tuple[int, int]] = deque()
    for x in range(w):
        for y in (0, h - 1):
            q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            q.append((x, y))

    seen: set[tuple[int, int]] = set()
    while q:
        x, y = q.popleft()
        if (x, y) in seen:
            continue
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        seen.add((x, y))
        r, g, b, a = pixels[x, y]
        if not is_edge_blackish(r, g, b, a):
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


def process_logo(img: Image.Image) -> Image.Image:
    """
    1) Flood vanaf rand: verwijdert alles wat met de buitenrand verbonden is (wit vlak,
       schaakbord buiten het logo). Gesloten gebieden (raster onder batterij) blijven.
    2) Op wat overblijft: verwijder neutrale pixels (grijs/wit raster) tenzij ze dicht
       bij chromatische logo-inkt liggen (dilatie beschermt o.a. wit huis in het icoon).
    """
    step1 = flood_transparent_rgba(img)
    step2 = remove_neutral_background_rgba(step1, dilate_size=27)
    # Holtes in blauwe letters (o, e, …): wit dat nergens aan transparant grenst
    return remove_enclosed_neutral_holes(step2)


def main() -> int:
    parser = argparse.ArgumentParser(description="Maak logo-achtergrond transparant.")
    parser.add_argument(
        "--black-bg",
        action="store_true",
        help="Zwarte rand-achtergrond transparant maken (header-logo met #000). "
        "Bron: logo-header.png als die bestaat, anders logo-source.png.",
    )
    parser.add_argument(
        "--max-rgb",
        type=int,
        default=52,
        metavar="N",
        help="Met --black-bg: max(r,g,b) voor flood vanaf rand (default 52, anti-alias).",
    )
    parser.add_argument(
        "--hole-max-rgb",
        type=int,
        default=None,
        metavar="N",
        help="Met --black-bg: max(r,g,b) voor gesloten donkere letterholtes (default: min(85, max-rgb+28)).",
    )
    args = parser.parse_args()

    repo = Path(__file__).resolve().parent.parent
    out_path = repo / "logo-header.png"

    if args.black_bg:
        candidates = [
            repo / "logo-header.png",
            repo / "logo-source.png",
            repo / "assets" / "logo-source.png",
        ]
        src = None
        for p in candidates:
            check = Path(win_long_path(p)) if sys.platform == "win32" else p
            if check.is_file():
                src = p
                break
        if src is None:
            print(
                "Geen bron voor --black-bg (logo-header.png of logo-source.png).",
                file=sys.stderr,
            )
            return 1
        img = Image.open(win_long_path(src) if sys.platform == "win32" else str(src))
        out = flood_black_background_rgba(img, max_rgb=args.max_rgb)
        hole_max = (
            args.hole_max_rgb
            if args.hole_max_rgb is not None
            else min(85, args.max_rgb + 28)
        )
        out = remove_enclosed_dark_holes(out, hole_max_rgb=hole_max)
        out.save(out_path, "PNG", optimize=True)
        print(f"OK (black-bg): {src} -> {out_path} ({out_path.stat().st_size} bytes)")
        return 0

    # logo-source.png in repo heeft voorrang (export uit ontwerptool, geen screenshots).
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
    out = process_logo(img)
    out.save(out_path, "PNG", optimize=True)
    print(f"OK: {src} -> {out_path} ({out_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
