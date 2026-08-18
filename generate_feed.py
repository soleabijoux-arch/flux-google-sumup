import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import json

BASE_URL = "https://solea-breizh-bijoux.fr"

def extract_image_url(soup, product_url):
    """Extrait l'URL d'image la plus précise possible depuis la page produit SumUp."""
    
    # 1. Recherche dans les données JSON-LD (données structurées e-commerce)
    for script in soup.find_all('script', type='application/ld+json'):
        try:
            data = json.loads(script.string)
            if isinstance(data, dict):
                if 'image' in data and data['image']:
                    img = data['image']
                    return img[0] if isinstance(img, list) else img
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and 'image' in item and item['image']:
                        img = item['image']
                        return img[0] if isinstance(img, list) else img
        except Exception:
            pass

    # 2. Recherche dans la balise OpenGraph (og:image)
    og_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
    if og_img and og_img.get('content'):
        return og_img['content'].strip()

    # 3. Balayage des balises <img> et srcset dans le DOM
    for img in soup.find_all('img'):
        srcset = img.get('srcset', '')
        if srcset:
            sources = [s.strip().split(' ') for s in srcset.split(',') if s.strip()]
            if sources:
                best_src = sources[-1][0]
                if best_src and not best_src.startswith('data:'):
                    return best_src

        src = img.get('src') or img.get('data-src') or img.get('data-original') or ''
        if src and not src.startswith('data:') and any(k in src.lower() for k in ['product', 'item', 'media', 'images', 'uploads', 'assets', 'sumup']):
            return src

    return ""

def format_url(url):
    """Nettoie et formate proprement l'URL de l'image."""
    if not url:
        return ""
    if url.startswith('//'):
        return f"https:{url}"
    elif url.startswith('/'):
        return f"{BASE_URL}{url}"
    elif not url.startswith('http'):
        return f"{BASE_URL}/{url}"
    return url

def get_product_details(product_url, session, headers):
    try:
        resp = session.get(product_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return "", ""
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extraction Image & Description
        raw_image = extract_image_url(soup, product_url)
        image_url = format_url(raw_image)

        og_desc = soup.find('meta', property='og:description')
        desc = og_desc['content'].strip() if og_desc and og_desc.get('content') else ""

        return image_url, desc

    except Exception as e:
        print(f"⚠️ Erreur lors de la lecture de {product_url}: {e}")
        return "", ""

def generate_xml():
    print("➜ Analyse approfondie du catalogue Solea Breizh Bijoux...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
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

            # Lien produit
            link_tag = card if card.name == 'a' else card.find('a', href=True)
            prod_link = BASE_URL
            if link_tag and link_tag.get('href'):
                href = link_tag['href']
                prod_link = href if href.startswith('http') else f"{BASE_URL}{href}"

            # Extraction image et description
            img_url, hd_desc = "", ""
            if prod_link != BASE_URL:
                img_url, hd_desc = get_product_details(prod_link, session, headers)

            # Attribution couleur
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

            description = hd_desc or f"{title} - Création artisanale en acier inoxydable par Solea Breizh Bijoux."

            products.append({
                'id': f"bijou-{idx+1}",
                'title': title,
                'price': price_val,
                'link': prod_link,
                'image': img_url,
                'description': description,
                'color': color
            })

    except Exception as e:
        print(f"❌ Erreur lors du traitement du catalogue : {e}")

    print(f"✓ {len(products)} bijoux détectés.")

    # Flux XML RSS 2.0
    rss = ET.Element("rss", version="2.0", **{"xmlns:g": "http://base.google.com/ns/1.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = "Solea Breizh Bijoux"
    ET.SubElement(channel, "link").text = BASE_URL
    ET.SubElement(channel, "description").text = "Bijoux en acier inoxydable Solea Breizh Bijoux"

    for p in products:
        item = ET.SubElement(channel, "item")
        
        ET.SubElement(item, "g:id").text = p['id']
        ET.SubElement(item, "g:title").text = p['title']
        ET.SubElement(item, "g:description").text = p['description']
        ET.SubElement(item, "g:link").text = p['link']
        
        # Champ obligatoire de l'image
        if p['image']:
            ET.SubElement(item, "g:image_link").text = p['image']
            
        ET.SubElement(item, "g:price").text = f"{p['price']:.2f} EUR"
        ET.SubElement(item, "g:condition").text = "new"
        ET.SubElement(item, "g:availability").text = "in_stock"
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"
        ET.SubElement(item, "g:identifier_exists").text = "no"

        # Champs obligatoires de conformité Google
        ET.SubElement(item, "g:shipping_weight").text = "0.1 kg"
        ET.SubElement(item, "g:age_group").text = "adult"
        ET.SubElement(item, "g:gender").text = "female"
        ET.SubElement(item, "g:color").text = p['color']

    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")

    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print("✓ Le fichier 'google-shopping.xml' a été mis à jour avec succès !")

if __name__ == "__main__":
    generate_xml()
