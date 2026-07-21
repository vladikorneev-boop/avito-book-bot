import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import re

class AvitoParser:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
        }
    
    def search_books(self, query="детские книги", city="", min_price=0, max_price=1000, limit=20):
        books = []
        
        if not city:
            base_url = "https://www.avito.ru/moskva"
            is_russia_wide = True
            print(f"🔍 Ищу по всей России: {query}")
        else:
            base_url = f"https://www.avito.ru/{city}"
            is_russia_wide = False
            print(f"🔍 Ищу в {city}: {query}")
        
        params = {
            'q': query,
            'p': 1,
        }
        
        if min_price > 0:
            params['pm'] = min_price
        if max_price > 0:
            params['prices'] = max_price
        
        if is_russia_wide:
            params['s'] = 1
        
        url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items() if v])}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code == 200:
                books = self._parse_books(response.text, "вся Россия" if is_russia_wide else city)
                
                page = 2
                while len(books) < limit:
                    params['p'] = page
                    url = f"{base_url}?{'&'.join([f'{k}={v}' for k, v in params.items() if v])}"
                    response = requests.get(url, headers=self.headers, timeout=30)
                    if response.status_code == 200:
                        new_books = self._parse_books(response.text, "вся Россия" if is_russia_wide else city)
                        if not new_books:
                            break
                        books.extend(new_books)
                        page += 1
                        time.sleep(1)
                    else:
                        break
        except Exception as e:
            print(f"❌ Ошибка: {e}")
        
        print(f"📚 Найдено: {len(books)}")
        return books[:limit]
    
    def _parse_books(self, html, city_display):
        # Используем встроенный парсер (не требует lxml)
        soup = BeautifulSoup(html, 'html.parser')
        books = []
        
        items = soup.find_all('div', {'data-marker': 'item'})
        
        for item in items:
            try:
                item_id = item.get('data-item-id')
                if not item_id:
                    continue
                
                title_elem = item.find('h3', {'itemprop': 'name'})
                if title_elem:
                    title = title_elem.text.strip()
                else:
                    title = "Без названия"
                
                price_elem = item.find('span', {'itemprop': 'price'})
                price = 0
                if price_elem:
                    price_text = price_elem.get('content', '0')
                    try:
                        price = float(price_text) if price_text else 0
                    except:
                        price = 0
                
                link_elem = item.find('a', {'data-marker': 'item-title'})
                url = ""
                if link_elem:
                    href = link_elem.get('href')
                    if href:
                        url = f"https://www.avito.ru{href}" if href.startswith('/') else href
                
                desc_elem = item.find('div', {'class': re.compile('iva-item-text-')})
                description = desc_elem.text.strip() if desc_elem else ""
                
                img_elem = item.find('img', {'class': 'photo-slider-image'})
                image_url = ""
                if img_elem:
                    image_url = img_elem.get('src', '')
                    if image_url and not image_url.startswith('http'):
                        image_url = f"https:{image_url}"
                
                book = {
                    'avito_id': item_id,
                    'title': title[:200],
                    'price': price,
                    'description': description[:500],
                    'url': url,
                    'image_url': image_url,
                    'city': city_display,
                    'published_at': datetime.now(),
                    'found_at': datetime.now(),
                    'is_notified': False
                }
                
                books.append(book)
                
            except Exception as e:
                continue
        
        return books
