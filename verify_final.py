
import asyncio
import json
import logging
from app.scraper import UniversalScraper

async def run_detailed_test():
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("Test")
    
    logger.info("--- STARTING FINAL VALIDATION ---")
    
    # URL 1: Simple Static Target (Example.com)
    url1 = "https://example.com"
    logger.info(f"Target 1: {url1}")
    result1 = await UniversalScraper.scrape(url1)
    
    if result1.sections:
        logger.info(f"SUCCESS: Found {len(result1.sections)} sections. Title: '{result1.meta.title}'")
    else:
        logger.error("FAILURE: No sections for example.com")
        exit(1)

    # URL 2: Wikipedia (Previously problematic)
    url2 = "https://en.wikipedia.org/wiki/Python_(programming_language)"
    logger.info(f"Target 2: {url2}")
    result2 = await UniversalScraper.scrape(url2)
    
    if len(result2.sections) > 10:
        logger.info(f"SUCCESS: Wikipedia scrape robust ({len(result2.sections)} sections).")
        # Check interactions object existence
        if result2.interactions:
             logger.info("Interactions object present.")
    else:
        logger.warning(f"WARNING: Low section count for Wikipedia: {len(result2.sections)}")

    # Check Labels
    logger.info("Checking section label quality...")
    bad_labels = [s.label for s in result2.sections if len(s.label) > 100 or "MenTopwear" in s.label]
    if not bad_labels:
        logger.info("SUCCESS: Labels seem clean and length-capped.")
    else:
        logger.warning(f"WARNING: Found suspicious labels: {bad_labels[:3]}")

    logger.info("--- VALIDATION COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(run_detailed_test())
