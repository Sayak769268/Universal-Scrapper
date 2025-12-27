# Universal Website Scraper

A full-stack web application that scrapes websites, extracting structured data into a JSON format. It supports both static and dynamic (JS-heavy) websites, with capabilities for handling basic interactions like clicks and scrolling using Playwright.

## Tech Stack
- **Static Scraping**: Uses `requests` with a modern Chrome User-Agent for reliable, high-speed fetching (bypassing 403 blocks). Parses with `BeautifulSoup4` (`lxml`).
- **Dynamic Scraping**: Uses `Playwright` (Chromium) with `playwright-stealth` to render JavaScript and bypass anti-bot detections when static scraping fails.
- **Robustness**: Automatically detects anti-bot blocks (e.g., Akamai, Cloudflare) and provides helpful UI feedback.
- **Backend**: `FastAPI` application for high-performance async processing.
- **Frontend**: Premium "Glassmorphic" UI with responsive design, JSON viewing, and a dedicated Reset/Clear button.

## Setup & Run

The project includes a `run.sh` script to automate setup and execution.

### Prerequisites
- Python 3.10+
- Git bash (or compatible shell on Windows)

### Instructions

1.  Open your terminal in the project root.
2.  Make the script executable (if needed, though on Windows `bash run.sh` usually works):
    ```bash
    chmod +x run.sh
    ```
3.  Run the script:
    ```bash
    ./run.sh
    ```

This script will:
- Create a virtual environment (`venv`).
- Install Python dependencies.
- Install Playwright browsers (chromium).
- Start the server on `http://localhost:8000`.

## Usage

1.  Open your browser to `http://localhost:8000`.
2.  Enter a URL (e.g., `https://news.ycombinator.com/`).
3.  Click **Scrape**.
4.  View the results:
    - **Meta:** Title, description, language.
    - **Sections:** Content broken down by page sections (click to expand for JSON).
    - **Interactions:** Details on clicks, scrolls, and pages visited (auto-hides if empty).
5.  Click **Download JSON** to save the full result.
6.  Use the **Reset Button** (circular arrow) to clear the input and start over.

## API Endpoints

-   `GET /healthz`: Health check. Returns `{ "status": "ok" }`.
-   `POST /scrape`: Scrape a URL.
    -   Body: `{ "url": "https://example.com" }`
    -   Response: JSON object with scraped content.

## Test URLs
I used the following URLs for testing:

1.  **https://en.wikipedia.org/wiki/Artificial_intelligence**
    -   *Type:* Static.
    -   *Why:* To verify basic HTML parsing, section grouping, and metadata extraction without JS overhead.
2.  **https://vercel.com/**
    -   *Type:* Dynamic / JS-Heavy.
    -   *Why:* To test the JS fallback strategy, ensuring content rendered by React is captured.
3.  **http://quotes.toscrape.com/scroll**
    -   *Type:* Infinite Scroll.
    -   *Why:* To demonstrate the scraper's ability to automatically scroll down and capture dynamically loaded content.

## Limitations
-   **Complex interactions:** The scraper handles basic "Load More" buttons and standard tabs, but complex SPAs with non-standard navigation might not be fully explored.
-   **Anti-bot measures:** Sites with aggressive anti-bot protections (Cloudflare, etc.) may block the scraper.
-   **Table parsing:** Table parsing is rudimentary and may not preserve complex headers or merged cells perfectly.

---
<div align="center">
  <b>Made with ❤️ by Sayak Mukherjee</b>
</div>
