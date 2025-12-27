
import asyncio
import re
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import httpx
import requests
from bs4 import BeautifulSoup, Comment, Tag
from playwright.async_api import async_playwright, Page, BrowserContext
from playwright_stealth import stealth
from app.models import (
    ScrapeResult, MetaData, Section, SectionContent, 
    Link, Image, Interactions, Error
)
from urllib.parse import urljoin, urlparse
from fake_useragent import UserAgent

# Constants
MAX_RAW_HTML_LENGTH = 1000
MIN_TEXT_LENGTH_FOR_SECTION = 1
NOISE_SELECTORS = [
    "script", "style", "noscript", "iframe", "svg", 
    ".cookie-banner", "#cookie-banner", ".popup", ".modal", 
    "[aria-modal='true']", ".ad", ".advertisement", ".dialog",
    "#onetrust-banner-sdk"
]
SECTION_TAGS = ["header", "nav", "main", "section", "footer", "article", "aside"]
HEADING_TAGS = ["h1", "h2", "h3", "h4", "h5", "h6"]

class ScraperUtils:
    @staticmethod
    def clean_text(text: str) -> str:
        # Replace newlines/tabs with spaces and collapse multiple spaces
        text = re.sub(r'[\r\n\t]+', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    @staticmethod
    def truncate_html(html: str, max_length: int = MAX_RAW_HTML_LENGTH) -> Tuple[str, bool]:
        if len(html) <= max_length:
            return html, False
        return html[:max_length] + "...", True

    @staticmethod
    def extract_meta(soup: BeautifulSoup, url: str) -> MetaData:
        title = None
        if soup.title:
            title = soup.title.string 
        
        if not title:
            og_title = soup.find("meta", property="og:title")
            if og_title:
                title = og_title.get("content")

        description = None
        meta_desc = soup.find("meta", attrs={"name": "description"})
        if meta_desc:
            description = meta_desc.get("content")
        
        language = soup.html.get("lang") if soup.html else None
        
        canonical = None
        link_canonical = soup.find("link", rel="canonical")
        if link_canonical:
            canonical = link_canonical.get("href")
            # Ensure absolute URL
            canonical = urljoin(url, canonical)
            
        return MetaData(
            title=title,
            description=description,
            language=language,
            canonical=canonical
        )

    @staticmethod
    def get_section_type(tag_name: str, class_names: List[str], text_sample: str) -> str:
        class_str = " ".join(class_names).lower()
        if tag_name == "nav" or "nav" in class_str:
            return "nav"
        if tag_name == "footer" or "footer" in class_str:
            return "footer"
        if "hero" in class_str:
            return "hero"
        if "faq" in class_str:
            return "faq"
        if "price" in class_str or "pricing" in class_str:
            return "pricing"
        if tag_name == "ul" or tag_name == "ol":
            return "list"
        # Heuristic for grid? maybe later
        return "section"

    @staticmethod
    def get_section_label(elem: Tag, text: str) -> str:
        # 1. Try to find a heading inside
        heading = elem.find(["h1", "h2", "h3", "h4", "h5", "h6"])
        if heading:
            return ScraperUtils.clean_text(heading.get_text(separator=" ", strip=True))
        
        # 2. Use aria-label if present
        if elem.get("aria-label"):
            return ScraperUtils.clean_text(elem.get("aria-label"))
            
        # 3. Heuristic for Nav/Footer based on tag name
        if elem.name == 'nav':
            return "Navigation"
        if elem.name == 'footer':
            return "Footer"

        # 4. Fallback to first few words
        # Take up to 10 words, but ensure we don't grab a giant mashed string
        words = text.split()
        if words:
            # Join first 5 words
            label = " ".join(words[:5])
            # Cap at 50 chars
            if len(label) > 50:
                return label[:47] + "..."
            return label
        
        return "Untitled Section"

    @staticmethod
    def parse_sections(soup: BeautifulSoup, base_url: str) -> List[Section]:
        sections = []
        
        # Remove noise
        for selector in NOISE_SELECTORS:
            for noise in soup.select(selector):
                noise.decompose()
        
        # Identify section candidates
        # We start with semantic tags, then fall back to divs with substantial content if needed.
        candidates = soup.find_all(SECTION_TAGS)
        
        # Add common content wrappers
        div_candidates = soup.find_all("div", class_=re.compile(r"content|main|article|body|entry", re.I))
        candidates.extend(div_candidates)

        if not candidates:
             if soup.body:
                 candidates = [soup.body]
             elif soup.html:
                 candidates = [soup.html]
             else:
                 candidates = []

        seen_ids = set()
        
        for idx, elem in enumerate(candidates):
            if elem is None: continue
            
            # Use ID if present, else generate one
            sec_id = elem.get("id")
            if not sec_id:
                sec_id = f"{elem.name}-{idx}"
            
            # Ensure unique ID
            counter = 1
            original_sec_id = sec_id
            while sec_id in seen_ids:
                sec_id = f"{original_sec_id}-{counter}"
                counter += 1
            seen_ids.add(sec_id)

            # Extract content
            text_content = ScraperUtils.clean_text(elem.get_text(separator=" ", strip=True))
            if len(text_content) < MIN_TEXT_LENGTH_FOR_SECTION and elem.name != 'img':
                continue # Skip empty sections

            headings = [ScraperUtils.clean_text(h.get_text(separator=" ", strip=True)) for h in elem.find_all(HEADING_TAGS)]
            
            links = []
            for a in elem.find_all("a", href=True):
                href = urljoin(base_url, a["href"])
                links.append(Link(text=ScraperUtils.clean_text(a.get_text()), href=href))
            
            images = []
            for img in elem.find_all("img", src=True):
                src = urljoin(base_url, img["src"])
                alt = img.get("alt", "")
                images.append(Image(src=src, alt=alt))
            
            lists = []
            for ul in elem.find_all(["ul", "ol"]):
                items = [ScraperUtils.clean_text(li.get_text(separator=" ", strip=True)) for li in ul.find_all("li")]
                if items:
                    lists.append(items)
            
            tables = [] # Placeholder logic for tables
            for table in elem.find_all("table"):
                # heavily simplified table parsing
                rows_data = []
                for tr in table.find_all("tr"):
                     cells = [ScraperUtils.clean_text(td.get_text()) for td in tr.find_all(["td", "th"])]
                     rows_data.append(cells)
                tables.append(rows_data)

            raw_html, truncated = ScraperUtils.truncate_html(str(elem))
            
            sec_type = ScraperUtils.get_section_type(elem.name, elem.get("class", []), text_content)
            label = ScraperUtils.get_section_label(elem, text_content)

            sections.append(Section(
                id=sec_id,
                type=sec_type,
                label=label,
                sourceUrl=base_url,
                content=SectionContent(
                    headings=headings,
                    text=text_content,
                    links=links,
                    images=images,
                    lists=lists,
                    tables=tables
                ),
                rawHtml=raw_html,
                truncated=truncated
            ))
            
        return sections

class StaticScraper:
    async def scrape(self, url: str) -> Tuple[Optional[str], Optional[MetaData], List[Section], List[Error]]:
        errors = []
        try:
            # Use a modern User-Agent to avoid blocks
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            headers = {
                "User-Agent": user_agent,
            }
            
            # Use requests in a thread (more reliable than httpx for some targets)
            def fetch():
                return requests.get(url, headers=headers, timeout=10)
            
            response = await asyncio.to_thread(fetch)
            response.raise_for_status()
            
            # Fix encoding issues (mojibake)
            if response.encoding == 'ISO-8859-1':
                response.encoding = response.apparent_encoding
                
            html = response.text
            
            soup = BeautifulSoup(html, "lxml")
            meta = ScraperUtils.extract_meta(soup, url)
            sections = ScraperUtils.parse_sections(soup, url)
            
            return html, meta, sections, errors
        except Exception as e:
            errors.append(Error(message=f"Static fetch failed: {str(e)}", phase="static_fetch"))
            return None, None, [], errors

class PlaywrightScraper:
    @staticmethod
    async def scrape(url: str, depth: int = 3) -> Tuple[Optional[str], Optional[MetaData], List[Section], Interactions, List[Error]]:
        errors = []
        interactions = Interactions()
        
        async with async_playwright() as p:
            try:
                # Add args to reduce detection
                browser = await p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-accelerated-2d-canvas",
                        "--no-first-run",
                        "--no-zygote",
                        "--disable-gpu",
                    ]
                )
                
                ua = UserAgent()
                user_agent = ua.random

                context = await browser.new_context(
                    user_agent=user_agent,
                    viewport={"width": 1920, "height": 1080},
                    device_scale_factor=1,
                    locale="en-US",
                )
                
                page = await context.new_page()
                await stealth(page)
                
                # Navigate
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    await page.wait_for_timeout(3000) 

                    # Attempt to handle cookie banners simply
                    try:
                        accept_btn = await page.query_selector("button:has-text('Accept'), button:has-text('Agree'), #onetrust-accept-btn-handler")
                        if accept_btn:
                            await accept_btn.click(timeout=2000)
                            await page.wait_for_timeout(1000)
                    except:
                        pass

                except Exception as e:
                    errors.append(Error(message=f"Navigation timeout or error: {str(e)}", phase="navigation"))
                
                interactions.pages.append(page.url)

                # --- INTERACTION PHASE ---
                
                # 1. Click tabs or 'Load more'
                interaction_selectors = [
                    "button:has-text('Load more')",
                    "button:has-text('Read more')",
                    "button:has-text('Show more')",
                    "[role='tab']",
                    ".tab",
                ]
                
                for selector in interaction_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        for i, handle in enumerate(elements[:3]): # Limit to first 3
                            if await handle.is_visible():
                                await handle.click(timeout=1000)
                                interactions.clicks.append(selector)
                                await page.wait_for_timeout(500) 
                    except Exception:
                        pass 

                # 2. Infinite Scroll / Pagination
                for _ in range(depth):
                    try:
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        await page.wait_for_timeout(1500) 
                        interactions.scrolls += 1
                        
                    except Exception as e:
                        errors.append(Error(message=f"Scroll error: {str(e)}", phase="interaction"))

                if page.url not in interactions.pages:
                    interactions.pages.append(page.url)

                # Get Content
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                meta = ScraperUtils.extract_meta(soup, url)
                sections = ScraperUtils.parse_sections(soup, url)
                
                await browser.close()
                return content, meta, sections, interactions, errors

            except Exception as e:
                errors.append(Error(message=str(e), phase="playwright_setup"))
                return None, None, [], interactions, errors

# Main Scraper Orchestrator
class UniversalScraper:
    @staticmethod
    async def scrape(url: str) -> ScrapeResult:
        try:
            # 1. Try Static First
            static_scraper = StaticScraper()
            html, meta, sections, static_errors = await static_scraper.scrape(url)
            
            needs_fallback = False
            
            # Updated Heuristics
            if not html:
                needs_fallback = True
            elif not sections:
                needs_fallback = True
            else:
                total_text = sum(len(s.content.text) for s in sections)
                if total_text < 300: # Increased threshold
                    needs_fallback = True
                
                suspicious_titles = ["Access Denied", "Just a moment", "Challenge", "Security Check", "Robot", "Captcha"]
                if meta and meta.title:
                    for t in suspicious_titles:
                        if t.lower() in meta.title.lower():
                            needs_fallback = True
                            break
                # Check for body-only simplistic fails
                if len(sections) == 1 and sections[0].content.text == "":
                    needs_fallback = True
    
            if html and ("You need to enable JavaScript" in html or "Loading..." in html):
                needs_fallback = True
    
            final_sections = sections if sections else []
            final_meta = meta
            interactions = Interactions()
            final_errors = static_errors
    
            if needs_fallback:
                # 2. Playwright Fallback
                dynamic_content, dynamic_meta, dynamic_sections, dyn_interactions, dyn_errors = await PlaywrightScraper.scrape(url)
                
                if dynamic_content: 
                    final_sections = dynamic_sections
                    final_meta = dynamic_meta
                    interactions = dyn_interactions
                    final_errors = dyn_errors
                elif not final_sections: 
                    final_errors.extend(dyn_errors)
    
            if not final_sections:
                error_msg = "No sections found. The page might be empty, purely graphical, or blocking our scraper."
                
                # Check for definitive block signals in errors
                is_blocked = any("403" in e.message or "Access Denied" in e.message for e in final_errors)
                if is_blocked:
                    error_msg = "Scraping Blocked (Anti-Bot Defense Detected)."
                    final_errors.append(Error(
                        message="Target site is using advanced protection (e.g., Akamai, Cloudflare). Standard scrapers cannot bypass this without residential proxies.",
                        phase="analysis_tip"
                    ))
                else:
                    final_errors.append(Error(
                        message="Try checking if the site requires a login or has mostly canvas/image content.",
                        phase="analysis_tip"
                    ))
                
                final_errors.append(Error(message=error_msg, phase="result_validation"))
            
            if not final_meta:
                final_meta = MetaData()
    
            return ScrapeResult(
                url=url,
                scrapedAt=datetime.now(timezone.utc).isoformat(),
                meta=final_meta,
                sections=final_sections,
                interactions=interactions,
                errors=final_errors
            )
        except Exception as e:
            # THIS IS THE CATCH-ALL TO PREVENT 500s or NotImplementedErrors bubbling up
            import traceback
            traceback.print_exc()
            return ScrapeResult(
                url=url,
                scrapedAt=datetime.now(timezone.utc).isoformat(),
                meta=MetaData(),
                sections=[],
                interactions=Interactions(),
                errors=[Error(message=f"CRITICAL SCRAPER ERROR: {str(e)}", phase="core_engine")]
            )
