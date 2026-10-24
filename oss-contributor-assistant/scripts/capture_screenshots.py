import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    os.makedirs('docs/images', exist_ok=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='msedge', headless=True)
        context = await browser.new_context(viewport={'width': 1280, 'height': 850})
        page = await context.new_page()
        
        print("Navigating to http://localhost:8001...")
        await page.goto('http://localhost:8001', wait_until='networkidle')
        await page.wait_for_timeout(1000)
        
        await page.screenshot(path='docs/images/ui-homepage.png')
        print("Captured docs/images/ui-homepage.png")
        
        # Fill repo input
        print("Submitting repository for analysis...")
        await page.fill('#repoUrl', 'https://github.com/octocat/Hello-World')
        await page.click('button[type="submit"]')
        
        # Wait for result to be visible
        print("Waiting for result section...")
        await page.wait_for_selector('#result:not(.hidden)', timeout=60000)
        await page.wait_for_timeout(2500)
        
        # Click open the first accordion or details section to show rich content
        details_elements = await page.query_selector_all('details')
        for det in details_elements[:2]:
            await det.evaluate('el => el.open = true')
        
        await page.wait_for_timeout(1000)
        await page.screenshot(path='docs/images/ui-analysis-result.png', full_page=True)
        print("Captured docs/images/ui-analysis-result.png")
        
        await browser.close()
        print("All screenshots successfully captured!")

if __name__ == '__main__':
    asyncio.run(main())
