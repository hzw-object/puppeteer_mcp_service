# Puppeteer MCP (Model Context Protocol) Service

## 1. Introduction

The Puppeteer MCP Service is a powerful browser automation server designed to enable Large Language Models (LLMs) and other programmatic clients to interact with web pages in a real browser environment. Built with Python using the Playwright library, it provides a robust set of tools for navigation, content extraction, element interaction, screenshotting, and JavaScript execution. Communication with the service is handled via the JSON-RPC 2.0 protocol over HTTP, making it easy to integrate with various client applications.

This service aims to bridge the gap between language models and the dynamic web, allowing for sophisticated web scraping, automated testing, data collection, and other tasks requiring browser interaction. It is designed to be configurable and extensible, providing a solid foundation for complex browser automation workflows.

## 2. Key Features

- **Comprehensive Browser Automation**: Leverages Playwright to control modern web browsers (Chromium by default, configurable for Firefox and WebKit).
- **JSON-RPC 2.0 Interface**: Standardized and straightforward API interaction using JSON-RPC over HTTP.
- **Page Navigation and Interaction**: Navigate to URLs, click elements, fill forms, and retrieve page content.
- **Rich Content Extraction**: Get page titles, current URLs, full HTML content, and text from specific elements.
- **Screenshot Capabilities**: Capture full-page or element-specific screenshots in various formats (PNG, JPEG) with quality and path customization.
- **JavaScript Execution**: Execute arbitrary JavaScript code within the context of the current page and retrieve results.
- **Browser Context Management**: Create, switch between, and close isolated browser contexts for managing sessions, cookies, and storage independently. This is a key feature for handling multiple independent tasks or user sessions.
- **Configurable Behavior**: Customize browser launch options, default timeouts, user agents, and viewport sizes through a `config.json` file.
- **Error Handling**: Clear and structured JSON-RPC error responses for easier debugging.
- **Health Check Endpoint**: A simple `/health` endpoint to monitor service and browser status.
- **Placeholder for Console Log Monitoring**: While the API endpoint `puppeteer.get_console_logs` exists, it currently serves as a placeholder. Full console log retrieval would typically involve event listeners within the browser management layer to collect messages as they occur.

## 3. Getting Started

### 3.1. Prerequisites

- Python 3.8+ (Python 3.11 recommended, as used in the development environment).
- `pip` for installing Python packages.
- Playwright browser drivers. The service will attempt to install the Chromium driver on first run if not found, but manual installation might be required in some environments:
  ```bash
  playwright install chromium
  ```

### 3.2. Installation

1.  Ensure all project files are in a directory (e.g., `/home/ubuntu/puppeteer_mcp_service`).
2.  Install the required Python dependencies:
    ```bash
    pip3 install -r /home/ubuntu/puppeteer_mcp_service/requirements.txt
    ```
    The `requirements.txt` file should contain:
    ```
    fastapi
    uvicorn[standard]
    playwright
    # Add other dependencies if any were introduced
    ```

### 3.3. Configuration

The service is configured using a `config.json` file located in the project root directory (`/home/ubuntu/puppeteer_mcp_service/config.json`).

**Default `config.json`:**
```json
{
    "browser_type": "chromium",
    "headless": true,
    "slow_mo": 0,
    "default_timeout": 30000,
    "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/99.0.4844.51 Safari/537.36",
    "viewport": {
        "width": 1280,
        "height": 720
    },
    "service_host": "0.0.0.0",
    "service_port": 8080,
    "log_level": "INFO",
    "playwright_browser_args": [] 
}
```

**Configuration Options:**

-   `browser_type` (string): The browser to use. Supported values: "chromium", "firefox", "webkit". Default: "chromium".
-   `headless` (boolean): Whether to run the browser in headless mode. Default: `true`.
-   `slow_mo` (integer): Slows down Playwright operations by the specified amount in milliseconds. Useful for debugging. Default: `0`.
-   `default_timeout` (integer): Default timeout in milliseconds for Playwright operations (e.g., navigation, waiting for selectors). Default: `30000` (30 seconds).
-   `user_agent` (string): Default user agent string for new browser contexts. Default: A common Chrome user agent.
-   `viewport` (object): Default viewport size for new pages.
    -   `width` (integer): Viewport width in pixels. Default: `1280`.
    -   `height` (integer): Viewport height in pixels. Default: `720`.
-   `service_host` (string): Host address for the MCP service to listen on. Default: "0.0.0.0".
-   `service_port` (integer): Port for the MCP service to listen on. Default: `8080`.
-   `log_level` (string): Logging level for the service. Supported values: "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL". Default: "INFO".
-   `playwright_browser_args` (array of strings): Additional arguments to pass to the browser instance on launch (e.g., `["--disable-gpu"]`). Default: `[]`.

### 3.4. Running the Service

Navigate to the project root directory (`/home/ubuntu/puppeteer_mcp_service`) and run the service using Uvicorn:

```bash
export PYTHONPATH=/home/ubuntu/puppeteer_mcp_service:$PYTHONPATH
/home/ubuntu/.local/bin/uvicorn main:app --host 0.0.0.0 --port 8080
```

Or, if Uvicorn is in your system path:

```bash
export PYTHONPATH=/home/ubuntu/puppeteer_mcp_service:$PYTHONPATH
uvicorn main:app --host 0.0.0.0 --port 8080
```

The service will be available at `http://0.0.0.0:8080`. The JSON-RPC endpoint is `http://0.0.0.0:8080/jsonrpc`.

## 4. API Endpoints (JSON-RPC Methods)

All API methods are invoked by sending a POST request to the `/jsonrpc` endpoint (e.g., `https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc` or `http://localhost:8080/jsonrpc`). The request body must be a JSON-RPC 2.0 object.

**Common Request Structure:**
```json
{
  "jsonrpc": "2.0",
  "method": "puppeteer.method_name",
  "params": { /* method-specific parameters */ },
  "id": "your-request-id"
}
```

**Common Success Response Structure:**
```json
{
  "jsonrpc": "2.0",
  "result": { /* method-specific result */ },
  "id": "your-request-id"
}
```

**Common Error Response Structure:**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32xxx, /* error code */
    "message": "Error description"
  },
  "id": "your-request-id"
}
```

### 4.1. `puppeteer.navigate`

Navigates the active page to the specified URL.

-   **Parameters**:
    -   `url` (string, required): The URL to navigate to.
    -   `timeout` (integer, optional): Navigation timeout in milliseconds. Defaults to `default_timeout` from `config.json`.
    -   `wait_until` (string, optional): When to consider navigation successful. Options: "load", "domcontentloaded", "networkidle", "commit". Default: "load".
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.navigate", "params": {"url": "http://example.com"}, "id": "nav1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "url": "http://example.com/",
        "http_status": 200
      },
      "id": "nav1"
    }
    ```

### 4.2. `puppeteer.get_current_url`

Retrieves the URL of the active page.

-   **Parameters**: None (empty object `{}` or omit `params`).
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.get_current_url", "params": {}, "id": "geturl1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response** (after navigating to example.com):
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "url": "http://example.com/"
      },
      "id": "geturl1"
    }
    ```

### 4.3. `puppeteer.get_page_title`

Retrieves the title of the active page.

-   **Parameters**: None.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.get_page_title", "params": {}, "id": "gettitle1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response** (after navigating to example.com):
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "title": "Example Domain"
      },
      "id": "gettitle1"
    }
    ```

### 4.4. `puppeteer.take_page_screenshot`

Captures a screenshot of the active page.

-   **Parameters**:
    -   `path` (string, optional): Absolute path to save the screenshot. If not provided, the image is returned as a base64 encoded string.
    -   `full_page` (boolean, optional): Whether to capture the full scrollable page. Default: `true`.
    -   `type` (string, optional): Screenshot type. "png" or "jpeg". Default: "png".
    -   `quality` (integer, optional): Quality for JPEG screenshots (0-100). Default: Not set.
    -   `omit_background` (boolean, optional): Hides default white background for PNGs, allowing capture of transparent websites. Default: `false`.
-   **Example Request (Save to File)**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.take_page_screenshot", "params": {"path": "/home/ubuntu/puppeteer_mcp_service/example.png"}, "id": "screenfile1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response (Save to File)**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "file_path": "/home/ubuntu/puppeteer_mcp_service/example.png"
      },
      "id": "screenfile1"
    }
    ```
-   **Example Request (Base64)**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.take_page_screenshot", "params": {"type": "jpeg", "quality": 80}, "id": "screenbase64"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response (Base64)**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "image_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD/... (long base64 string) ..."
      },
      "id": "screenbase64"
    }
    ```

### 4.5. `puppeteer.get_page_content`

Retrieves the full HTML content of the active page.

-   **Parameters**: None.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.get_page_content", "params": {}, "id": "getcontent1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "content": "<!doctype html><html><head>...</body></html>"
      },
      "id": "getcontent1"
    }
    ```

### 4.6. `puppeteer.click_element`

Clicks an element specified by a CSS selector.

-   **Parameters**:
    -   `selector` (string, required): CSS selector for the target element.
    -   `timeout` (integer, optional): Timeout in milliseconds to wait for the element. Defaults to `default_timeout`.
    -   `button` (string, optional): Mouse button to use ("left", "middle", "right"). Default: "left".
    -   `click_count` (integer, optional): Number of times to click. Default: `1`.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.click_element", "params": {"selector": "a[href=\"https://www.iana.org/domains/example\"]"}, "id": "click1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success"
      },
      "id": "click1"
    }
    ```

### 4.7. `puppeteer.fill_form_field`

Fills a form field (input, textarea) with the specified value.

-   **Parameters**:
    -   `selector` (string, required): CSS selector for the target form field.
    -   `value` (string, required): The value to fill into the field.
    -   `timeout` (integer, optional): Timeout in milliseconds. Defaults to `default_timeout`.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.fill_form_field", "params": {"selector": "#searchInput", "value": "Playwright"}, "id": "fill1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success"
      },
      "id": "fill1"
    }
    ```

### 4.8. `puppeteer.get_element_text`

Retrieves the text content of an element specified by a CSS selector.

-   **Parameters**:
    -   `selector` (string, required): CSS selector for the target element.
    -   `timeout` (integer, optional): Timeout in milliseconds. Defaults to `default_timeout`.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.get_element_text", "params": {"selector": "h1"}, "id": "gettext1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response** (on example.com):
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "text": "Example Domain"
      },
      "id": "gettext1"
    }
    ```

### 4.9. `puppeteer.get_element_attribute`

Retrieves the value of a specified attribute from an element.

-   **Parameters**:
    -   `selector` (string, required): CSS selector for the target element.
    -   `attribute_name` (string, required): The name of the attribute to retrieve (e.g., "href", "src", "value").
    -   `timeout` (integer, optional): Timeout in milliseconds. Defaults to `default_timeout`.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.get_element_attribute", "params": {"selector": "a", "attribute_name": "href"}, "id": "getattr1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response** (on example.com, for the first link):
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "value": "https://www.iana.org/domains/example"
      },
      "id": "getattr1"
    }
    ```

### 4.10. `puppeteer.execute_javascript`

Executes a JavaScript function or expression in the context of the active page.

-   **Parameters**:
    -   `script` (string, required): The JavaScript code to execute. This should be a string representing a function body or an expression. Example: `"() => document.title"` or `"document.querySelector('h1').innerText"`.
    -   `args` (any, optional): An argument to pass to the JavaScript function. If the script is a function, `args` will be passed as its argument. Playwright handles serialization.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.execute_javascript", "params": {"script": "() => ({ title: document.title, url: window.location.href })"}, "id": "execjs1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "result": {
          "title": "Example Domain",
          "url": "http://example.com/"
        }
      },
      "id": "execjs1"
    }
    ```

### 4.11. `puppeteer.create_context`

Creates a new isolated browser context.

-   **Parameters**:
    -   `context_options` (object, optional): Playwright browser context options (e.g., `user_agent`, `viewport`, `storage_state`). See Playwright documentation for available options.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.create_context", "params": {"context_options": {"user_agent": "MyCustomAgent/1.0"}}, "id": "createctx1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "context_id": "context_abc123xyz"
      },
      "id": "createctx1"
    }
    ```

### 4.12. `puppeteer.switch_context`

Switches the active browser context.

-   **Parameters**:
    -   `context_id` (string, required): The ID of the context to switch to (obtained from `puppeteer.create_context` or the initial default context ID).
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.switch_context", "params": {"context_id": "context_abc123xyz"}, "id": "switchctx1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "active_context_id": "context_abc123xyz",
        "active_page_id": "page_for_context_abc123xyz_1" /* Example page ID */
      },
      "id": "switchctx1"
    }
    ```

### 4.13. `puppeteer.close_context`

Closes a browser context and all its pages.

-   **Parameters**:
    -   `context_id` (string, required): The ID of the context to close.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.close_context", "params": {"context_id": "context_abc123xyz"}, "id": "closectx1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "closed_context_id": "context_abc123xyz"
      },
      "id": "closectx1"
    }
    ```

### 4.14. `puppeteer.get_console_logs`

**Note**: This method is currently a placeholder.
Retrieves console log messages from the browser. A full implementation would require collecting these messages via event listeners in the `BrowserManager`.

-   **Parameters**: None.
-   **Example Request**:
    ```bash
    curl -X POST -H "Content-Type: application/json" \
    -d '{"jsonrpc": "2.0", "method": "puppeteer.get_console_logs", "params": {}, "id": "getlogs1"}' \
    https://8080-i0k0tkcmavbj2c6d8nvoz-8c2b5b50.manus.computer/jsonrpc
    ```
-   **Example Success Response (Current Placeholder)**:
    ```json
    {
      "jsonrpc": "2.0",
      "result": {
        "status": "success",
        "logs": [],
        "message": "Log retrieval is not fully implemented yet. Console messages should be monitored via Playwright's event system."
      },
      "id": "getlogs1"
    }
    ```

## 5. Error Handling

The service uses standard JSON-RPC 2.0 error objects. Common error codes include:

-   `-32700`: **Parse error**. Invalid JSON was received by the server.
-   `-32600`: **Invalid Request**. The JSON sent is not a valid Request object.
-   `-32601`: **Method not found**. The method does not exist / is not available.
-   `-32602`: **Invalid params**. Invalid method parameter(s).
-   `-32603`: **Internal error**. Internal JSON-RPC error.
-   `-32000`: **Browser Operation Error**. Generic error during a browser operation (e.g., navigation failure, screenshot failure).
-   `-32001`: **Page Not Available Error**. No active page is available, or creation of a new page failed.
-   `-32002`: **Element Not Found Error**. A specified element could not be found on the page within the timeout.
-   `-32003`: **Configuration Error**. Problem with service or browser configuration.

**Example Error Response:**
```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params: 'url' parameter is required and must be a string."
  },
  "id": "nav_error_1"
}
```

## 6. Health Check

A simple HTTP GET endpoint is available at `/health` for monitoring the service status.

-   **Endpoint**: `GET /health` (e.g., `http://localhost:8080/health`)
-   **Success Response (Browser Connected)**:
    ```json
    {
      "status": "ok",
      "browser_status": "connected"
    }
    ```
-   **Success Response (Browser Disconnected/Degraded)**:
    ```json
    {
      "status": "degraded",
      "browser_status": "disconnected"
    }
    ```
-   **Error Response (Browser Unavailable)**:
    ```json
    {
      "status": "error",
      "browser_status": "unavailable_or_failed_to_start"
    }
    ```

## 7. Deployment Notes

-   The service is currently designed to be run directly using Uvicorn.
-   For production deployments, consider running Uvicorn behind a reverse proxy like Nginx or using a process manager like Supervisor or systemd to ensure reliability and manage logging.
-   Ensure the environment has sufficient resources (CPU, memory) for running browser instances, especially if handling concurrent requests or multiple contexts.
-   The `playwright install` command might need to be run in the deployment environment to ensure browser binaries are available.

This concludes the initial documentation for the Puppeteer MCP Service.

