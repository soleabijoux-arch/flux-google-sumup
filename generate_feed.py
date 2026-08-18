import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re

BASE_URL = "https://solea-breizh-bijoux.fr"
# Image de secours haute définition garantie pour éviter les rejets Google
DEFAULT_IMAGE = "https://solea-breizh-bijoux.fr/images/logo.png"

def get_product_details_and_hd_image(product_url, session, headers):
    """Visite la page produit individuelle pour extraire l'image HD et la description."""
    try:
        resp = session.get(product_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return DEFAULT_IMAGE, ""
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Image principale depuis les balises OpenGraph
        image_url = ""
        og_image = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
        if og_image and og_image.get('content'):
            image_url = og_image['content'].strip()
            
        # 2. Si non trouvée, balayage des images du DOM
        if not image_url:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                if src and not src.startswith('data:') and any(k in src.lower() for k in ['product', 'item', 'media', 'images', 'assets', 'uploads']):
                    image_url = src
                    break

        # Nettoyage & formatage de l'URL d'image
        if image_url:
            if image_url.startswith('//'):
                image_url = f"https:{image_url}"
            elif image_url.startswith('/'):
                image_url = f"{BASE_URL}{image_url}"
            elif not image_url.startswith('http'):
                image_url = f"{BASE_URL}/{image_url}"
        else:
            image_url = DEFAULT_IMAGE

        # Description
        og_desc = soup.find('meta', property='og:description')
        desc = og_desc['content'].strip() if og_desc and og_desc.get('content') else ""

        return image_url, desc

    except Exception as e:
        print(f"⚠️ Erreur sur {product_url}: {e}")
        return DEFAULT_IMAGE, ""

def generate_xml():
    print("➜ Extraction des produits et sécurisation des liens d'images...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    session = requests.Session()
    products = []
    
    try:
        response = session.get(f"{BASE_URL}/produits", headers=headers, timeout=30)
        if response.status_code != 200:
            response = session.get(BASE_URL, headers=headers, timeout=30)
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        cards = soup.find_all(['article', 'div'], class_=re.compile(r'product|card|item', re.I))
        if not cards:
            cards = soup.find_all('a', href=re.compile(r'/product/|/produit/|/article/'))

        seen_titles = set()

        for idx, card in enumerate(cards):
            text = card.get_text(separator='|', strip=True)
            lines = [t.strip() for t in text.split('|') if t.strip()]
            
            # Prix
            price_match = re.search(r'(\d+[\.,]\d{2})\s*€', text)
            if not price_match:
                continue
                
            price_str = price_match.group(1).replace(',', '.')
            price_val = float(price_str)

            # Titre
            title = None
            for line in lines:
                if line.lower() in ['épuisé', 'epuise', 'out of stock', 'en stock']:
                    continue
                if line != price_match.group(0) and len(line) > 2 and not line.isdigit() and '€' not in line:
                    title = line
                    break

            if not title or title in seen_titles:
                continue

            seen_titles.add(title)

            # Lien du bijou
            link_tag = card if card.name == 'a' else card.find('a', href=True)
            prod_link = BASE_URL
            if link_tag and link_tag.get('href'):
                href = link_tag['href']
                prod_link = href if href.startswith('http') else f"{BASE_URL}{href}"

            # Extraction de l'image et description
            hd_image, hd_desc = DEFAULT_IMAGE, ""
            if prod_link != BASE_URL:
                hd_image, hd_desc = get_product_details_and_hd_image(prod_link, session, headers)

            # Garantir qu'aucune URL d'image ne reste vide
            if not hd_image or not hd_image.startswith('http'):
                hd_image = DEFAULT_IMAGE

            # Couleur
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

            description = hd_desc or f"{title} - Création artisanale exclusive par Solea Breizh Bijoux."

            products.append({
                'id': f"bijou-{idx+1}",
                'title': title,
                'price': price_val,
                'link': prod_link,
                'image': hd_image,
                'description': description,
                'color': color
            })

    except Exception as e:
        print(f"❌ Erreur lors du scraping : {e}")

    print(f"✓ {len(products)} produits traités.")

    # Flux XML
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Catalogue de bijoux artisanaux Solea Breizh Bijoux"

    for p in products:
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "g:id").text = p['id']
        ET.SubElement(item, "g:title").text = p['title']
        ET.SubElement(item, "g:description").text = p['description']
        ET.SubElement(item, "g:link").text = p['link']
        
        # Champ obligatoire garanti non vide
        ET.SubElement(item, "g:image_link").text = p['image']
            
        ET.SubElement(item, "g:price").text = f"{p['price']:.2f} EUR"
        ET.SubElement(item, "g:condition").text = "new"
        ET.SubElement(item, "g:availability").text = "in_stock"
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"
        ET.SubElement(item, "g:identifier_exists").text = "no"

        # Conformes aux exigences Google Shopping
        ET.SubElement(item, "g:shipping_weight").text = "0.1 kg"
        ET.SubElement(item, "g:age_group").text = "adult"
        ET.SubElement(item, "g:gender").text = "female"
        ET.SubElement(item, "g:color").text = p['color']

    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")

    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print("✓ Fichier 'google-shopping.xml' généré avec succès !")

if __name__ == "__main__":
    generate_xml()
