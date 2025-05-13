import asyncio
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from typing import Optional, Dict, Any
import logging

from .config_loader import ConfigLoader

logger = logging.getLogger(__name__)

class BrowserManager:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.playwright: Optional[Playwright] = None
        self.browser: Optional[Browser] = None
        self._contexts: Dict[str, BrowserContext] = {}
        self._pages: Dict[str, Page] = {}
        self._active_context_id: Optional[str] = None
        self._active_page_id: Optional[str] = None
        self._default_context_id_prefix = "default_ctx_"
        self._default_page_id_prefix = "default_page_"
        self._context_counter = 0
        self._page_counter = 0

    async def start_browser(self) -> None:
        if self.browser and self.browser.is_connected():
            logger.info("Browser is already running.")
            return

        self.playwright = await async_playwright().start()
        browser_config = self.config_loader.get_browser_config()
        browser_type = browser_config.get("browser_type", "chromium")
        launch_options = {
            "headless": browser_config.get("headless", True),
            "slow_mo": browser_config.get("slow_mo", 0),
        }
        if browser_config.get("proxy"):
            launch_options["proxy"] = browser_config.get("proxy")
        
        logger.info(f"Launching {browser_type} browser with options: {launch_options}")
        try:
            if browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(**launch_options)
            elif browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**launch_options)
            elif browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**launch_options)
            else:
                logger.error(f"Unsupported browser type: {browser_type}. Defaulting to chromium.")
                self.browser = await self.playwright.chromium.launch(**launch_options)
            logger.info(f"{browser_type} browser launched successfully.")
            # Create a default context and page on startup
            await self.create_context(context_id="initial_default_context")
        except Exception as e:
            logger.error(f"Failed to launch browser: {e}")
            if self.playwright:
                await self.playwright.stop()
            raise

    async def create_context(self, context_id: Optional[str] = None, context_options: Optional[Dict[str, Any]] = None) -> str:
        if not self.browser or not self.browser.is_connected():
            logger.warning("Browser not started. Attempting to start browser.")
            await self.start_browser()
        
        if not self.browser: # Should not happen if start_browser is successful
             raise ConnectionError("Browser is not available after attempting to start.")

        options = context_options or {}
        browser_cfg = self.config_loader.get_browser_config()
        if browser_cfg.get("user_agent") and "user_agent" not in options:
            options["user_agent"] = browser_cfg.get("user_agent")
        if browser_cfg.get("viewport_size") and "viewport" not in options:
            options["viewport"] = browser_cfg.get("viewport_size")
        
        new_context = await self.browser.new_context(**options)
        self._context_counter += 1
        c_id = context_id or f"{self._default_context_id_prefix}{self._context_counter}"
        self._contexts[c_id] = new_context
        if not self._active_context_id or context_id == "initial_default_context": # Activate first context or specified initial
            self._active_context_id = c_id
        logger.info(f"Created new browser context with ID: {c_id} and options: {options}")
        # Automatically create a default page for the new context
        await self.create_page(context_id=c_id, page_id=f"initial_page_for_{c_id}")
        return c_id

    async def create_page(self, context_id: Optional[str] = None, page_id: Optional[str] = None) -> str:
        target_context_id = context_id or self._active_context_id
        if not target_context_id or target_context_id not in self._contexts:
            logger.error(f"Context ID '{target_context_id}' not found. Cannot create page.")
            # Attempt to create a default context if none active
            if not self._active_context_id:
                logger.info("No active context. Creating a new default context.")
                target_context_id = await self.create_context()
            else:
                raise ValueError(f"Context ID '{target_context_id}' not found.")
        context = self._contexts[target_context_id]
        new_page = await context.new_page()
        self._page_counter += 1
        p_id = page_id or f"{self._default_page_id_prefix}{self._page_counter}"
        self._pages[p_id] = new_page
        if not self._active_page_id or page_id and page_id.startswith("initial_page_for_"): # Activate first page or specified initial
            self._active_page_id = p_id
        logger.info(f"Created new page with ID: {p_id} in context: {target_context_id}")
        return p_id

    def get_active_page(self) -> Optional[Page]:
        if self._active_page_id and self._active_page_id in self._pages:
            return self._pages[self._active_page_id]
        elif self._pages: # Fallback to the first available page if no active one is set but pages exist
            logger.warning("No active page set, returning the first available page.")
            return next(iter(self._pages.values()))
        logger.warning("No active page available.")
        return None

    def get_page_by_id(self, page_id: str) -> Optional[Page]:
        return self._pages.get(page_id)

    def get_active_context(self) -> Optional[BrowserContext]:
        if self._active_context_id and self._active_context_id in self._contexts:
            return self._contexts[self._active_context_id]
        logger.warning("No active context available.")
        return None

    def get_context_by_id(self, context_id: str) -> Optional[BrowserContext]:
        return self._contexts.get(context_id)

    def set_active_context(self, context_id: str) -> bool:
        if context_id in self._contexts:
            self._active_context_id = context_id
            logger.info(f"Switched active context to: {context_id}")
            # When switching context, also try to set an active page (e.g., first page of that context)
            # This logic might need refinement based on how pages are associated with contexts
            # For now, we assume pages are globally managed but logically belong to contexts.
            # A better approach would be to store pages within their context objects.
            self._active_page_id = None # Reset active page, let create_page or another mechanism set it.
            for pid, page_obj in self._pages.items():
                if page_obj.context == self._contexts[context_id]:
                    self._active_page_id = pid
                    logger.info(f"Set active page to {pid} from new active context {context_id}")
                    break
            if not self._active_page_id and self._contexts[context_id].pages:
                # If context has pages but none are in our _pages dict (e.g. opened by user js)
                # This part is tricky without more robust page tracking within contexts.
                # For now, if no page from our dict matches, we might need to create one or error.
                logger.warning(f"Context {context_id} has pages, but no tracked active page set.")
            return True
        logger.error(f"Context ID {context_id} not found.")
        return False

    def set_active_page(self, page_id: str) -> bool:
        if page_id in self._pages:
            self._active_page_id = page_id
            # Ensure the active context is the one this page belongs to
            page_context = self._pages[page_id].context
            for ctx_id, ctx_obj in self._contexts.items():
                if ctx_obj == page_context:
                    if self._active_context_id != ctx_id:
                         self._active_context_id = ctx_id
                         logger.info(f"Implicitly switched active context to {ctx_id} based on active page {page_id}")
                    break
            logger.info(f"Switched active page to: {page_id}")
            return True
        logger.error(f"Page ID {page_id} not found.")
        return False

    async def close_page(self, page_id: str) -> bool:
        if page_id in self._pages:
            page = self._pages.pop(page_id)
            await page.close()
            logger.info(f"Closed page: {page_id}")
            if self._active_page_id == page_id:
                self._active_page_id = None
                # Try to set another page as active if available
                if self._pages:
                    self._active_page_id = next(iter(self._pages.keys()))
                    logger.info(f"Set active page to {self._active_page_id} after closing previous active page.")
            return True
        logger.warning(f"Page ID {page_id} not found for closing.")
        return False

    async def close_context(self, context_id: str) -> bool:
        if context_id in self._contexts:
            context = self._contexts.pop(context_id)
            # Close all pages associated with this context
            pages_to_close = [pid for pid, page in self._pages.items() if page.context == context]
            for pid in pages_to_close:
                await self.close_page(pid)
            await context.close()
            logger.info(f"Closed context: {context_id}")
            if self._active_context_id == context_id:
                self._active_context_id = None
                # Try to set another context as active if available
                if self._contexts:
                    self._active_context_id = next(iter(self._contexts.keys()))
                    logger.info(f"Set active context to {self._active_context_id} after closing previous active context.")
                    # Also attempt to set an active page for this new active context
                    self.set_active_context(self._active_context_id) # Re-call to set active page
            return True
        logger.warning(f"Context ID {context_id} not found for closing.")
        return False

    async def close_browser(self) -> None:
        if self.browser and self.browser.is_connected():
            await self.browser.close()
            self.browser = None
            logger.info("Browser closed.")
        if self.playwright:
            await self.playwright.stop()
            self.playwright = None
            logger.info("Playwright stopped.")
        self._contexts.clear()
        self._pages.clear()
        self._active_context_id = None
        self._active_page_id = None

# Example Usage (for testing, to be integrated into the main service)
async def main_test():
    # Create a dummy config.json for testing if it doesn't exist
    dummy_config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config.json")
    if not os.path.exists(dummy_config_path):
        print(f"Creating dummy config at {dummy_config_path} for testing browser_manager.")
        dummy_data = {
            "browser_type": "chromium", "headless": False, "slow_mo": 50,
            "service": {"port": 8080}
        }
        with open(dummy_config_path, "w") as f: json.dump(dummy_data, f)
    
    config = ConfigLoader(config_path=dummy_config_path)
    manager = BrowserManager(config_loader=config)
    try:
        await manager.start_browser()
        print(f"Browser started. Active context: {manager._active_context_id}, Active page: {manager._active_page_id}")
        
        page = manager.get_active_page()
        if page:
            print("Attempting to navigate to example.com")
            await page.goto("http://example.com")
            print(f"Page title: {await page.title()}")
            await asyncio.sleep(2) # Keep browser open for a bit
        else:
            print("No active page found after startup.")

        ctx_id_2 = await manager.create_context(context_options={"user_agent": "TestAgent/1.0"})
        print(f"Created second context: {ctx_id_2}")
        manager.set_active_context(ctx_id_2)
        page_id_2 = await manager.create_page()
        print(f"Created page in second context: {page_id_2}")
        page2 = manager.get_active_page()
        if page2:
            await page2.goto("http://google.com")
            print(f"Page 2 title: {await page2.title()}")
            await asyncio.sleep(2)

    except Exception as e:
        print(f"Error during BrowserManager test: {e}")
    finally:
        print("Closing browser...")
        await manager.close_browser()

if __name__ == "__main__":
    # Setup basic logging for the test
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    asyncio.run(main_test())

