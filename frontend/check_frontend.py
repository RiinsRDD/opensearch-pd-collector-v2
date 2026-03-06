from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(args=['--no-sandbox', '--disable-setuid-sandbox'])
        page = browser.new_page()
        
        # Capture console errors
        def handle_console(msg):
            if msg.type in ('error', 'warning'):
                print(f"Browser Console {msg.type.upper()}: {msg.text}")
        
        page.on("console", handle_console)
        
        # Capture unhandled exceptions
        def handle_page_error(exc):
            print(f"PAGE ERROR: {exc}")
            
        page.on("pageerror", handle_page_error)
        
        print("Navigating to settings...")
        try:
            page.goto("http://localhost:5173/settings", wait_until="networkidle", timeout=10000)
            page.wait_for_timeout(2000)
            print("Successfully loaded Settings page.")
            
            # Print page content to see if it's blank
            body = page.locator("body").inner_text()
            print("Body preview:", body[:200].replace("\n", " "))
        except Exception as e:
            print("Failed to navigate/load:", e)
        
        browser.close()

if __name__ == "__main__":
    run()
