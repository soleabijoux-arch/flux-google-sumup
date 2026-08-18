import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

MERCHANT_CODE = "M7QFQAMW"
BASE_URL = "https://solea-breizh-bijoux.fr"
API_URL = f"https://store.sumup.com/api/v1/merchants/{MERCHANT_CODE}/products"

def get_image_url(p):
    """Extrait une URL d'image valide et complète pour Google."""
    images = p.get("images", []) or p.get("media", [])
    if not images:
        return f"{BASE_URL}/images/logo.png" # Image de secours si aucune image trouvée
        
    img_data = images[0]
    url = ""
    if isinstance(img_data, dict):
        url = img_data.get("url") or img_data.get("src") or img_data.get("path", "")
    elif isinstance(img_data, str):
        url = img_data

    if not url:
        return f"{BASE_URL}/images/logo.png"

    if url.startswith("http://") or url.startswith("https://"):
        return url
    elif url.startswith("//"):
        return f"https:{url}"
    elif url.startswith("/"):
        return f"{BASE_URL}{url}"
    else:
        return f"https://images.sumup.com/{url}"

def generate_xml():
    print("➜ Interrogation de l'API SumUp...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json',
        'Referer': f"{BASE_URL}/"
    }

    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        print(f"Code HTTP SumUp: {response.status_code}")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Erreur lors de la requête API : {e}")
        data = []

    # Extraction de la liste des produits
    if isinstance(data, list):
        products = data
    elif isinstance(data, dict):
        products = data.get('products') or data.get('items') or data.get('data') or []
    else:
        products = []

    print(f"✓ {len(products)} produits bruts extraits de l'API.")

    # Balises XML racine Google Shopping
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Boutique de bijoux artisanaux Solea Breizh Bijoux"

    valid_count = 0

    for idx, p in enumerate(products):
        if not isinstance(p, dict):
            continue

        name = (p.get("name") or p.get("title") or "").strip()
        if not name:
            continue

        item = ET.SubElement(channel, "item")

        # 1. ID Produit (Obligatoire)
        prod_id = str(p.get("id") or p.get("sku") or p.get("code") or f"bijou-{idx+1}")
        ET.SubElement(item, "g:id").text = prod_id

        # 2. Titre (Obligatoire)
        ET.SubElement(item, "g:title").text = name

        # 3. Description (Obligatoire pour Google)
        desc = (p.get("description") or p.get("summary") or "").strip()
        if not desc or len(desc) < 5:
            desc = f"{name} - Magnifique bijou de la collection Solea Breizh Bijoux."
        ET.SubElement(item, "g:description").text = desc

        # 4. Lien vers la page du produit (Obligatoire)
        slug = p.get("slug") or p.get("url_key") or ""
        if slug:
            link = f"{BASE_URL}/product/{slug}" if not slug.startswith("http") else slug
        else:
            link = BASE_URL
        ET.SubElement(item, "g:link").text = link

        # 5. Image (Obligatoire)
        ET.SubElement(item, "g:image_link").text = get_image_url(p)

        # 6. Prix (Obligatoire - Ex: "14.00 EUR")
        price_raw = p.get("price") or p.get("unit_price") or 0
        try:
            price_val = float(price_raw)
        except (ValueError, TypeError):
            price_val = 0.0
            
        ET.SubElement(item, "g:price").text = f"{price_val:.2f} EUR"

        # 7. Attributs obligatoires de conformité Google Shopping
        ET.SubElement(item, "g:condition").text = "new"
        
        in_stock = p.get("in_stock", True)
        ET.SubElement(item, "g:availability").text = "in_stock" if in_stock else "out_of_stock"

        # Marque & Codes d'identification (GTIN/MPN non requis pour l'artisanat)
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"
        ET.SubElement(item, "g:identifier_exists").text = "no"

        valid_count += 1

    # Formatage XML final
    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")

    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"✓ Terminé : {valid_count} produits intégrés au fichier 'google-shopping.xml'.")

if __name__ == "__main__":
    generate_xml()
