from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.models import ScrapeRequest, ScrapeResponse, ScrapeResult, Error, Interactions, MetaData
from app.scraper import UniversalScraper
import os

app = FastAPI(title="Universal Website Scraper")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="app/templates")

@app.get("/healthz")
async def health_check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/scrape", response_model=ScrapeResponse)
async def scrape_url(request: ScrapeRequest):
    try:
        # Validate URL scheme
        if request.url.scheme not in ["http", "https"]:
             raise HTTPException(status_code=400, detail="Only http and https schemes are supported.")
        
        result = await UniversalScraper.scrape(str(request.url))
        return ScrapeResponse(result=result)
    except Exception as e:
        # Return a partial failure if possible, or a 500
        # The spec asks for a JSON response with errors, but FastAPI exception handler might override.
        # Let's try to construct a valid result with the error if it was a high level failure
        import traceback
        traceback.print_exc() # Print to console for debugging
        return ScrapeResponse(result=ScrapeResult(
            url=str(request.url),
            scrapedAt="",
            meta=MetaData(),
            sections=[],
            interactions=Interactions(),
            errors=[Error(message=f"{type(e).__name__}: {str(e)}", phase="api_handler")]
        ))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
