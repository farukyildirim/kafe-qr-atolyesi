# ☕ Kafe QR Atölyesi

Kafe, restoran ve küçük işletmeler için baskıya hazır QR kartları üreten
Streamlit uygulaması. Menü, Wi-Fi, Google yorum, Instagram, IBAN ve WhatsApp
için yüksek okunabilirlikli kartlar hazırlar.

## Özellikler

- 6 QR türü: Menü, Wi-Fi, Google yorum, Instagram, IBAN, WhatsApp
- Çoklu kağıt boyutu (A3, A4, A5, A6, Letter, Legal, B5, 10×15, 13×18 cm)
- Her kağıt için **optimum düzen** otomatik hesaplanır
- Okunabilirlik kontrolü (modül boyutu, QR boyutu, yoğunluk)
- Aynı sayfada birden fazla kartı PNG olarak indirme
- IBAN kontrol basamağı, WhatsApp numara normalizasyonu
- Kart üzerindeki tüm veriler tarayıcıdan hiç çıkmaz

## Kurulum (yerel)

```bash
pip install -r requirements.txt
streamlit run app.py