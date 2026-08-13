import urllib.request
import json
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Config boutique SumUp
MERCHANT_CODE = "M7QFQAMW"
BASE_URL = "https://solea-breizh-bijoux.fr"
API_URL = f"https://store.sumup.com/api/v1/merchants/{MERCHANT_CODE}/products"

def generate_xml():
    print("➜ Récupération des données SumUp...")
    req = urllib.request.Request(
        API_URL, 
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
            'Accept': 'application/json',
            'Referer': BASE_URL
        }
    )

    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"Erreur lors de la requête API : {e}")
        return

    products = data if isinstance(data, list) else data.get('products', data.get('items', []))
    print(f"✓ {len(products)} produits trouvés.")

    # Création du XML Google Shopping
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux Catalog"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Flux automatique des produits Solea Breizh Bijoux"

    for p in products:
        item = ET.SubElement(channel, "item")
        
        # ID & Titre
        ET.SubElement(item, "g:id").text = str(p.get("id", p.get("sku", "")))
        ET.SubElement(item, "g:title").text = p.get("name", "Bijou Solea Breizh")
        ET.SubElement(item, "g:description").text = p.get("description", p.get("name", "Bijou artisanal"))
        
        # URL du produit
        slug = p.get("slug", "")
        product_link = f"{BASE_URL}/product/{slug}" if slug else BASE_URL
        ET.SubElement(item, "g:link").text = product_link
        
        # Image
        images = p.get("images", [])
        image_url = images[0].get("url") if images and isinstance(images[0], dict) else ""
        if image_url:
            ET.SubElement(item, "g:image_link").text = image_url
            
        # Prix (Format : "14.00 EUR")
        price = p.get("price", 0)
        ET.SubElement(item, "g:price").text = f"{price:.2f} EUR"
        
        # Attributs requis par Google
        ET.SubElement(item, "g:condition").text = "new"
        ET.SubElement(item, "g:availability").text = "in_stock" if p.get("in_stock", True) else "out_of_stock"
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"

    # Formatage propre avec indentation
    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")
    
    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    print(" Fichier 'google-shopping.xml' généré avec succès !")

if __name__ == "__main__":
    generate_xml()
