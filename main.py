from fastapi import FastAPI, UploadFile, File, Form
import uvicorn
import requests
import base64
import json
import urllib.parse

app = FastAPI()

API_KEY = "AIzaSyBAFos3YTfm_vXDRvf3cOgt-b7Af1onrQA"
MODEL_NAME = "gemini-2.5-flash"

def magaza_linkleri_olustur(urun_adi, cinsiyet, ulke_kodu="tr-tr"):
    market_links = []
    arama_sorgusu = f"{urun_adi} {cinsiyet}"
    safe_sorgu = urllib.parse.quote(arama_sorgusu)

    if "tr" in ulke_kodu:
        market_links.append({
            "magaza": "Trendyol",
            "link": f"https://www.trendyol.com/sr?q={safe_sorgu}"
        })
        market_links.append({
            "magaza": "Hepsiburada",
            "link": f"https://www.hepsiburada.com/ara?q={safe_sorgu}"
        })
        market_links.append({
            "magaza": "Amazon TR",
            "link": f"https://www.amazon.com.tr/s?k={safe_sorgu}"
        })
    else:
        market_links.append({
            "magaza": "Amazon",
            "link": f"https://www.amazon.com/s?k={safe_sorgu}"
        })
        market_links.append({
            "magaza": "eBay",
            "link": f"https://www.ebay.com/sch/i.html?_nkw={safe_sorgu}"
        })
        market_links.append({
            "magaza": "Walmart",
            "link": f"https://www.walmart.com/search?q={safe_sorgu}"
        })
        
    return market_links

@app.post("/analiz-et")
async def analiz_et(file: UploadFile = File(...), ulke: str = Form("tr-tr")):
    try:
        resim_verisi = await file.read()
        resim_base64 = base64.b64encode(resim_verisi).decode('utf-8')
        mime_type = file.content_type or "image/jpeg"

        is_tr = "tr" in ulke.lower()
        dil = "Türkçe" if is_tr else "İngilizce"
        
        prompt_text = f"""
        Sen uzman bir moda stilistisin.
        Görev 1: Resimdeki kişinin cinsiyetini veya kıyafetin hitap ettiği cinsiyeti belirle (Erkek/Kadın).
        Görev 2: {dil} dilinde stil önerisi ver.
        Görev 3: Kombin için gerekli ürünlerin listesini çıkar.
        
        KURAL: Ürün isimleri MARKASIZ ve NET olsun.
        Türkiye dışı ({ulke}) için ürün adlarını İNGİLİZCE ver.
        
        Cevabını SADECE şu JSON formatında ver:
        {{
            "cinsiyet": "Erkek" veya "Kadın" (Global ise "Men" veya "Women"),
            "yorum": "Stil önerisi metni buraya",
            "aranacak_urunler": ["Ürün 1", "Ürün 2", "Ürün 3"]
        }}
        """

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={API_KEY}"
        headers = {'Content-Type': 'application/json'}
        data = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {"inline_data": {"mime_type": mime_type, "data": resim_base64}}
                ]
            }],
            "generationConfig": {"response_mime_type": "application/json"}
        }

        response = requests.post(url, headers=headers, data=json.dumps(data))
        
        if response.status_code == 200:
            sonuc = response.json()
            try:
                metin_json = sonuc['candidates'][0]['content']['parts'][0]['text']
                analiz_verisi = json.loads(metin_json)
            except:
                return {"hata": "Veri işlenemedi", "detay": str(sonuc)}
            
            yorum = analiz_verisi.get("yorum", "Yorum alınamadı.")
            cinsiyet = analiz_verisi.get("cinsiyet", "")
            aranacaklar = analiz_verisi.get("aranacak_urunler", [])

            alisveris_onerileri = {}
            for urun in aranacaklar:
                magaza_linkleri = magaza_linkleri_olustur(urun, cinsiyet, ulke_kodu=ulke)
                alisveris_onerileri[urun] = magaza_linkleri

            return {
                "durum": "Başarılı",
                "bolge": ulke,
                "tespit_edilen_cinsiyet": cinsiyet,
                "stilist_yorumu": yorum,
                "onerilen_kombinler": alisveris_onerileri
            }
        else:
            return {"hata": f"API Hatası: {response.text}"}

    except Exception as e:
        return {"hata": f"Sunucu Hatası: {str(e)}"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8017)