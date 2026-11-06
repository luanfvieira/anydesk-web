"""Read-only browser smoke check against the local tunnel; no remote connection requested."""
import asyncio
import json
from pathlib import Path
from playwright.async_api import async_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        page = await browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        await page.goto('http://127.0.0.1:8765/')
        await page.locator('#login-panel').wait_for(state='visible')
        await page.screenshot(path=str(ROOT / 'verification/login.png'), full_page=True)
        await page.locator('#password').fill((ROOT / '.runtime/password.txt').read_text().strip())
        await page.locator('#login-form button').click()
        await page.locator('#workspace').wait_for(state='visible')
        await expect(page.locator('#transport-label')).to_have_text('Ponte ativa')
        await page.wait_for_timeout(4000)
        frame_ready = await page.locator('#screen').evaluate("e=>e.classList.contains('ready')")
        await page.screenshot(path=str(ROOT / 'verification/workspace.png'), full_page=True)
        await page.set_viewport_size({'width': 390, 'height': 844})
        await page.screenshot(path=str(ROOT / 'verification/mobile.png'), full_page=True)
        overflow = await page.evaluate('document.documentElement.scrollWidth > innerWidth')
        await page.locator('#logout').click()
        await page.locator('#login-panel').wait_for(state='visible')
        assert not errors, errors
        assert not overflow, 'Mobile horizontal overflow'
        result = {'login': True, 'websocket': True, 'frame_ready': frame_ready,
                  'logout': True, 'mobile_overflow': overflow, 'javascript_errors': errors,
                  'remote_connection_tested': False}
        (ROOT / 'verification/browser.json').write_text(json.dumps(result, indent=2))
        print(json.dumps(result))
        await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
