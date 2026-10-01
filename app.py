import streamlit as st
import qrcode
from qrcode.constants import (
    ERROR_CORRECT_L, ERROR_CORRECT_M, ERROR_CORRECT_Q, ERROR_CORRECT_H,
)
from PIL import Image, ImageDraw, ImageFont
import io, os, re, math, urllib.parse

st.set_page_config(page_title="Kafe QR Atölyesi", page_icon="☕", layout="wide")

# ------------------------------------------------------------------ sabitler
DPI = 300
PX_PER_MM = DPI / 25.4
def mm_to_px(mm: float) -> int:
    return int(round(mm * PX_PER_MM))

EC_MAP = {'L': ERROR_CORRECT_L, 'M': ERROR_CORRECT_M,
          'Q': ERROR_CORRECT_Q, 'H': ERROR_CORRECT_H}

DEFAULT_CAPTIONS = {
    'menu':   'Menüyü görmek için okutun',
    'wifi':   "Wi-Fi'ye bağlanmak için okutun",
    'review': "Bizi Google'da değerlendirin",
    'insta':  "Bizi Instagram'da takip edin",
    'iban':   "IBAN'ı kopyalamak için okutun",
    'wa':     "WhatsApp'tan bize yazın",
}

TYPE_NAMES = {
    'menu':   'Menü',
    'wifi':   'Wi-Fi',
    'review': 'Google yorum',
    'insta':  'Instagram',
    'iban':   'IBAN',
    'wa':     'WhatsApp',
}

PAPER_SIZES = {
    'A3 (297 × 420 mm)':      (297.0, 420.0),
    'A4 (210 × 297 mm)':      (210.0, 297.0),
    'A5 (148 × 210 mm)':      (148.0, 210.0),
    'A6 (105 × 148 mm)':      (105.0, 148.0),
    'Letter (216 × 279 mm)':  (215.9, 279.4),
    'Legal (216 × 356 mm)':   (215.9, 355.6),
    'B5 (176 × 250 mm)':      (176.0, 250.0),
    '10 × 15 cm (fotoğraf)':  (100.0, 150.0),
    '13 × 18 cm':             (130.0, 180.0),
}

PRESET_COLORS = [
    ("Siyah",       "#111111"),
    ("Gece yeşili", "#14201B"),
    ("Lacivert",    "#1B2A4A"),
    ("Kahve",       "#3A2217"),
    ("Zümrüt",      "#0F5C4D"),
]

# ------------------------------------------------------------------ fontlar
FONT_REG_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "C:/Windows/Fonts/segoeui.ttf",
]
FONT_BOLD_PATHS = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/segoeuib.ttf",
]
def _pick(paths):
    for p in paths:
        if p and os.path.exists(p):
            return p
    return None

FONT_REG  = _pick(FONT_REG_PATHS)
FONT_BOLD = _pick(FONT_BOLD_PATHS) or FONT_REG

@st.cache_resource(show_spinner=False)
def get_font(size: int, bold: bool = False):
    path = FONT_BOLD if bold else FONT_REG
    if path:
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            pass
    try:
        return ImageFont.load_default(size)
    except Exception:
        return ImageFont.load_default()

# ------------------------------------------------------------------ yardımcı
def hex_to_rgb(h: str):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def wrap_text(draw, text, font, max_width):
    if not text:
        return []
    words = text.split()
    lines, cur = [], ''
    for w in words:
        test = (cur + ' ' + w).strip()
        try:
            tw = draw.textlength(test, font=font)
        except Exception:
            tw = len(test) * 10
        if tw <= max_width or not cur:
            cur = test
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines

@st.cache_data(show_spinner=False, max_entries=500)
def qr_matrix(data: str, ecc: str):
    qr = qrcode.QRCode(version=None, error_correction=EC_MAP[ecc],
                       box_size=1, border=0)
    qr.add_data(data)
    qr.make(fit=True)
    return [[bool(c) for c in row] for row in qr.modules]

def render_qr(matrix, target_px: int, color_hex: str, border: int = 4) -> Image.Image:
    n = len(matrix)
    total = n + 2 * border
    box = max(1, target_px // total)
    size = total * box
    img = Image.new('RGB', (size, size), 'white')
    draw = ImageDraw.Draw(img)
    fill = hex_to_rgb(color_hex)
    for i, row in enumerate(matrix):
        for j, dark in enumerate(row):
            if dark:
                x, y = (j + border) * box, (i + border) * box
                draw.rectangle([x, y, x + box - 1, y + box - 1], fill=fill)
    if size != target_px:
        img = img.resize((target_px, target_px), Image.NEAREST)
    return img

def qr_to_svg(matrix, color_hex: str, border: int = 4, size: int = 800) -> str:
    n = len(matrix)
    total = n + 2 * border
    parts = []
    for i, row in enumerate(matrix):
        for j, dark in enumerate(row):
            if dark:
                parts.append(f"M{j+border} {i+border}h1v1h-1z")
    d = "".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {total} {total}" '
        f'width="{size}" height="{size}" shape-rendering="crispEdges">'
        f'<rect width="{total}" height="{total}" fill="#FFFFFF"/>'
        f'<path d="{d}" fill="{color_hex}"/></svg>'
    )

# ------------------------------------------------------------------ doğrulama
def norm_url(u: str):
    u = u.strip()
    if not u:
        return None
    if not re.match(r'^https?://', u, re.I):
        u = 'https://' + u
    if not re.match(r'^https?://[^\s/]+\.[^\s/]{2,}', u, re.I):
        return None
    return u

def iban_valid(s: str) -> bool:
    s = re.sub(r'\s+', '', s).upper()
    if not re.match(r'^[A-Z]{2}[0-9]{2}[A-Z0-9]{11,30}$', s):
        return False
    if s.startswith('TR') and len(s) != 26:
        return False
    r = s[4:] + s[:4]
    rem = 0
    for ch in r:
        v = ch if ch.isdigit() else str(ord(ch) - 55)
        for dch in v:
            rem = (rem * 10 + int(dch)) % 97
    return rem == 1

def wa_number(s: str):
    d = re.sub(r'\D', '', s or '')
    if d.startswith('00'):
        d = d[2:]
    elif d.startswith('0'):
        d = '90' + d[1:]
    elif len(d) == 10 and d.startswith('5'):
        d = '90' + d
    return d if 10 <= len(d) <= 15 else None

def esc_wifi(s: str) -> str:
    return re.sub(r'([\\;,:"])', r'\\\1', s)

# ------------------------------------------------------------------ payload
def build_payload(qr_type, v):
    if qr_type == 'menu':
        u = (v.get('url') or '').strip()
        if not u:
            return None, None, None
        url = norm_url(u)
        if not url:
            return None, None, "Geçerli bir web adresi girin."
        shown = re.sub(r'^https?://', '', url, flags=re.I).rstrip('/')
        return url, ([shown] if len(shown) <= 42 else []), None

    if qr_type == 'wifi':
        ssid = (v.get('ssid') or '').strip()
        if not ssid:
            return None, None, None
        sec = v.get('security') or 'WPA'
        pw = v.get('pw') or ''
        if sec != 'nopass' and not pw:
            return None, None, 'Şifre girin ya da "Şifresiz" seçin.'
        data = (f"WIFI:T:{sec};S:{esc_wifi(ssid)};"
                + ("" if sec == 'nopass' else f"P:{esc_wifi(pw)};")
                + f"H:{'true' if v.get('hidden') else 'false'};;")
        sub = [f"Ağ: {ssid}"]
        if v.get('showpw') and sec != 'nopass':
            sub.append(f"Şifre: {pw}")
        return data, sub, None

    if qr_type == 'review':
        s = (v.get('input') or '').strip()
        if not s:
            return None, None, None
        if re.match(r'^https?://', s, re.I):
            return s, [], None
        if re.match(r'^[A-Za-z0-9_-]{20,}$', s):
            return f"https://search.google.com/local/writereview?placeid={s}", [], None
        return None, None, 'Bağlantı ya da Place ID tanınmadı.'

    if qr_type == 'insta':
        u = (v.get('user') or '').strip()
        if not u:
            return None, None, None
        u = re.sub(r'^https?://(www\.)?instagram\.com/', '', u, flags=re.I)
        u = u.lstrip('@').split('/')[0].split('?')[0].split('#')[0]
        if not re.match(r'^[A-Za-z0-9._]{1,30}$', u):
            return None, None, 'Kullanıcı adı harf, rakam, nokta ve alt çizgi içerebilir.'
        return f"https://instagram.com/{u}", [f"@{u}"], None

    if qr_type == 'iban':
        s = re.sub(r'\s+', '', (v.get('iban') or '')).upper()
        if not s:
            return None, None, None
        if not iban_valid(s):
            return None, None, 'IBAN geçersiz görünüyor; rakamları kontrol edin.'
        sub = []
        holder = (v.get('holder') or '').strip()
        if holder:
            sub.append(holder)
        sub.append(' '.join(s[i:i+4] for i in range(0, len(s), 4)))
        return s, sub, None

    if qr_type == 'wa':
        p = (v.get('phone') or '').strip()
        if not p:
            return None, None, None
        n = wa_number(p)
        if not n:
            return None, None, 'Telefon numarası geçersiz görünüyor.'
        msg = (v.get('msg') or '').strip()
        url = f"https://wa.me/{n}"
        if msg:
            url += "?text=" + urllib.parse.quote(msg)
        return url, [f"+{n}"], None

    return None, None, None

# ------------------------------------------------------------------ kart
def build_card(cfg, card_w_mm: float, card_h_mm: float):
    W = mm_to_px(card_w_mm)
    H = mm_to_px(card_h_mm)
    card = Image.new('RGB', (W, H), 'white')
    draw = ImageDraw.Draw(card)

    color = cfg['color']

    bar_h = max(8, int(H * 0.018))
    draw.rectangle([0, 0, W, bar_h], fill=color)

    margin = int(W * 0.07)
    inner_w = W - 2 * margin

    f_title = get_font(max(18, int(W * 0.090)), bold=True)
    f_cap   = get_font(max(13, int(W * 0.058)), bold=True)
    f_sub   = get_font(max(10, int(W * 0.040)), bold=False)

    def lh(font):
        bbox = draw.textbbox((0, 0), "Ağ", font=font)
        return int((bbox[3] - bbox[1]) * 1.45)

    lh_t, lh_c, lh_s = lh(f_title), lh(f_cap), lh(f_sub)

    title = (cfg.get('title') or '').strip()
    caption = (cfg.get('caption') or '').strip() or DEFAULT_CAPTIONS.get(cfg['type'], '')
    subs = cfg.get('sub') or []

    title_lines = wrap_text(draw, title, f_title, inner_w) if title else []
    cap_lines   = wrap_text(draw, caption, f_cap, inner_w) if caption else []
    sub_lines = []
    for s in subs:
        sub_lines.extend(wrap_text(draw, s, f_sub, inner_w))

    reserved = (len(title_lines) * lh_t + len(cap_lines) * lh_c
                + len(sub_lines) * lh_s + margin * 2
                + (margin // 2 if title_lines else 0)
                + (margin // 2 if cap_lines or sub_lines else 0))

    qr_space = H - bar_h - margin - reserved
    qr_size = max(120, min(inner_w, qr_space))

    matrix = qr_matrix(cfg['data'], cfg['ecc'])
    qr_img = render_qr(matrix, qr_size, color, border=4)

    y = bar_h + margin
    for line in title_lines:
        tw = draw.textlength(line, font=f_title)
        draw.text(((W - tw) // 2, y), line, font=f_title, fill='#111111')
        y += lh_t
    if title_lines:
        y += margin // 2

    qr_x = (W - qr_size) // 2
    card.paste(qr_img, (qr_x, y))
    y += qr_size
    if cap_lines or sub_lines:
        y += margin // 2

    for line in cap_lines:
        tw = draw.textlength(line, font=f_cap)
        draw.text(((W - tw) // 2, y), line, font=f_cap, fill='#111111')
        y += lh_c
    for line in sub_lines:
        tw = draw.textlength(line, font=f_sub)
        draw.text(((W - tw) // 2, y), line, font=f_sub, fill='#4A4A4A')
        y += lh_s

    meta = {
        'qr_px': qr_size,
        'qr_mm': qr_size / PX_PER_MM,
        'modules': len(matrix),
        'matrix': matrix,
        'card_w_mm': card_w_mm,
        'card_h_mm': card_h_mm,
    }
    return card, meta

# ------------------------------------------------------------------ optimum düzen
def compute_layouts(paper_mm, margin_mm, gap_mm, min_qr_mm=30,
                    max_cards=32, min_card_mm=45):
    """
    Belirtilen kağıt/marj/boşluk ve minimum okunabilir QR boyutu için
    tüm geçerli (kolon, satır) düzenlerini hesaplar.
    Kart genişliği 45 mm'den, yüksekliği 55 mm'den küçük olanları eler.
    Aspect oranı 0.5–1.15 arasında tutulur (dikey kartlar).
    """
    pw, ph = paper_mm
    options = []
    for cols in range(1, 8):
        for rows in range(1, 11):
            cards = cols * rows
            if cards > max_cards:
                continue
            cw = (pw - 2*margin_mm - (cols - 1) * gap_mm) / cols
            ch = (ph - 2*margin_mm - (rows - 1) * gap_mm) / rows
            if cw < min_card_mm or ch < 55:
                continue
            if cw > 170 or ch > 240:
                continue
            aspect = cw / ch
            if aspect < 0.50 or aspect > 1.15:
                continue
            # QR boyutu tahmini: genişliğin ~%85'i, yüksekliğin ~%62'si
            qr_est = min(cw * 0.85, ch * 0.62)
            if qr_est < min_qr_mm:
                continue
            options.append({
                'cols': cols,
                'rows': rows,
                'cards': cards,
                'card_w': round(cw, 1),
                'card_h': round(ch, 1),
                'qr_est_mm': round(qr_est, 1),
                'aspect': round(aspect, 2),
            })
    # En çok kart → en büyük alan
    options.sort(key=lambda x: (-x['cards'], -(x['card_w'] * x['card_h'])))
    return options

def layout_diagram_text(chosen):
    """Küçük ASCII şema."""
    return f"{chosen['cols']} kolon × {chosen['rows']} satır"

# ------------------------------------------------------------------ sayfa
def _dashed(draw, x1, y1, x2, y2, color=(190, 190, 190), dash=18, gap=14):
    length = math.hypot(x2 - x1, y2 - y1)
    if length < 1:
        return
    dx, dy = (x2 - x1) / length, (y2 - y1) / length
    pos = 0
    while pos < length:
        e = min(pos + dash, length)
        draw.line([(x1 + dx*pos, y1 + dy*pos), (x1 + dx*e, y1 + dy*e)],
                  fill=color, width=2)
        pos = e + gap

def build_sheet_pages(cards_cfg, paper_mm, card_w_mm, card_h_mm,
                      margin_mm=10, gap_mm=5, cut_marks=True):
    pw, ph = paper_mm
    W = mm_to_px(pw); H = mm_to_px(ph)
    m = mm_to_px(margin_mm); g = mm_to_px(gap_mm)
    cw = mm_to_px(card_w_mm); ch = mm_to_px(card_h_mm)

    cols = max(1, int((W - 2*m + g) // (cw + g)))
    rows = max(1, int((H - 2*m + g) // (ch + g)))
    per_page = cols * rows

    imgs = [build_card(c, card_w_mm, card_h_mm)[0] for c in cards_cfg]

    grid_w = cols * cw + (cols - 1) * g
    grid_h = rows * ch + (rows - 1) * g
    ox = (W - grid_w) // 2
    oy = (H - grid_h) // 2

    pages = []
    for start in range(0, len(imgs), per_page):
        page = Image.new('RGB', (W, H), 'white')
        pdraw = ImageDraw.Draw(page)
        chunk = imgs[start:start + per_page]
        for j, ci in enumerate(chunk):
            col = j % cols
            row = j // cols
            x = ox + col * (cw + g)
            y = oy + row * (ch + g)
            page.paste(ci, (x, y))
        if cut_marks:
            for col in range(1, cols):
                x = int(ox + col * cw + (col - 0.5) * g)
                _dashed(pdraw, x, oy, x, oy + grid_h)
            for row in range(1, rows):
                y = int(oy + row * ch + (row - 0.5) * g)
                _dashed(pdraw, ox, y, ox + grid_w, y)
        pages.append(page)

    return pages, per_page, (cols, rows)

# ------------------------------------------------------------------ form
def render_form(qr_type):
    if qr_type == 'menu':
        url = st.text_input(
            "Menü bağlantısı", key='menu_url',
            placeholder="kafem.com/menu",
            help="Web sayfası, PDF ya da QR menü servisi bağlantısı olabilir. "
                 "Kısa bağlantı daha kolay okunur.")
        return {'url': url}

    if qr_type == 'wifi':
        ssid = st.text_input("Ağ adı (SSID)", key='wifi_ssid', placeholder="KafeWiFi")
        sec = st.selectbox(
            "Güvenlik", options=['WPA', 'WEP', 'nopass'],
            format_func=lambda x: {'WPA': 'WPA / WPA2 / WPA3 (çoğu modem)',
                                   'WEP': 'WEP (eski)',
                                   'nopass': 'Şifresiz'}[x],
            key='wifi_sec')
        if sec == 'nopass':
            st.caption("Şifresiz ağ seçildi.")
            pw = ''
        else:
            pw = st.text_input("Şifre", key='wifi_pw')
        hidden = st.checkbox("Gizli ağ", key='wifi_hidden')
        showpw = st.checkbox("Şifreyi kartın üstüne de yaz", key='wifi_showpw')
        return {'ssid': ssid, 'security': sec, 'pw': pw,
                'hidden': hidden, 'showpw': showpw}

    if qr_type == 'review':
        s = st.text_input(
            "Yorum bağlantısı ya da Place ID",
            key='review_input',
            placeholder="https://g.page/r/.../review",
            help="Google İşletme Profili'nde 'Yorum isteyin' bağlantısını yapıştırın. "
                 "Bağlantı yoksa Place ID (ChIJ… ile başlar) de olur.")
        return {'input': s}

    if qr_type == 'insta':
        u = st.text_input(
            "Kullanıcı adı", key='insta_user', placeholder="kafem",
            help="@ ile ya da profil bağlantısı olarak da yapıştırabilirsiniz.")
        return {'user': u}

    if qr_type == 'iban':
        holder = st.text_input("Hesap sahibi (kartta görünür)",
                               key='iban_holder',
                               placeholder="Ad Soyad / Unvan")
        iban = st.text_input("IBAN", key='iban_val',
                             placeholder="TR00 0000 0000 0000 0000 0000 00",
                             help="Kontrol basamağı doğrulanır.")
        return {'holder': holder, 'iban': iban}

    if qr_type == 'wa':
        phone = st.text_input("Telefon numarası", key='wa_phone',
                              placeholder="0532 000 00 00")
        msg = st.text_input("Hazır mesaj (isteğe bağlı)", key='wa_msg',
                            placeholder="Merhaba, rezervasyon yapmak istiyorum")
        return {'phone': phone, 'msg': msg}

    return {}

# ------------------------------------------------------------------ state
if 'set_list' not in st.session_state:
    st.session_state.set_list = []

# ------------------------------------------------------------------ header
st.title("☕ Kafe QR Atölyesi")
st.caption("Menü, Wi-Fi, Google yorum, Instagram, IBAN ve WhatsApp için "
           "telefonla ilk denemede okunan, baskıya hazır kartlar hazırlayın.")

# ------------------------------------------------------------------ sidebar
with st.sidebar:
    st.header("🖨️ Baskı ayarları")
    paper_key = st.selectbox("Kağıt boyutu", list(PAPER_SIZES.keys()), index=1)
    paper_mm = PAPER_SIZES[paper_key]

    st.markdown("**Sayfa boşlukları**")
    margin_mm = st.slider("Kenar boşluğu (mm)", 0, 30, 10, 1,
                          help="Yazıcının kenar payı. Genelde 8–12 mm yeterli.")
    gap_mm    = st.slider("Kartlar arası boşluk (mm)", 0, 15, 5, 1)

    st.markdown("**Okunabilirlik kısıtı**")
    min_qr_mm = st.slider(
        "Minimum QR boyutu (mm)", 20, 80, 30, 1,
        help="Her kartın içindeki QR en az bu büyüklükte olur. "
             "Masa mesafesi için 30 mm iyi bir eşiktir; yakın okutma için 25 mm.")

    st.markdown("**Boyutlandırma**")
    sizing_mode = st.radio(
        "Mod",
        ["Otomatik (optimum)", "Manuel"],
        horizontal=True, label_visibility="collapsed")

    if sizing_mode == "Otomatik (optimum)":
        layouts = compute_layouts(
            paper_mm, margin_mm, gap_mm,
            min_qr_mm=min_qr_mm, max_cards=32, min_card_mm=45)

        if not layouts:
            st.error("Bu kısıtlarla uygun düzen bulunamadı. "
                     "Kenar boşluğunu/aralığı azaltın ya da minimum QR boyutunu düşürün.")
            card_w_mm, card_h_mm = 85.0, 110.0
            _cols, _rows = 2, 2
            chosen = None
        else:
            def fmt(i):
                o = layouts[i]
                return (f"{o['cols']} × {o['rows']}  →  {o['cards']} kart   ·   "
                        f"her biri {o['card_w']:.0f} × {o['card_h']:.0f} mm   "
                        f"(QR ≈ {o['qr_est_mm']:.0f} mm)")

            sel = st.selectbox(
                "Sayfa düzeni", range(len(layouts)),
                format_func=fmt, index=0,
                help="Kart sayısına göre azalan sırada. Minimum QR boyutunu "
                     "karşılayan tüm geçerli düzenler listelenir.")
            chosen = layouts[sel]
            card_w_mm = chosen['card_w']
            card_h_mm = chosen['card_h']
            _cols, _rows = chosen['cols'], chosen['rows']

            # Kaç sayfa gerektiği bilgisi
            n_cards_in_set = len(st.session_state.set_list)
            if n_cards_in_set > 0:
                per = chosen['cards']
                pages_needed = math.ceil(n_cards_in_set / per)
                st.caption(f"Setinizde {n_cards_in_set} kart var → "
                           f"**{pages_needed} sayfa** {paper_key.split(' ')[0]} gerekir.")
    else:
        card_w_mm = st.slider("Kart genişliği (mm)", 40, 170, 85, 1)
        card_h_mm = st.slider("Kart yüksekliği (mm)", 40, 240, 110, 1)
        _cols = max(1, int((paper_mm[0] - 2*margin_mm + gap_mm) // (card_w_mm + gap_mm)))
        _rows = max(1, int((paper_mm[1] - 2*margin_mm + gap_mm) // (card_h_mm + gap_mm)))
        chosen = None

    st.divider()
    cut_marks = st.checkbox("Kesim çizgileri", value=True)

    st.markdown("**Hata düzeltme (ECC)**")
    ecc = st.selectbox(
        "Okunabilirlik düzeyi",
        options=['M', 'Q', 'H', 'L'],
        format_func=lambda x: {
            'M': 'Orta (önerilen)',
            'Q': 'Yüksek (yıpranmaya dayanıklı)',
            'H': 'Çok yüksek (en sağlam, kod yoğunlaşır)',
            'L': 'Düşük (en sade kod)',
        }[x], index=0,
        help="Yüksek düzey, QR'ın bir kısmı hasar görse bile okunmasını sağlar.")

    st.divider()
    st.metric("Sayfa başına", f"{_cols * _rows} kart", f"{_cols} × {_rows}")

    if sizing_mode == "Otomatik (optimum)" and chosen:
        st.caption(
            f"Her kart: **{card_w_mm:.0f} × {card_h_mm:.0f} mm**  ·  "
            f"QR ≈ **{chosen['qr_est_mm']:.0f} mm**")
        st.caption("Optimum düzen: QR okunabilirliği korunarak sayfaya "
                   "sığdırılabilecek maksimum kart sayısı.")

# ------------------------------------------------------------------ ana bölüm
col1, col2 = st.columns([1, 1], gap="large")

with col1:
    st.subheader("1. QR türünü seçin")
    qr_type = st.radio(
        "QR türü",
        options=list(TYPE_NAMES.keys()),
        format_func=lambda k: TYPE_NAMES[k],
        horizontal=True, label_visibility='collapsed', key='qr_type')

    st.subheader("2. Bilgileri doldurun")
    vals = render_form(qr_type)

    st.subheader("3. Kart görünümü")
    title = st.text_input("Kafe adı (kartın üstünde)",
                          key='card_title', placeholder="Örn. Moda Kahve")
    caption = st.text_input(
        "Kartın alt yazısı", key=f'caption_{qr_type}',
        placeholder=DEFAULT_CAPTIONS[qr_type])

    st.markdown("**QR rengi**")
    color_name = st.radio(
        "Renk", options=[c[0] for c in PRESET_COLORS],
        horizontal=True, label_visibility='collapsed', key='color_name')
    color_hex = dict(PRESET_COLORS)[color_name]
    st.caption("Koyu renkler en güvenlisidir; siyah her kamerada okunur.")

# ------------------------------------------------------------------ önizleme
data, sub, err = build_payload(qr_type, vals)

with col2:
    st.subheader("Önizleme")

    if err:
        st.error(err)
    elif not data:
        st.info("Bilgileri doldurun; kart burada belirecek.")
    else:
        cfg = {
            'type':    qr_type,
            'data':    data,
            'sub':     sub or [],
            'title':   title,
            'caption': caption,
            'color':   color_hex,
            'ecc':     ecc,
        }
        try:
            card_img, meta = build_card(cfg, card_w_mm, card_h_mm)
            st.image(card_img, use_container_width=True)

            buf = io.BytesIO()
            card_img.save(buf, 'PNG')
            fname_base = (title or TYPE_NAMES[qr_type]).lower().replace(' ', '-')
            fname_base = re.sub(r'[^a-z0-9\-]+', '', fname_base) or 'kart'

            d1, d2, d3 = st.columns(3)
            with d1:
                st.download_button(
                    "📥 Kartı indir", data=buf.getvalue(),
                    file_name=f"{fname_base}-{qr_type}-qr.png",
                    mime="image/png", use_container_width=True)
            with d2:
                svg = qr_to_svg(meta['matrix'], color_hex)
                st.download_button(
                    "🧩 QR (SVG)", data=svg.encode('utf-8'),
                    file_name=f"{fname_base}-{qr_type}-qr.svg",
                    mime="image/svg+xml", use_container_width=True)
            with d3:
                if st.button("➕ Sete ekle", use_container_width=True):
                    st.session_state.set_list.append(cfg)
                    st.success("Sete eklendi.")
                    st.rerun()

            st.markdown("---")
            st.markdown("**🔍 Okunabilirlik kontrolü**")
            n = meta['modules']
            qr_mm = meta['qr_mm']
            module_mm = qr_mm / (n + 8) if n else 0

            if n <= 33:
                dens = "Sade kod — her telefon kolay okur."
            elif n <= 45:
                dens = "Orta yoğunlukta kod — masa mesafesinde sorunsuz okunur."
            else:
                dens = ("Yoğun kod — içeriği kısaltmayı ya da hata düzeltmeyi "
                        "düşürmeyi deneyin.")

            st.markdown(
                f"- {dens} ({n}×{n} nokta)\n"
                f"- Baskıdaki QR boyutu: **{qr_mm:.1f} mm**\n"
                f"- Modül boyutu: **{module_mm:.2f} mm**")

            if module_mm < 0.4:
                st.warning("Modül boyutu 0,4 mm'nin altında. Daha büyük kart ya da "
                           "daha kısa içerik kullanın; yazıcıda bulanabilir.")
            elif module_mm < 0.55:
                st.info("Modül boyutu sınırda. 300 DPI mat kağıtta çıktı alın.")
            else:
                st.success(f"QR yazdırmaya hazır görünüyor (~{qr_mm/10:.1f} cm).")

            # Düzen bilgisi
            if sizing_mode == "Otomatik (optimum)" and chosen:
                st.caption(
                    f"Seçili düzen: {layout_diagram_text(chosen)} · "
                    f"{chosen['cards']} kart/sayfa · "
                    f"kart {card_w_mm:.0f}×{card_h_mm:.0f} mm")
            else:
                st.caption(
                    f"Düzen: {_cols}×{_rows} · {_cols*_rows} kart/sayfa · "
                    f"kart {card_w_mm:.0f}×{card_h_mm:.0f} mm")

            st.caption("QR içeriği:")
            st.code(data, language=None)

        except Exception as e:
            st.error(f"Kart oluşturulamadı: {e}")

# ------------------------------------------------------------------ optimum özet
if sizing_mode == "Otomatik (optimum)" and layouts:
    with st.expander(f"📐 {paper_key.split(' ')[0]} için tüm uygun düzenler "
                     f"({len(layouts)} seçenek)", expanded=False):
        st.caption(
            f"Kenar boşluğu {margin_mm} mm, kartlar arası {gap_mm} mm, "
            f"minimum QR {min_qr_mm} mm. Liste kart sayısına göre azalan sırada.")
        rows_data = []
        for o in layouts:
            rows_data.append({
                "Düzen": f"{o['cols']} × {o['rows']}",
                "Kart/sayfa": o['cards'],
                "Kart (mm)": f"{o['card_w']:.0f} × {o['card_h']:.0f}",
                "QR ~ (mm)": f"{o['qr_est_mm']:.0f}",
                "En/boy": f"{o['aspect']:.2f}",
            })
        st.dataframe(rows_data, hide_index=True, use_container_width=True)

        st.caption(
            "**Not:** Karta üst başlık, alt yazı veya uzun IBAN/adres "
            "eklendiğinde QR biraz küçülebilir. Kartın gerçek önizlemesini "
            "sağdaki panelde kontrol edin; modül boyutu 0,4 mm altına "
            "düşüyorsa bir üst düzene geçin.")

# ------------------------------------------------------------------ set
st.divider()
st.subheader(f"🧩 Kafenin QR seti — {len(st.session_state.set_list)} kart")

if st.session_state.set_list:
    thumb_cols = st.columns(4)
    to_remove = None
    for i, c in enumerate(st.session_state.set_list):
        with thumb_cols[i % 4]:
            try:
                timg, _ = build_card(c, 60, 78)
                st.image(timg, use_container_width=True)
                label = TYPE_NAMES[c['type']]
                if c.get('title'):
                    label += f" · {c['title']}"
                st.caption(label)
                if st.button("🗑️ Kaldır", key=f"rm_{i}",
                             use_container_width=True):
                    to_remove = i
            except Exception:
                st.warning("Kart gösterilemedi")
    if to_remove is not None:
        st.session_state.set_list.pop(to_remove)
        st.rerun()

    cA, cB = st.columns([1, 3])
    with cA:
        if st.button("🗑️ Seti temizle", use_container_width=True):
            st.session_state.set_list = []
            st.rerun()

    n_set = len(st.session_state.set_list)
    per_page = _cols * _rows
    pages_needed = math.ceil(n_set / per_page)
    st.markdown(
        f"**{paper_key}** · düzen **{_cols}×{_rows}** = {per_page} kart/sayfa · "
        f"**{n_set} kart → {pages_needed} sayfa**  \n"
        "Sayfaları 300 DPI PNG olarak indirin, kenar boşluklarını koruyarak "
        "yazdırın ve kesim çizgilerinden kesin.")

    if st.button("📄 Sayfaları oluştur", type="primary"):
        with st.spinner("Sayfalar hazırlanıyor..."):
            pages, per, (cc, rr) = build_sheet_pages(
                st.session_state.set_list, paper_mm,
                card_w_mm, card_h_mm, margin_mm, gap_mm, cut_marks)
        st.session_state['_pages_ready'] = True

    if st.session_state.get('_pages_ready'):
        try:
            pages, per, (cc, rr) = build_sheet_pages(
                st.session_state.set_list, paper_mm,
                card_w_mm, card_h_mm, margin_mm, gap_mm, cut_marks)
            for i, page in enumerate(pages):
                buf = io.BytesIO()
                page.save(buf, 'PNG')
                st.download_button(
                    f"📥 Sayfa {i+1} indir ({per} kart · {cc}×{rr})",
                    data=buf.getvalue(),
                    file_name=f"qr-seti-sayfa-{i+1}.png",
                    mime="image/png", key=f"pg_dl_{i}")
                with st.expander(f"Sayfa {i+1} önizleme"):
                    st.image(page, use_container_width=True)
        except Exception as e:
            st.error(f"Sayfalar oluşturulamadı: {e}")

else:
    st.caption("Henüz kart eklenmedi. Yukarıdan bir kart hazırlayıp "
               "'Sete ekle' butonuna basın.")

# ------------------------------------------------------------------ ipuçları
st.divider()
with st.expander("📌 Basarken dikkat edin", expanded=False):
    st.markdown("""
- **Optimum düzen nasıl hesaplanır?** Uygulama her (kolon × satır) kombinasyonu
  için kart genişliğini/yüksekliğini bulur; okunabilirlik kısıtını (min. QR boyutu),
  kart en-boy oranını (0,50–1,15) ve min. kart boyutunu (45 mm) sağlayanları
  listeler. Kart sayısına göre azalan sırada gösterilir.
- QR'ın çevresindeki beyaz boşluğa dokunmayın; kartı kesmeden önce kenarlardan
  en az 1 cm pay bırakın. **Bu uygulama standart 4 modül sessiz bölgeyi otomatik
  ekler.**
- Parlak laminasyon ışığı yansıtır. **Mat kağıt** ya da **mat laminasyon** seçin.
- Renkleri ters çevirmeyin (koyu zemin üstüne açık QR) — birçok telefon okuyamaz.
- Basmadan önce hem iPhone hem Android kamerasıyla, masa mesafesinden deneyin.
- IBAN kodu ödeme başlatmaz; telefon IBAN'ı metin olarak gösterir, müşteri
  kopyalayıp bankacılık uygulamasına yapıştırır.
- 300 DPI baskı için PNG indirip yazıcıya **"Gerçek boyut" (100%)** ile gönderin.
  "Sayfaya sığdır" seçeneği QR'ı küçültüp okunmaz hale getirebilir.
- **Okunabilirlik için minimum QR boyutları:** sade kod ≥ 2 cm, orta ≥ 2,5 cm,
  yoğun kod ≥ 3 cm. Uygulama her kartta ölçüyü gösterir.
""")

st.caption("Bu araç, kartları cihazınızda üretir; hiçbir veri sunucuya gitmez.")