import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

BASE_URL = "https://solea-breizh-bijoux.fr"

def generate_xml():
    print("➜ Extraction du catalogue depuis la boutique en ligne...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    products = []
    
    try:
        response = requests.get(f"{BASE_URL}/produits", headers=headers, timeout=30)
        if response.status_code != 200:
            response = requests.get(BASE_URL, headers=headers, timeout=30)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        cards = soup.find_all(['article', 'div'], class_=re.compile(r'product|card|item', re.I))
        if not cards:
            cards = soup.find_all('a', href=re.compile(r'/product/|/produit/'))

        seen_titles = set()

        for idx, card in enumerate(cards):
            text = card.get_text(separator='|', strip=True)
            lines = [t.strip() for t in text.split('|') if t.strip()]
            
            # Extraction du prix
            price_match = re.search(r'(\d+[\.,]\d{2})\s*€', text)
            if not price_match:
                continue
                
            price_str = price_match.group(1).replace(',', '.')
            price_val = float(price_str)

            # Identification du titre
            title = None
            for line in lines:
                # Filtrer les mots de statut comme "Épuisé" ou les prix
                if line.lower() in ['épuisé', 'epuise', 'out of stock', 'en stock']:
                    continue
                if line != price_match.group(0) and len(line) > 2 and not line.isdigit() and '€' not in line:
                    title = line
                    break

            if not title or title in seen_titles:
                continue

            seen_titles.add(title)

            # Link
            link_tag = card if card.name == 'a' else card.find('a', href=True)
            prod_link = BASE_URL
            if link_tag and link_tag.get('href'):
                href = link_tag['href']
                prod_link = href if href.startswith('http') else f"{BASE_URL}{href}"

            # Extraction d'Image HD
            img_tag = card.find('img')
            img_link = ""
            if img_tag:
                src = img_tag.get('src') or img_tag.get('data-src') or img_tag.get('srcset', '').split(' ')[0]
                if src:
                    if src.startswith('http'):
                        img_link = src
                    elif src.startswith('//'):
                        img_link = f"https:{src}"
                    else:
                        img_link = f"{BASE_URL}{src}"

            # Détection automatique de la couleur
            title_lower = title.lower()
            color = "Doré"
            if "argent" in title_lower:
                color = "Argenté"
            elif "bleu" in title_lower:
                color = "Bleu"
            elif "rose" in title_lower:
                color = "Rose"
            elif "vert" in title_lower:
                color = "Vert"
            elif "noir" in title_lower:
                color = "Noir"

            products.append({
                'id': f"bijou-{idx+1}",
                'title': title,
                'price': price_val,
                'link': prod_link,
                'image': img_link,
                'color': color
            })

    except Exception as e:
        print(f"❌ Erreur lors du scraping du site : {e}")

    print(f"✓ {len(products)} produits extraits de la boutique.")

    # Construction du flux XML Google Shopping
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Bijoux artisanaux Solea Breizh Bijoux"

    for p in products:
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "g:id").text = p['id']
        ET.SubElement(item, "g:title").text = p['title']
        ET.SubElement(item, "g:description").text = f"{p['title']} - Bijou artisanal unique créé par Solea Breizh Bijoux."
        ET.SubElement(item, "g:link").text = p['link']
        if p['image']:
            ET.SubElement(item, "g:image_link").text = p['image']
        ET.SubElement(item, "g:price").text = f"{p['price']:.2f} EUR"
        ET.SubElement(item, "g:condition").text = "new"
        ET.SubElement(item, "g:availability").text = "in_stock"
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"
        ET.SubElement(item, "g:identifier_exists").text = "no"

        # Attributs requis pour corriger le blocage Google
        ET.SubElement(item, "g:shipping_weight").text = "0.1 kg"
        ET.SubElement(item, "g:age_group").text = "adult"
        ET.SubElement(item, "g:gender").text = "female"
        ET.SubElement(item, "g:color").text = p['color']

    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")

    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(" Fichier 'google-shopping.xml' mis à jour avec succès !")

if __name__ == "__main__":
    generate_xml()
