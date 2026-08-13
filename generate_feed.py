import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom

MERCHANT_CODE = "M7QFQAMW"
BASE_URL = "https://solea-breizh-bijoux.fr"
API_URL = f"https://store.sumup.com/api/v1/merchants/{MERCHANT_CODE}/products"

def format_image_url(img_data):
    """S'assure que l'URL de l'image est complète et valide pour Google."""
    if not img_data:
        return ""
    
    url = ""
    if isinstance(img_data, dict):
        url = img_data.get("url", "") or img_data.get("src", "")
    elif isinstance(img_data, str):
        url = img_data

    if url and not url.startswith("http"):
        if url.startswith("//"):
            url = f"https:{url}"
        elif url.startswith("/"):
            url = f"{BASE_URL}{url}"
        else:
            url = f"https://images.sumup.com/{url}"
            
    return url

def generate_xml():
    print("➜ Récupération des données SumUp...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Origin': BASE_URL,
        'Referer': f"{BASE_URL}/"
    }

    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Erreur lors de la requête API : {e}")
        data = []

    products = data if isinstance(data, list) else data.get('products', data.get('items', []))
    print(f"✓ {len(products)} produits trouvés dans l'API SumUp.")

    # Structure du flux RSS Google Shopping
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Catalogue complet de bijoux artisanaux Solea Breizh Bijoux"

    count = 0
    for idx, p in enumerate(products):
        name = p.get("name", "").strip()
        if not name:
            continue

        item = ET.SubElement(channel, "item")
        
        # 1. ID Unique (Requis)
        prod_id = str(p.get("id") or p.get("sku") or f"bijou-{idx+1}")
        ET.SubElement(item, "g:id").text = prod_id
        
        # 2. Titre (Requis)
        ET.SubElement(item, "g:title").text = name
        
        # 3. Description (Requis par Google)
        desc = p.get("description", "").strip() or f"{name} - Bijou artisanal par Solea Breizh Bijoux."
        ET.SubElement(item, "g:description").text = desc
        
        # 4. Lien Produit (Requis)
        slug = p.get("slug", "")
        product_link = f"{BASE_URL}/product/{slug}" if slug else BASE_URL
        ET.SubElement(item, "g:link").text = product_link
        
        # 5. Lien Image (Requis)
        images = p.get("images", [])
        image_url = format_image_url(images[0]) if images else ""
        if image_url:
            ET.SubElement(item, "g:image_link").text = image_url
            
        # 6. Prix (Requis - Format: "14.00 EUR")
        price = p.get("price", 0)
        try:
            price_val = float(price)
        except (ValueError, TypeError):
            price_val = 0.0
            
        ET.SubElement(item, "g:price").text = f"{price_val:.2f} EUR"
        
        # 7. Champs obligatoires Google Shopping
        ET.SubElement(item, "g:condition").text = "new"
        
        # Disponibilité
        in_stock = p.get("in_stock", True)
        ET.SubElement(item, "g:availability").text = "in_stock" if in_stock else "out_of_stock"
        
        # Marque & Identifiants uniques
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"
        ET.SubElement(item, "g:identifier_exists").text = "no"

        count += 1

    # Sauvegarde au format XML propre
    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")
    
    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    print(f" Success ! {count} produits ont été formatés et enregistrés dans 'google-shopping.xml'.")

if __name__ == "__main__":
    generate_xml()
