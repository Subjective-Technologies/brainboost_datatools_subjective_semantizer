import os
import subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
from urllib.parse import urlparse
from urllib.parse import urlparse


class HTMLPage:

    #initial_url = "https://docs.python.org/3/tutorial/index.html"

    def __init__(self,initial_url) -> None:
        self.initial_url = initial_url
       
        parsed_url = urlparse(initial_url)
        self.domain = parsed_url.netloc


    def extract_raw(self):


        def is_valid_url(url):
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)

        def is_web_page(url):
            # Only allow specific web extensions
            web_extensions = ('.html', '.htm', '.php', '/')
            return url.endswith(web_extensions) or '?' in url

        def fetch_links(url, base_domain):
            try:
                response = requests.get(url)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                links = set()
                for a_tag in soup.find_all('a', href=True):
                    href = a_tag['href']
                    full_url = urljoin(url, href)
                    # Ensure the URL is valid, is a web page, and stays within the same domain
                    if is_valid_url(full_url) and is_web_page(full_url) and urlparse(full_url).netloc == base_domain:
                        links.add(full_url)
                return links
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                return set()

        def fetch_text_with_lynx(url):
            # Check content type before fetching with lynx
            try:
                head_response = requests.head(url, allow_redirects=True)
                if head_response.headers.get('Content-Type', '').startswith('text/html'):
                    result = subprocess.run(['lynx', '-dump', url], capture_output=True, text=True, check=True)
                    return result.stdout
                else:
                    print(f"Skipping non-HTML content: {url}")
                    return ""
            except (requests.RequestException, subprocess.CalledProcessError) as e:
                print(f"Error fetching text from {url}: {e}")
                return ""

        def sanitize_filename(filename):
            # Remove invalid characters for filenames
            return re.sub(r'[\\/*?:"<>|]', "_", filename)

        def save_intermediate_text(url, text, output_dir):
            parsed_url = urlparse(url)
            # Create a filename based on the URL path
            filename = f"{parsed_url.netloc}{parsed_url.path}".replace('/', '_').strip('_') + ".txt"
            filename = sanitize_filename(filename)
            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(text)
            return filepath
        
        
        initial_url = self.initial_url
        base_domain = urlparse(initial_url).netloc  # Extract the base domain of the initial URL

        if not is_valid_url(initial_url):
            print("Invalid URL. Please enter a valid URL.")
            return

        output_dir = "com_worktwins_data/books_html"
        os.makedirs(output_dir, exist_ok=True)

        visited = set()
        to_visit = {initial_url}
        all_text = ""

        while to_visit:
            current_url = to_visit.pop()
            if current_url in visited:
                continue
            visited.add(current_url)
            print(f"Processing: {current_url}")
            page_text = fetch_text_with_lynx(current_url)
            if page_text:
                all_text += page_text + "\n\n"
                intermediate_file = save_intermediate_text(current_url, page_text, output_dir)
                print(f"Saved intermediate text to {intermediate_file}")
            links = fetch_links(current_url, base_domain)
            to_visit.update(links - visited)

        combined_file = self.domain + '.txt'
        with open(combined_file, 'w', encoding='utf-8') as f:
            f.write(all_text)

        print(f"Combined text saved to {combined_file}")
        return all_text
