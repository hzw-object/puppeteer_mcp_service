from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import logging
import traceback
from typing import Any, Dict, Optional, Union, List
from functools import wraps

# JSON-RPC Error Codes
JSON_RPC_PARSE_ERROR = -32700
JSON_RPC_INVALID_REQUEST = -32600
JSON_RPC_METHOD_NOT_FOUND = -32601
JSON_RPC_INVALID_PARAMS = -32602
JSON_RPC_INTERNAL_ERROR = -32603
# Application specific errors
BROWSER_OPERATION_ERROR = -32000
PAGE_NOT_AVAILABLE_ERROR = -32001
ELEMENT_NOT_FOUND_ERROR = -32002
CONFIG_ERROR = -32003

logger = logging.getLogger(__name__)

def create_jsonrpc_error(id: Optional[Union[str, int]], code: int, message: str, data: Optional[Any] = None) -> Dict[str, Any]:
    error_obj = {"code": code, "message": message}
    if data is not None:
        error_obj["data"] = data
    return {"jsonrpc": "2.0", "error": error_obj, "id": id}

def create_jsonrpc_success(id: Optional[Union[str, int]], result: Any) -> Dict[str, Any]:
    return {"jsonrpc": "2.0", "result": result, "id": id}

class RPCException(Exception):
    def __init__(self, code: int, message: str, id: Optional[Union[str, int]] = None, data: Optional[Any] = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.id = id
        self.data = data

    def to_json_response(self) -> JSONResponse:
        return JSONResponse(content=create_jsonrpc_error(self.id, self.code, self.message, self.data))

async def get_params(request_data: Dict[str, Any]) -> Union[Dict[str, Any], List[Any]]:
    params = request_data.get("params")
    if params is None:
        return {}
    if not isinstance(params, (dict, list)):
        # Ensure rpc_id is passed to RPCException if available from request_data
        rpc_id = request_data.get("id")
        raise RPCException(code=JSON_RPC_INVALID_PARAMS, message="Invalid params: Must be object or array.", id=rpc_id)
    return params

# Decorator for API methods
def api_method_handler(func_to_be_wrapped):
    @wraps(func_to_be_wrapped)
    async def wrapper_function(params: Union[Dict[str, Any], List[Any]], rpc_id: Optional[Union[str, int]]):
        try:
            # The original API methods in routes.py are defined as:
            # async def some_api_method(params: Dict[str, Any], rpc_id: Optional[Union[str, int]]):
            # So, they are called with (params, rpc_id)
            result = await func_to_be_wrapped(params, rpc_id)
            return create_jsonrpc_success(id=rpc_id, result=result) # Returns a dict
        except RPCException as e:
            # This RPCException was raised by func_to_be_wrapped or by param validation within it.
            # Ensure the original rpc_id is used if the exception didn't capture it or overwrote it.
            current_rpc_id = rpc_id if e.id is None else e.id
            logger.error(f"RPCException in {func_to_be_wrapped.__name__}: {e.message} (Code: {e.code}) - ID: {current_rpc_id} - Data: {e.data}")
            return create_jsonrpc_error(id=current_rpc_id, code=e.code, message=e.message, data=e.data) # Returns a dict
        except Exception as e:
            logger.error(f"Unhandled exception in API method {func_to_be_wrapped.__name__}: {e} - ID: {rpc_id}")
            logger.error(traceback.format_exc())
            return create_jsonrpc_error(id=rpc_id, code=JSON_RPC_INTERNAL_ERROR, message=f"Internal server error: {str(e)}") # Returns a dict
    
    return wrapper_function # Crucially, return the async wrapper FUNCTION, not an invocation of it.

