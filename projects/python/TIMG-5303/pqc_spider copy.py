import os
import re
import time
import random
import argparse
import urllib.parse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup
import tqdm

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("scraper.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class WebScraper:
    def __init__(self, output_dir, delay_min=1, delay_max=3, max_pages_per_domain=100):
        self.output_dir = output_dir
        self.delay_min = delay_min
        self.delay_max = delay_max
        self.max_pages_per_domain = max_pages_per_domain
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        self.visited_urls = set()
        self.robot_parsers = {}
        self.domain_counters = {}

    def get_robot_parser(self, base_url):
        """Get or create a robot parser for the given base URL."""
        domain = urllib.parse.urlparse(base_url).netloc
        if domain not in self.robot_parsers:
            robot_url = urllib.parse.urljoin(base_url, "/robots.txt")
            parser = RobotFileParser()
            parser.set_url(robot_url)
            try:
                parser.read()
                logger.info(f"Read robots.txt from {robot_url}")
            except Exception as e:
                logger.warning(f"Failed to parse robots.txt from {robot_url}: {e}")
            self.robot_parsers[domain] = parser
        return self.robot_parsers[domain]

    def can_fetch(self, url):
        """Check if the URL can be fetched according to robots.txt."""
        try:
            parser = self.get_robot_parser(url)
            can_fetch = parser.can_fetch(self.headers['User-Agent'], url)
            return can_fetch
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            # Default to True if we can't check robots.txt
            return True

    def normalize_url(self, url, base_url):
        """Normalize URL by resolving relative URLs and removing fragments."""
        url = urllib.parse.urljoin(base_url, url)
        parsed = urllib.parse.urlparse(url)
        # Remove fragments
        normalized = urllib.parse.urlunparse((
            parsed.scheme, parsed.netloc, parsed.path, 
            parsed.params, parsed.query, ''
        ))
        return normalized

    def is_same_domain(self, url, base_url):
        """Check if URL belongs to the same domain as the base URL."""
        url_domain = urllib.parse.urlparse(url).netloc
        base_domain = urllib.parse.urlparse(base_url).netloc
        
        # Extract the main domain without subdomains for comparison
        def get_main_domain(domain):
            parts = domain.split('.')
            if len(parts) > 2:
                # Handle domains like co.uk, com.au
                if parts[-2] in ['co', 'com', 'org', 'gov', 'edu'] and len(parts[-1]) == 2:
                    return '.'.join(parts[-3:])
                return '.'.join(parts[-2:])
            return domain
        
        url_main = get_main_domain(url_domain)
        base_main = get_main_domain(base_domain)
        
        return url_main == base_main

    def should_follow_url(self, url, base_url):
        """Determine if a URL should be followed during crawling."""
        # Skip if already visited
        if url in self.visited_urls:
            return False
            
        # Check if URL is from the same domain
        if not self.is_same_domain(url, base_url):
            return False
            
        # Skip URLs with file extensions to avoid non-HTML content
        if re.search(r'\.(pdf|jpg|jpeg|png|gif|svg|css|js|ico|xml|zip|gz|tar|mp4|mp3|avi|mov)$', url, re.IGNORECASE):
            return False
            
        # Check robots.txt
        if not self.can_fetch(url):
            logger.info(f"Skipping {url} (disallowed by robots.txt)")
            return False
            
        # Check domain page limit
        domain = urllib.parse.urlparse(url).netloc
        if domain in self.domain_counters and self.domain_counters[domain] >= self.max_pages_per_domain:
            logger.info(f"Skipping {url} (reached max pages for domain {domain})")
            return False
            
        return True

    def extract_text(self, html):
        """Extract clean text content from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style", "header", "footer", "nav"]):
            script.extract()
            
        # Get text and clean it
        text = soup.get_text(separator=' ')
        
        # Remove extra whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return text

    def extract_links(self, html, base_url):
        """Extract and normalize links from HTML."""
        soup = BeautifulSoup(html, 'html.parser')
        links = []
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Normalize URL
            normalized_url = self.normalize_url(href, base_url)
            links.append(normalized_url)
            
        return links

    def fetch_url(self, url):
        """Fetch content from a URL with error handling."""
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()  # Raise exception for HTTP errors
            return response.text
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def save_content(self, url, text):
        """Save the extracted text to a file."""
        if not text or len(text.strip()) < 100:  # Skip if text is too short
            return
            
        domain = urllib.parse.urlparse(url).netloc
        path = urllib.parse.urlparse(url).path
        
        # Create a filename based on the URL
        if path == "" or path == "/":
            filename = f"{domain}_index.txt"
        else:
            # Replace path separators and query parameters with underscores
            safe_path = re.sub(r'[^\w]', '_', path)
            filename = f"{domain}{safe_path}.txt"
            
        # Limit filename length
        if len(filename) > 200:
            filename = filename[:190] + "..." + filename[-7:]
            
        file_path = os.path.join(self.output_dir, filename)
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                # Add URL as metadata at the top of the file
                f.write(f"Source URL: {url}\n")
                f.write(f"Scraped on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("-" * 80 + "\n\n")
                f.write(text)
            logger.info(f"Saved content to {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save content from {url} to {file_path}: {e}")
            return None

    def crawl(self, start_url):
        """Crawl a website starting from the given URL."""
        base_url = start_url
        domain = urllib.parse.urlparse(base_url).netloc
        self.domain_counters[domain] = 0
        
        # Queue of URLs to process
        queue = [start_url]
        
        logger.info(f"Starting crawl of {base_url}")
        
        with tqdm.tqdm(total=self.max_pages_per_domain, desc=f"Crawling {domain}") as pbar:
            while queue and self.domain_counters[domain] < self.max_pages_per_domain:
                # Get next URL to process
                url = queue.pop(0)
                
                # Skip if already visited
                if url in self.visited_urls:
                    continue
                    
                # Mark as visited
                self.visited_urls.add(url)
                
                # Respect crawl delay from robots.txt or use default
                robot_parser = self.get_robot_parser(base_url)
                crawl_delay = getattr(robot_parser, 'crawl_delay', None)
                if crawl_delay:
                    delay = crawl_delay('*')
                    if delay:
                        time.sleep(delay)
                    else:
                        time.sleep(random.uniform(self.delay_min, self.delay_max))
                else:
                    time.sleep(random.uniform(self.delay_min, self.delay_max))
                
                # Fetch URL
                logger.info(f"Fetching {url}")
                html = self.fetch_url(url)
                if not html:
                    continue
                
                # Extract and save text
                text = self.extract_text(html)
                saved_path = self.save_content(url, text)
                if saved_path:
                    self.domain_counters[domain] += 1
                    pbar.update(1)
                
                # Extract links and add to queue
                links = self.extract_links(html, url)
                for link in links:
                    if self.should_follow_url(link, base_url):
                        queue.append(link)
        
        logger.info(f"Completed crawl of {base_url}, processed {self.domain_counters[domain]} pages")
        return self.domain_counters[domain]

def main():
    parser = argparse.ArgumentParser(description='Web Scraper for PQC Companies')
    parser.add_argument('--output_dir', type=str, default='/Users/joehu/Downloads/pqc_companies_corpus',
                        help='Directory to save scraped content')
    parser.add_argument('--delay_min', type=float, default=2.0,
                        help='Minimum delay between requests (seconds)')
    parser.add_argument('--delay_max', type=float, default=5.0,
                        help='Maximum delay between requests (seconds)')
    parser.add_argument('--max_pages', type=int, default=50,
                        help='Maximum pages to scrape per domain')
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # List of PQC company URLs
    company_urls = [
         "https://www.isara.com/products/isara-radiate.html",
  "https://post-quantum.com/qse/index.html",
  "https://www.cryptonext-security.com/products",
  "https://kudelskisecurity.com/services/emerging-technology-security/quantum-security/",
  "https://www.fortanix.com/solutions/use-case/post-quantum-readiness",
  "https://www.cisco.com/c/en/us/about/trust-center/post-quantum-cryptography.html?dtid=osscdc000283#~overview",
  "https://www.evolutionq.com/products/basejumpqdn",
  "https://www.ibm.com/quantum/quantum-safe",
  "https://www.infosecglobal.com/solutions/pqc-migration",
  "https://www.magiqtech.com/solutions/network-security/",
  "https://www.qnulabs.com/post-quantum-cryptography",
  "https://www.qrypt.com/quantum-secure-messaging/",
  "https://www.qusecure.com/quprotect/",
  "https://quantumxc.com/pqc-migration/",
  "https://www.samsungsds.com/en/news/nccoe-pqc-project.html",
  "https://cpl.thalesgroup.com/encryption/post-quantum-crypto-agility",
  "https://utimaco.com/solutions/applications/post-quantum-cryptography",
  "https://crypto4a.com/pqc-migration-solutions/",
  "https://www.cryptoquantique.com/quarklink-v2/",
  "https://www.entrust.com/solutions/post-quantum-cryptography",
  "https://www.etas.com/ww/en/products-services/cybersecurity-services/escrypt-post-quantum-cryptography/",
  "https://www.secunet.com/en/products-consulting/sina",
  "https://www.infineon.com/",
  "https://kets-quantum.com/quantum-key-distribution/",
  "https://www.luxquanta.com/solutions",
  "https://www.microchip.com/en-us/products/fpgas-and-plds/ip-core-tools/xip6110b",
  "https://www.nxp.com/applications/technologies/security/post-quantum-cryptography:POST-QUANTUM-CRYPTOGRAPHY",
  "https://developers.cloudflare.com/ssl/post-quantum-cryptography/pqc-support/",
  "https://pqshield.com/products/",
  "https://www.quantum-info.com/English/product/",
  "https://www.genua.eu/it-security-solutions/firewall-vpn-appliance-genuscreen",
  "https://www.rambus.com/security/quantum-safe-cryptography/",
  "https://www.radware.com/documents/media-coverage/radware-fights-ai-driven-bots-with-ai-and-cryptography-en/",
  "https://arqit.uk/encryptionintelligence",
  "https://www.idquantique.com/quantum-safe-security/products/",
  "https://terraquantum.swiss/solutions/tqchem-enabling-technology",
  "https://xiphera.com/xiphera-develops-quantum-resilient-hardware-security-solutions-for-space/",
  "https://azure.microsoft.com/en-us/solutions/quantum-computing/",
  "https://cloud.google.com/blog/products/identity-security/how-google-is-preparing-for-a-post-quantum-world",
  "https://aws.amazon.com/security/post-quantum-cryptography/",
  "https://www.tencentcloud.com/document/product/1030/56197",
  "https://www.infosecglobal.com/solutions/enterprise",
  "https://www.ironcap.ca/",
  "https://www.btq.com/",
  "https://cryptalabs.com/",
  "https://www.nxmlabs.com/",
  "https://qanplatform.com/en",
  "https://www.quantumblockchains.io/",
  "https://www.theqrl.org/",
  "https://www.quantropi.com/",
  "https://qryptocyber.com/",
  "https://www.sandboxaq.com/",
  "https://www.securosys.com/",
  "https://cpl.thalesgroup.com/about-us/newsroom/thales-quantinuum-pqc-starter-kit-press-release",
  "https://surepassid.com/post-quantum-mfa/",
  "https://www.quintessencelabs.com/quantum-101",
  "https://eviden.com/solutions/digital-security/data-encryption/",
  "https://www.keyfactor.com/solutions/crypto-agility/",
  "https://venafi.com/crypto-agility-for-a-post-quantum-world/",
  "https://www.sealsq.com/investors/news-releases/sealsq-enhances-financial-sector-security-with-post-quantum-cryptography-solutions",
  "https://www.resquant.com/industries",
  "https://www.secure-ic.com/products/securyzr/post-quantum-cryptography/",
  "https://www.safelogic.com/products-and-services/post-quantum-cryptography",
  "https://www.quantinuum.com/",
  "https://www.qanapi.com/",
  "https://agnostiq.ai/products/cloud-security",
  "https://www.infiniquant.com/",
  "https://www.qaisec.com/",
  "https://qrate.ru/en/",
  "https://qubalt.de/"
    ]
    
    # Initialize scraper
    scraper = WebScraper(
        output_dir=args.output_dir,
        delay_min=args.delay_min,
        delay_max=args.delay_max,
        max_pages_per_domain=args.max_pages
    )
    
    # Create a summary file
    summary_path = os.path.join(args.output_dir, "scrape_summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as summary_file:
        summary_file.write(f"PQC Companies Web Scraping Summary\n")
        summary_file.write(f"Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        summary_file.write("-" * 80 + "\n\n")
        
        # Process each company URL
        total_pages = 0
        for url in company_urls:
            domain = urllib.parse.urlparse(url).netloc
            summary_file.write(f"Company: {domain}\n")
            summary_file.write(f"Starting URL: {url}\n")
            
            start_time = time.time()
            pages_scraped = scraper.crawl(url)
            end_time = time.time()
            
            summary_file.write(f"Pages scraped: {pages_scraped}\n")
            summary_file.write(f"Time taken: {end_time - start_time:.2f} seconds\n")
            summary_file.write("-" * 80 + "\n\n")
            
            total_pages += pages_scraped
        
        summary_file.write(f"Total pages scraped: {total_pages}\n")
    
    logger.info(f"Scraping completed. Results saved to {args.output_dir}")
    logger.info(f"Summary saved to {summary_path}")

if __name__ == "__main__":
    main()