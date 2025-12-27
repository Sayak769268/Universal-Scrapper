# Design Notes

## Static vs JS Fallback
- Strategy: "Static First, Dynamic Fallback".
  - We attempt to fetch the page using `requests` (synchronous, threaded) with a modern Chrome User-Agent. This proved more reliable than `httpx` for avoiding 403 blocks on some sites (e.g. Wikipedia).
  - If the static fetch fails (network error) or returns insufficient content (empty body, very little text), we trigger Playwright.
  - We inspect the result. If the static scrape yields no content, empty sections, or very little text (heuristic: total text length < 200 characters), we trigger the JS fallback.
  - We also check the raw HTML for keywords like "You need to enable JavaScript" or "Loading...".
  - **Anti-Bot Check:** If the final result is empty, we check the error logs for "403" or "Access Denied". If found, we explicitly flag this as a "Blocked" attempt in the UI.

## Wait Strategy for JS
- [x] Network idle
- [x] Fixed sleep
- [ ] Wait for selectors
- Details: I used `wait_until="networkidle"` on navigation to ensure the initial load is mostly complete. During interactions (clicks/scrolls), I used a short `wait_for_timeout` (fixed sleep) of 500-1000ms. This is simple and effective for a generic scraper where I don't know the specific selectors to wait for ahead of time.

## Click & Scroll Strategy
- Click flows implemented: 
  - I search for buttons with text content like "Load more", "Show more", "Read more", or elements with `[role='tab']` or class `.tab`.
  - I click up to 3 of these elements to reveal content.
- Scroll / pagination approach:
  - I implemented an infinite scroll strategy. The scraper scrolls to the bottom of the page `depth` times (default 3).
  - This covers "Load more" via scroll and many infinite scroll implementations.
  - Explicit pagination link following is not implemented in this MVP (complexity vs generic robustness trade-off).
- Stop conditions (max depth / timeout): 
  - Max scroll depth is fixed at 3.
  - Interaction clicks are limited to 3 candidates.
  - Navigation has a 30s timeout.

## Section Grouping & Labels
- How you group DOM into sections: 
  - I prioritize semantic tags: `header`, `nav`, `main`, `section`, `footer`, `article`, `aside`.
  - If none of these are found, I fallback to treating the `body` as a single section (or a better heuristic if implemented).
  - I assign stable IDs based on the tag name and index (e.g., `section-0`).
- How you derive section `type` and `label`:
  - `type`: Derived from the tag name (`nav` -> nav, `footer` -> footer) or class names (contains "hero", "faq", "pricing"). Defaults to "section".
  - `label`: I look for the first heading (`h1`-`h6`) within the section. If found, that becomes the label. If not, I use the first 5-7 words of the text content.

## Noise Filtering & Truncation
- What you filter out: 
  - Common noise selectors: `script`, `style`, `noscript`, `iframe`, `svg`.
  - UI nuisances: `.cookie-banner`, `.popup`, `.modal`, `.ad`, `.advertisement`.
- How you truncate `rawHtml` and set `truncated`:
  - I limit `rawHtml` to 1000 characters.
  - If the string length exceeds this, I slice it and append "...", setting `truncated` to `true`.
