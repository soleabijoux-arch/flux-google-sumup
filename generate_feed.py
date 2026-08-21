import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from xml.dom import minidom
import re
import unicodedata

BASE_URL = "https://solea-breizh-bijoux.fr"

CATEGORIES = [
    "/catégorie/bagues",
    "/catégorie/boucles-d-oreilles",
    "/catégorie/bracelets",
    "/catégorie/colliers",
    "/catégorie/joncs",
    "/catégorie/sautoirs",
    "/catégorie/accessoires",
    "/produits"
]

def slugify(value):
    """Transforme un titre en slug d'URL SumUp valide (ex: "Boucles d’oreilles Eve" -> "boucles-doreilles-eve")"""
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('utf-8')
    value = value.replace("'", "").replace("’", "")
    value = re.sub(r'[^\w\s-]', '', value.lower())
    return re.sub(r'[-\s]+', '-', value).strip('-')

def upscale_image_url(url):
    """Force l'image SumUp en haute résolution (au moins 800x800)."""
    if not url:
        return ""
    # Remplacement des paramètres de taille/vignette dans l'URL d'image SumUp si présents
    url = re.sub(r'/_next/image\?url=', '', url)
    url = re.sub(r'&w=\d+&q=\d+', '', url)
    url = re.sub(r'\d+x\d+', '800x800', url)
    return url

def get_product_details(product_url, session, headers):
    """Récupère l'image HD et la description sur la fiche produit."""
    try:
        resp = session.get(product_url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return "", ""
            
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # 1. Image OpenGraph (souvent la version HD)
        image_url = ""
        og_img = soup.find('meta', property='og:image') or soup.find('meta', attrs={'name': 'og:image'})
        if og_img and og_img.get('content'):
            image_url = og_img['content'].strip()

        # 2. Image fallback dans le DOM
        if not image_url:
            for img in soup.find_all('img'):
                src = img.get('src') or img.get('data-src') or ''
                if src and 'images.sumup.com' in src:
                    image_url = src
                    break

        if image_url:
            if image_url.startswith('//'):
                image_url = f"https:{image_url}"
            elif image_url.startswith('/'):
                image_url = f"{BASE_URL}{image_url}"
            
            image_url = upscale_image_url(image_url)

        # Description OpenGraph
        og_desc = soup.find('meta', property='og:description')
        desc = og_desc['content'].strip() if og_desc and og_desc.get('content') else ""

        return image_url, desc

    except Exception:
        return "", ""

def generate_xml():
    print("➜ Extraction multi-catégories et optimisation des images HD...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)',
        'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7'
    }

    session = requests.Session()
    products = []
    seen_titles = set()
    
    urls_to_scrape = []
    for cat in CATEGORIES:
        urls_to_scrape.append(f"{BASE_URL}{cat}")
        for p in range(1, 7):
            urls_to_scrape.append(f"{BASE_URL}{cat}?page={p}")

    for target_url in urls_to_scrape:
        try:
            response = session.get(target_url, headers=headers, timeout=15)
            if response.status_code != 200:
                continue
                
            soup = BeautifulSoup(response.text, 'html.parser')
            
            cards = soup.find_all(['article', 'div'], class_=re.compile(r'product|card|item', re.I))
            if not cards:
                cards = soup.find_all('a', href=re.compile(r'/product/|/produit/|/article/'))

            for card in cards:
                text = card.get_text(separator='|', strip=True)
                lines = [t.strip() for t in text.split('|') if t.strip()]
                
                # Détection du prix
                price_match = re.search(r'(\d+[\.,]\d{2})\s*€', text)
                if not price_match:
                    continue
                    
                price_str = price_match.group(1).replace(',', '.')
                price_val = float(price_str)

                # Détection du titre du bijou
                title = None
                for line in lines:
                    if line.lower() in ['épuisé', 'epuise', 'out of stock', 'en stock', 'autres variantes disponibles']:
                        continue
                    if line != price_match.group(0) and len(line) > 2 and not line.isdigit() and '€' not in line:
                        title = line
                        break

                if not title or title in seen_titles:
                    continue

                seen_titles.add(title)

                # Extraction ou reconstruction du lien produit
                link_tag = card if card.name == 'a' else card.find('a', href=True)
                prod_link = ""
                if link_tag and link_tag.get('href') and any(k in link_tag['href'] for k in ['/product/', '/article/']):
                    href = link_tag['href']
                    prod_link = href if href.startswith('http') else f"{BASE_URL}{href}"
                else:
                    prod_link = f"{BASE_URL}/product/{slugify(title)}"

                # Récupération image HD et description
                img_url, hd_desc = get_product_details(prod_link, session, headers)

                if not img_url:
                    alt_link = f"{BASE_URL}/article/{slugify(title)}"
                    img_url, hd_desc = get_product_details(alt_link, session, headers)
                    if img_url:
                        prod_link = alt_link

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

                description = hd_desc or f"{title} - Création artisanale en acier inoxydable par Solea Breizh Bijoux."

                products.append({
                    'id': f"bijou-{len(products)+1}",
                    'title': title,
                    'price': price_val,
                    'link': prod_link,
                    'image': img_url,
                    'description': description,
                    'color': color
                })

        except Exception:
            continue

    print(f"✓ {len(products)} produits extraits et optimisés !")

    # Génération XML
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
        
        if p['image']:
            ET.SubElement(item, "g:image_link").text = p['image']
            
        ET.SubElement(item, "g:price").text = f"{p['price']:.2f} EUR"
        ET.SubElement(item, "g:condition").text = "new"
        ET.SubElement(item, "g:availability").text = "in_stock"
        ET.SubElement(item, "g:brand").text = "Solea Breizh Bijoux"
        ET.SubElement(item, "g:identifier_exists").text = "no"

        ET.SubElement(item, "g:shipping_weight").text = "0.1 kg"
        ET.SubElement(item, "g:age_group").text = "adult"
        ET.SubElement(item, "g:gender").text = "female"
        ET.SubElement(item, "g:color").text = p['color']

    xml_str = minidom.parseString(ET.tostring(rss, encoding='utf-8')).toprettyxml(indent="  ")

    with open("google-shopping.xml", "w", encoding="utf-8") as f:
        f.write(xml_str)

    print("✓ Fichier 'google-shopping.xml' régénéré !")

if __name__ == "__main__":
    generate_xml()
