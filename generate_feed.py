import requests
import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys

MERCHANT_CODE = "M7QFQAMW"
BASE_URL = "https://solea-breizh-bijoux.fr"
API_URL = f"https://store.sumup.com/api/v1/merchants/{MERCHANT_CODE}/products"

def generate_xml():
    print("➜ Récupération des données SumUp...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Origin': BASE_URL,
        'Referer': f"{BASE_URL}/"
    }

    try:
        response = requests.get(API_URL, headers=headers, timeout=30)
        print(f"Statut HTTP : {response.status_code}")
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print(f"❌ Erreur lors de la requête API : {e}")
        # On crée un XML minimaliste de secours pour éviter que Git plante
        data = []

    products = data if isinstance(data, list) else data.get('products', data.get('items', []))
    print(f"✓ {len(products)} produits trouvés.")

    # Structure XML Google Shopping
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux Catalog"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Flux automatique des produits Solea Breizh Bijoux"

    for p in products:
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "g:id").text = str(p.get("id", p.get("sku", "")))
        ET.SubElement(item, "g:title").text = p.get("name", "Bijou Solea Breizh")
        ET.SubElement(item, "g:description").text = p.get("description", p.get("name", "Bijou artisanal"))
        
        slug = p.get("slug", "")
        product_link = f"{BASE_URL}/product/{slug}" if slug else BASE_URL
        ET.SubElement(item, "g:link").text = product_link
        
        images = p.get("images", [])
        image_url = ""
        if images and isinstance(images, list):
            if isinstance(images[0], dict):
                image_url = images[0].get("url", "")
            elif isinstance(images[0], str):
                image_url = images[0]
                
        if image_url:
            ET.SubElement(item, "g:image_link").text = image_url
            
        price = p.get("price", 0)
        if isinstance(price, (int, float)):
            ET.SubElement(item, "g:price").text = f"{price:.2f} EUR"
        else:
            ET.SubElement(item, "g:price").text = "0.00 EUR"
        
        ET.SubElement(item, "g:condition").text = "new"
        ET.SubElement(item, "g:availability").text = "in_stock" if p.get("in_stock", True) else "out_of_stock"
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"

    # Enregistrement du fichier
    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")
    
    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)
        
    print(" Fichier 'google-shopping.xml' généré avec succès !")

if __name__ == "__main__":
    generate_xml()
    
