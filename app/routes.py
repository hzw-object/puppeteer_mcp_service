from app.browser_manager import BrowserManager

from app.config_loader import ConfigLoader

from app.utils import api_method_handler, RPCException, BROWSER_OPERATION_ERROR, PAGE_NOT_AVAILABLE_ERROR, JSON_RPC_INVALID_PARAMS, ELEMENT_NOT_FOUND_ERROR

from typing import Dict, Any, Optional, Union, List

import base64

import os

import logging



logger = logging.getLogger(__name__)



# Global instances to be initialized by main.py

_browser_manager: Optional[BrowserManager] = None

_config_loader: Optional[ConfigLoader] = None



def initialize_routes(browser_manager: BrowserManager, config_loader: ConfigLoader):

    global _browser_manager, _config_loader

    _browser_manager = browser_manager

    _config_loader = config_loader

    logger.info("Routes initialized with browser_manager and config_loader.")



async def _get_active_page_or_raise():

    if not _browser_manager:

        raise RPCException(code=BROWSER_OPERATION_ERROR, message="Browser manager not initialized.")

    page = _browser_manager.get_active_page()

    if not page:

        # Try to create a default page if none exists

        logger.warning("No active page found. Attempting to create a new default page.")

        try:

            await _browser_manager.create_page() # This will also set it as active if it's the first

            page = _browser_manager.get_active_page()

            if not page:

                 raise RPCException(code=PAGE_NOT_AVAILABLE_ERROR, message="No active page available and failed to create a new one.")

        except Exception as e:

            logger.error(f"Failed to auto-create page: {e}")

            raise RPCException(code=PAGE_NOT_AVAILABLE_ERROR, message=f"No active page available. Auto-creation failed: {e}")

    return page



@api_method_handler

async def puppeteer_navigate(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    url = params.get("url")

    if not url or not isinstance(url, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'url' parameter is required and must be a string.", id=rpc_id)

    

    timeout = params.get("timeout", _config_loader.get_service_config().get("default_timeout"))

    wait_until = params.get("wait_until", "load") # Playwright defaults: load, domcontentloaded, networkidle, commit



    page = await _get_active_page_or_raise()

    try:

        logger.info(f"Navigating to {url} with timeout {timeout}ms and wait_until '{wait_until}'")

        response = await page.goto(url, timeout=float(timeout), wait_until=wait_until)

        status = response.status if response else "unknown"

        logger.info(f"Navigation to {url} completed with status: {status}")

        return {"status": "success", "url": page.url, "http_status": status}

    except Exception as e:

        logger.error(f"Navigation to {url} failed: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Navigation failed: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_get_page_title(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    page = await _get_active_page_or_raise()

    try:

        title = await page.title()

        return {"status": "success", "title": title}

    except Exception as e:

        logger.error(f"Failed to get page title: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to get page title: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_get_current_url(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    page = await _get_active_page_or_raise()

    try:

        current_url = page.url

        return {"status": "success", "url": current_url}

    except Exception as e:

        logger.error(f"Failed to get current URL: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to get current URL: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_take_page_screenshot(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    page = await _get_active_page_or_raise()

    

    path = params.get("path")

    full_page = params.get("full_page", True)

    screenshot_type = params.get("type", "png") # png or jpeg

    quality = params.get("quality") # For jpeg, 0-100

    omit_background = params.get("omit_background", False) # For png



    if path and not isinstance(path, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'path' parameter must be a string if provided.", id=rpc_id)

    if screenshot_type not in ["png", "jpeg"]:

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'type' parameter must be 'png' or 'jpeg'.", id=rpc_id)



    options = {

        "full_page": full_page,

        "type": screenshot_type,

    }

    if path:

        options["path"] = path

        # Ensure directory exists if path is provided

        try:

            os.makedirs(os.path.dirname(path), exist_ok=True)

        except Exception as e:

            raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to create directory for screenshot path: {str(e)}", id=rpc_id)



    if screenshot_type == "jpeg" and quality is not None:

        if not (isinstance(quality, int) and 0 <= quality <= 100):

            raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'quality' must be an integer between 0 and 100 for jpeg.", id=rpc_id)

        options["quality"] = quality

    if screenshot_type == "png" and omit_background:

        options["omit_background"] = omit_background



    try:

        logger.info(f"Taking page screenshot with options: {options}")

        image_bytes = await page.screenshot(**options)

        if path:

            logger.info(f"Screenshot saved to {path}")

            return {"status": "success", "file_path": path}

        else:

            image_base64 = base64.b64encode(image_bytes).decode("utf-8")

            logger.info("Screenshot taken and encoded in base64.")

            return {"status": "success", "image_base64": image_base64}

    except Exception as e:

        logger.error(f"Failed to take page screenshot: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Screenshot failed: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_get_page_content(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    page = await _get_active_page_or_raise()

    try:

        content = await page.content()

        return {"status": "success", "content": content}

    except Exception as e:

        logger.error(f"Failed to get page content: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to get page content: {str(e)}", id=rpc_id)



# Add more API methods here following the pattern...



@api_method_handler

async def puppeteer_click_element(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    selector = params.get("selector")

    if not selector or not isinstance(selector, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'selector' parameter is required and must be a string.", id=rpc_id)

    

    timeout = params.get("timeout", _config_loader.get_service_config().get("default_timeout"))

    button = params.get("button", "left")

    click_count = params.get("click_count", 1)



    page = await _get_active_page_or_raise()

    try:

        logger.info(f"Clicking element '{selector}' with timeout {timeout}ms, button '{button}', click_count {click_count}")

        element = await page.wait_for_selector(selector, timeout=float(timeout))

        if not element:

            raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Element with selector '{selector}' not found.", id=rpc_id)

        await element.click(button=button, click_count=click_count, timeout=float(timeout))

        logger.info(f"Clicked element '{selector}' successfully.")

        return {"status": "success"}

    except Exception as e:

        logger.error(f"Failed to click element '{selector}': {e}")

        if "Target closed" in str(e) or "Timeout" in str(e):

             raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Failed to click element (selector: {selector}): {str(e)}", id=rpc_id)

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to click element (selector: {selector}): {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_fill_form_field(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    selector = params.get("selector")

    value = params.get("value") # value can be empty string



    if not selector or not isinstance(selector, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'selector' parameter is required and must be a string.", id=rpc_id)

    if value is None or not isinstance(value, str): # Ensure value is a string, even if empty

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'value' parameter is required and must be a string.", id=rpc_id)



    timeout = params.get("timeout", _config_loader.get_service_config().get("default_timeout"))

    page = await _get_active_page_or_raise()

    try:

        logger.info(f"Filling form field '{selector}' with value '{value}' and timeout {timeout}ms")

        element = await page.wait_for_selector(selector, timeout=float(timeout))

        if not element:

            raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Element with selector '{selector}' not found.", id=rpc_id)

        await element.fill(value, timeout=float(timeout))

        logger.info(f"Filled form field '{selector}' successfully.")

        return {"status": "success"}

    except Exception as e:

        logger.error(f"Failed to fill form field '{selector}': {e}")

        if "Target closed" in str(e) or "Timeout" in str(e):

             raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Failed to fill field (selector: {selector}): {str(e)}", id=rpc_id)

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to fill form field (selector: {selector}): {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_get_element_text(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    selector = params.get("selector")

    if not selector or not isinstance(selector, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'selector' parameter is required and must be a string.", id=rpc_id)

    

    timeout = params.get("timeout", _config_loader.get_service_config().get("default_timeout"))

    page = await _get_active_page_or_raise()

    try:

        logger.info(f"Getting text from element '{selector}' with timeout {timeout}ms")

        element = await page.wait_for_selector(selector, timeout=float(timeout))

        if not element:

            raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Element with selector '{selector}' not found.", id=rpc_id)

        text_content = await element.text_content()

        logger.info(f"Got text from element '{selector}': '{text_content}'")

        return {"status": "success", "text": text_content}

    except Exception as e:

        logger.error(f"Failed to get text from element '{selector}': {e}")

        if "Target closed" in str(e) or "Timeout" in str(e):

             raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Failed to get text (selector: {selector}): {str(e)}", id=rpc_id)

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to get text from element (selector: {selector}): {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_execute_javascript(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    script = params.get("script")

    if not script or not isinstance(script, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'script' parameter is required and must be a string.", id=rpc_id)

    

    args = params.get("args") # This will be passed as a single argument to the JS function if it's a complex object/array



    page = await _get_active_page_or_raise()

    try:

        logger.info(f"Executing JavaScript: '{script}' with args: {args}")

        # Playwright's evaluate takes the script (as a JS function body or expression) and an optional arg

        # If `args` is a list, it can be spread into the JS function if the function is defined like `(arg1, arg2) => ...`

        # If `args` is a dict or a single value, it's passed as the first argument to the JS function.

        # For simplicity, we'll pass `args` as a single argument. The JS script needs to expect this.

        # Example JS: "(myArg) => { console.log(myArg); return myArg.someValue; }"

        result = await page.evaluate(script, args)

        logger.info(f"JavaScript execution completed. Result: {result}")

        return {"status": "success", "result": result}

    except Exception as e:

        logger.error(f"JavaScript execution failed: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"JavaScript execution failed: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_create_context(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    if not _browser_manager:

        raise RPCException(code=BROWSER_OPERATION_ERROR, message="Browser manager not initialized.", id=rpc_id)

    context_options = params.get("context_options", {})

    if not isinstance(context_options, dict):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'context_options' must be an object.", id=rpc_id)

    try:

        context_id = await _browser_manager.create_context(context_options=context_options)

        logger.info(f"Successfully created new browser context with ID: {context_id}")

        return {"status": "success", "context_id": context_id}

    except Exception as e:

        logger.error(f"Failed to create browser context: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to create context: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_switch_context(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    context_id = params.get("context_id")

    if not context_id or not isinstance(context_id, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'context_id' parameter is required and must be a string.", id=rpc_id)

    if not _browser_manager:

        raise RPCException(code=BROWSER_OPERATION_ERROR, message="Browser manager not initialized.", id=rpc_id)

    try:

        success = _browser_manager.set_active_context(context_id)

        if success:

            logger.info(f"Successfully switched to context ID: {context_id}")

            return {"status": "success", "active_context_id": _browser_manager._active_context_id, "active_page_id": _browser_manager._active_page_id}

        else:

            raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to switch to context ID '{context_id}'. Context not found.", id=rpc_id)

    except Exception as e:

        logger.error(f"Failed to switch browser context: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to switch context: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_close_context(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    context_id = params.get("context_id")

    if not context_id or not isinstance(context_id, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'context_id' parameter is required and must be a string.", id=rpc_id)

    if not _browser_manager:

        raise RPCException(code=BROWSER_OPERATION_ERROR, message="Browser manager not initialized.", id=rpc_id)

    try:

        success = await _browser_manager.close_context(context_id)

        if success:

            logger.info(f"Successfully closed context ID: {context_id}")

            return {"status": "success", "closed_context_id": context_id}

        else:

            raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to close context ID '{context_id}'. Context not found or already closed.", id=rpc_id)

    except Exception as e:

        logger.error(f"Failed to close browser context: {e}")

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to close context: {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_get_element_attribute(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    selector = params.get("selector")

    attribute_name = params.get("attribute_name")

    if not selector or not isinstance(selector, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'selector' parameter is required and must be a string.", id=rpc_id)

    if not attribute_name or not isinstance(attribute_name, str):

        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="'attribute_name' parameter is required and must be a string.", id=rpc_id)



    timeout = params.get("timeout", _config_loader.get_service_config().get("default_timeout"))

    page = await _get_active_page_or_raise()

    try:

        logger.info(f"Getting attribute '{attribute_name}' from element '{selector}' with timeout {timeout}ms")

        element = await page.wait_for_selector(selector, timeout=float(timeout))

        if not element:

            raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Element with selector '{selector}' not found.", id=rpc_id)

        attribute_value = await element.get_attribute(attribute_name)

        logger.info(f"Got attribute '{attribute_name}' from element '{selector}': '{attribute_value}'")

        return {"status": "success", "value": attribute_value}

    except Exception as e:

        logger.error(f"Failed to get attribute from element '{selector}': {e}")

        if "Target closed" in str(e) or "Timeout" in str(e):

             raise RPCException(code=ELEMENT_NOT_FOUND_ERROR, message=f"Failed to get attribute (selector: {selector}): {str(e)}", id=rpc_id)

        raise RPCException(code=BROWSER_OPERATION_ERROR, message=f"Failed to get attribute from element (selector: {selector}): {str(e)}", id=rpc_id)



@api_method_handler

async def puppeteer_get_console_logs(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):

    # This is a placeholder. Playwright captures console messages via an event listener.

    # A robust implementation would collect these in BrowserManager or on a per-page basis.

    # For now, this will return an empty list or a note about its current limitation.

    # To implement properly: in BrowserManager, on page.on('console', handler), store messages.

    # Then this API would retrieve those stored messages.

    logger.warning("puppeteer_get_console_logs is a placeholder and does not currently retrieve live logs.")

    return {"status": "success", "logs": [], "message": "Log retrieval is not fully implemented yet. Console messages should be monitored via Playwright's event system."}


