from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
import logging
import asyncio

from app.config_loader import ConfigLoader
from app.browser_manager import BrowserManager
from app.utils import (
    create_jsonrpc_error, RPCException, JSON_RPC_INVALID_REQUEST, 
    JSON_RPC_METHOD_NOT_FOUND, JSON_RPC_PARSE_ERROR, api_method_handler, get_params,
    JSON_RPC_INTERNAL_ERROR
)
from app import routes

logger = logging.getLogger(__name__)

config_loader: ConfigLoader
browser_manager: BrowserManager

app = FastAPI(
    title="Puppeteer MCP Service",
    description="A Model Context Protocol server for browser automation using Playwright.",
    version="0.1.0"
)

@app.on_event("startup")
async def startup_event():
    global config_loader, browser_manager
    try:
        config_loader = ConfigLoader()
        service_config = config_loader.get_service_config()
        logging.basicConfig(level=service_config.get("log_level", "INFO"), 
                            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        logger.info("Configuration loaded.")
        
        browser_manager = BrowserManager(config_loader)
        logger.info("BrowserManager initialized. Starting browser...")
        await browser_manager.start_browser()
        logger.info("Browser started successfully during application startup.")
        routes.initialize_routes(browser_manager, config_loader)
    except Exception as e:
        logger.error(f"Critical error during application startup: {e}", exc_info=True)
        # Consider raising e to stop FastAPI if browser init is critical

@app.on_event("shutdown")
async def shutdown_event():
    global browser_manager
    if browser_manager:
        logger.info("Application shutting down. Closing browser...")
        await browser_manager.close_browser()
        logger.info("Browser closed successfully.")

@app.post("/jsonrpc", tags=["JSON-RPC"])
async def jsonrpc_handler(request: Request):
    request_data: dict
    try:
        request_data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON request body: {e}")
        return JSONResponse(content=create_jsonrpc_error(id=None, code=JSON_RPC_PARSE_ERROR, message="Parse error"))

    rpc_id = request_data.get("id")
    if not isinstance(request_data, dict) or \
       request_data.get("jsonrpc") != "2.0" or \
       "method" not in request_data:
        return JSONResponse(content=create_jsonrpc_error(id=rpc_id, code=JSON_RPC_INVALID_REQUEST, message="Invalid Request"))

    method_name = request_data["method"]
    api_function_name = method_name.replace(".", "_")
    
    if not hasattr(routes, api_function_name):
        logger.warning(f"Method not found: {method_name} (mapped to {api_function_name})")
        return JSONResponse(content=create_jsonrpc_error(id=rpc_id, code=JSON_RPC_METHOD_NOT_FOUND, message="Method not found"))

    api_function = getattr(routes, api_function_name)
    logger.info(f"Attempting to call: {api_function_name}")
    logger.info(f"Type of api_function: {type(api_function)}")
    logger.info(f"Is api_function a coroutine object: {asyncio.iscoroutine(api_function)}")
    logger.info(f"Is api_function a coroutine function: {asyncio.iscoroutinefunction(api_function)}")

    try:
        params = await get_params(request_data) # Can raise RPCException
        # api_function is the decorated wrapper, which now returns a dict
        response_dict = await api_function(params, rpc_id)
        return JSONResponse(content=response_dict)
    except RPCException as e:
        # This catches RPCException from get_params or if api_function itself re-raises one (though it shouldn't if handled by decorator)
        e.id = rpc_id # Ensure ID is set if not already
        logger.error(f"RPCException in handler for {method_name}: Code {e.code}, Msg: {e.message}", exc_info=True)
        return e.to_json_response() # RPCException.to_json_response() returns a JSONResponse object
    except Exception as e:
        logger.error(f"Unexpected error handling method {method_name}: {e}", exc_info=True)
        return JSONResponse(content=create_jsonrpc_error(id=rpc_id, code=JSON_RPC_INTERNAL_ERROR, message=f"Server error: {str(e)}"))

@app.get("/health", tags=["Management"])
async def health_check():
    if browser_manager and browser_manager.browser and browser_manager.browser.is_connected():
        return {"status": "ok", "browser_status": "connected"}
    elif browser_manager and browser_manager.browser:
        return {"status": "degraded", "browser_status": "disconnected"}
    return {"status": "error", "browser_status": "unavailable_or_failed_to_start"}

