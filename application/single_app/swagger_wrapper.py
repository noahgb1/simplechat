# swagger_wrapper.py

"""
Swagger Route Wrapper System

This module provides decorators and utilities to automatically generate Swagger/OpenAPI
documentation for Flask routes. Routes decorated with @swagger_route will be automatically
included in the /swagger endpoint.

Usage:
    from swagger_wrapper import swagger_route, register_swagger_routes
    
    # Register the swagger routes in your app
    register_swagger_routes(app)
    
    # Use the decorator on your routes
    @app.route('/api/example', methods=['POST'])
    @swagger_route(
        summary="Example API endpoint",
        description="This is an example API endpoint that demonstrates the swagger wrapper",
        tags=["Examples"],
        request_body={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "User name"},
                "age": {"type": "integer", "description": "User age"}
            },
            "required": ["name"]
        },
        responses={
            200: {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            },
            400: {"description": "Bad request"}
        }
    )
    def example_endpoint():
        return jsonify({"success": True, "message": "Hello World"})
"""

from flask import Flask, jsonify, render_template_string
from functools import wraps
from typing import Dict, List, Optional, Any, Union
import json
import re
import inspect
import ast
from datetime import datetime

# Global registry to store route documentation
_swagger_registry: Dict[str, Dict[str, Any]] = {}

def _analyze_function_returns(func) -> Dict[str, Any]:
    """
    Analyze a function's return statements to generate response schemas.
    
    Args:
        func: Function to analyze
        
    Returns:
        Dictionary of response schemas by status code
    """
    try:
        # Get the source code
        source = inspect.getsource(func)
        
        # Remove leading indentation to avoid parse errors
        import textwrap
        source = textwrap.dedent(source)
        
        tree = ast.parse(source)
        
        responses = {}
        
        class ReturnVisitor(ast.NodeVisitor):
            def visit_Return(self, node):
                if isinstance(node.value, ast.Call):
                    # Handle jsonify() calls
                    if (isinstance(node.value.func, ast.Name) and 
                        node.value.func.id == 'jsonify'):
                        
                        # Try to extract the structure from jsonify argument
                        if node.value.args:
                            arg = node.value.args[0]
                            schema = _ast_to_schema(arg)
                            if schema:
                                responses["200"] = {
                                    "description": "Success",
                                    "content": {
                                        "application/json": {
                                            "schema": schema
                                        }
                                    }
                                }
                
                # Handle tuple returns like (jsonify(...), 400)
                elif isinstance(node.value, ast.Tuple) and len(node.value.elts) == 2:
                    json_part, status_part = node.value.elts
                    
                    # Extract status code
                    status_code = 500  # default
                    if isinstance(status_part, ast.Constant) and isinstance(status_part.value, int):
                        status_code = status_part.value
                    elif isinstance(status_part, ast.Num):  # Python < 3.8 compatibility
                        status_code = status_part.n
                    
                    # Extract schema from jsonify call
                    if (isinstance(json_part, ast.Call) and
                        isinstance(json_part.func, ast.Name) and
                        json_part.func.id == 'jsonify' and
                        json_part.args):
                        
                        schema = _ast_to_schema(json_part.args[0])
                        if schema:
                            description = "Success" if status_code == 200 else "Error"
                            if isinstance(status_code, int) and status_code >= 400:
                                description = _get_error_description(status_code)
                            
                            responses[str(status_code)] = {
                                "description": description,
                                "content": {
                                    "application/json": {
                                        "schema": schema
                                    }
                                }
                            }
                
                self.generic_visit(node)
        
        visitor = ReturnVisitor()
        visitor.visit(tree)
        
        # Add default responses if none found
        if not responses:
            responses["200"] = {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            }
        
        return responses
        
    except Exception as e:
        # Fallback to default responses if analysis fails
        return {
            "200": {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            }
        }

def _ast_to_schema(node) -> Optional[Dict[str, Any]]:
    """
    Convert an AST node to a JSON schema.
    
    Args:
        node: AST node to convert
        
    Returns:
        JSON schema dictionary or None
    """
    if isinstance(node, ast.Dict):
        # Handle dictionary literals
        properties = {}
        
        for key_node, value_node in zip(node.keys, node.values):
            if isinstance(key_node, ast.Constant) and isinstance(key_node.value, str):
                key = key_node.value
                prop_schema = _ast_to_schema(value_node)
                if prop_schema:
                    properties[key] = prop_schema
            elif isinstance(key_node, ast.Str):  # Python < 3.8 compatibility
                key = key_node.s
                prop_schema = _ast_to_schema(value_node)
                if prop_schema:
                    properties[key] = prop_schema
        
        if properties:
            return {
                "type": "object",
                "properties": properties
            }
    
    elif isinstance(node, ast.List):
        # Handle list literals
        if node.elts:
            # Try to infer item schema from first element
            item_schema = _ast_to_schema(node.elts[0])
            if item_schema:
                return {
                    "type": "array",
                    "items": item_schema
                }
        return {"type": "array"}
    
    elif isinstance(node, ast.Constant):
        # Handle constant values
        value = node.value
        if isinstance(value, str):
            return {"type": "string", "example": value}
        elif isinstance(value, int):
            return {"type": "integer", "example": value}
        elif isinstance(value, float):
            return {"type": "number", "example": value}
        elif isinstance(value, bool):
            return {"type": "boolean", "example": value}
    
    elif isinstance(node, (ast.Str, ast.Num, ast.NameConstant)):  # Python < 3.8 compatibility
        if isinstance(node, ast.Str):
            return {"type": "string", "example": node.s}
        elif isinstance(node, ast.Num):
            if isinstance(node.n, int):
                return {"type": "integer", "example": node.n}
            else:
                return {"type": "number", "example": node.n}
        elif isinstance(node, ast.NameConstant):
            if isinstance(node.value, bool):
                return {"type": "boolean", "example": node.value}
    
    # Default fallback
    return {"type": "object"}

def _get_error_description(status_code: int) -> str:
    """Get description for HTTP error status codes."""
    descriptions = {
        400: "Bad Request",
        401: "Unauthorized", 
        403: "Forbidden",
        404: "Not Found",
        500: "Internal Server Error",
        502: "Bad Gateway",
        503: "Service Unavailable"
    }
    return descriptions.get(status_code, "Error")

def _analyze_function_parameters(func) -> List[Dict[str, Any]]:
    """
    Analyze function parameters to generate parameter documentation.
    
    Args:
        func: Function to analyze
        
    Returns:
        List of parameter definitions
    """
    try:
        sig = inspect.signature(func)
        parameters = []
        
        for param_name, param in sig.parameters.items():
            # Skip common Flask route parameters
            if param_name in ['args', 'kwargs']:
                continue
                
            param_def = {
                "name": param_name,
                "in": "path",  # Assume path parameters for now
                "required": param.default == inspect.Parameter.empty,
                "description": f"Parameter: {param_name}",
                "schema": {"type": "string"}
            }
            
            # Try to infer type from annotation
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == str:
                    param_def["schema"] = {"type": "string"}
                elif param.annotation == int:
                    param_def["schema"] = {"type": "integer"}
                elif param.annotation == float:
                    param_def["schema"] = {"type": "number"}
                elif param.annotation == bool:
                    param_def["schema"] = {"type": "boolean"}
            
            parameters.append(param_def)
        
        return parameters
        
    except Exception:
        return []

def _generate_summary_from_function_name(func_name: str) -> str:
    """
    Generate a human-readable summary from function name.
    
    Args:
        func_name: Function name (e.g., 'get_user_profile')
        
    Returns:
        Human-readable summary (e.g., 'Get User Profile')
    """
    # Convert snake_case to Title Case
    words = func_name.replace('_', ' ').split()
    return ' '.join(word.capitalize() for word in words)

def _extract_tags_from_route_path(route_path: str) -> List[str]:
    """
    Extract tags from route path segments.
    
    Args:
        route_path: Flask route path (e.g., '/api/users/<int:user_id>')
        
    Returns:
        List of tags extracted from path segments
    """
    if not route_path or route_path == '/':
        return []
    
    # Split path into segments and filter out empty, parameter, and common segments
    segments = [seg for seg in route_path.split('/') if seg]
    
    # Remove common API prefixes and parameter segments
    filtered_segments = []
    skip_segments = {'api', 'v1', 'v2', 'v3'}
    
    for segment in segments:
        # Skip parameter segments like <int:user_id>, <user_id>
        if segment.startswith('<') and segment.endswith('>'):
            continue
        # Skip common API prefixes
        if segment.lower() in skip_segments:
            continue
        # Take meaningful segments
        filtered_segments.append(segment.capitalize())
    
    return filtered_segments

def swagger_route(
    summary: str = "",
    description: str = "",
    tags: Optional[List[str]] = None,
    request_body: Optional[Dict[str, Any]] = None,
    responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
    parameters: Optional[List[Dict[str, Any]]] = None,
    deprecated: bool = False,
    security: Optional[List[Dict[str, List[str]]]] = None,
    auto_schema: bool = True,
    auto_summary: bool = True,
    auto_description: bool = True,
    auto_tags: bool = True
):
    """
    Decorator to add Swagger/OpenAPI documentation to Flask routes.
    
    Args:
        summary: Brief summary of the endpoint (auto-generated from function name if empty and auto_summary=True)
        description: Detailed description of the endpoint (auto-generated from docstring if empty and auto_description=True)
        tags: List of tags for grouping endpoints (auto-generated from route path if empty and auto_tags=True)
        request_body: OpenAPI request body schema
        responses: Dictionary of response codes and their schemas (auto-generated if None and auto_schema=True)
        parameters: List of parameter definitions (auto-generated if None and auto_schema=True)
        deprecated: Whether the endpoint is deprecated
        security: Security requirements for the endpoint
        auto_schema: Whether to automatically generate schemas from function inspection
        auto_summary: Whether to automatically generate summary from function name
        auto_description: Whether to automatically use function docstring as description
        auto_tags: Whether to automatically generate tags from route path
    
    Returns:
        Decorated function with swagger documentation attached
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        # Auto-generate summary from function name if not provided
        final_summary = summary
        if auto_summary and not summary:
            final_summary = _generate_summary_from_function_name(func.__name__)
        
        # Auto-generate description from function docstring if not provided
        final_description = description
        if auto_description and not description and func.__doc__:
            final_description = func.__doc__.strip()
        
        # Auto-generate responses if not provided
        final_responses = responses
        if auto_schema and not responses:
            final_responses = _analyze_function_returns(func)
        
        # Auto-generate parameters if not provided
        final_parameters = parameters
        if auto_schema and not parameters:
            final_parameters = _analyze_function_parameters(func)
        
        # Store the documentation metadata (tags will be resolved later in extract_route_info)
        setattr(wrapper, '_swagger_doc', {
            'summary': final_summary,
            'description': final_description,
            'tags': tags,  # Keep original tags, will be processed in extract_route_info
            'request_body': request_body,
            'responses': final_responses or {},
            'parameters': final_parameters or [],
            'deprecated': deprecated,
            'security': security or [],
            'auto_tags': auto_tags  # Store the auto_tags setting for later use
        })
        
        return wrapper
    return decorator

def extract_route_info(app: Flask) -> Dict[str, Any]:
    """
    Extract route information from Flask app and generate OpenAPI specification.
    
    Args:
        app: Flask application instance
        
    Returns:
        OpenAPI specification dictionary
    """
    openapi_spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "SimpleChat API",
            "description": "Auto-generated API documentation for SimpleChat application",
            "version": getattr(app.config, 'VERSION', '1.0.0'),
            "contact": {
                "name": "SimpleChat Support"
            }
        },
        "servers": [
            {
                "url": "/",
                "description": "Current server"
            }
        ],
        "paths": {},
        "components": {
            "schemas": {
                "ErrorResponse": {
                    "type": "object",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Error message"
                        }
                    },
                    "required": ["error"]
                }
            },
            "securitySchemes": {
                "bearerAuth": {
                    "type": "http",
                    "scheme": "bearer",
                    "bearerFormat": "JWT"
                },
                "sessionAuth": {
                    "type": "apiKey",
                    "in": "cookie",
                    "name": "session"
                }
            }
        },
        "tags": []
    }
    
    # Extract routes from Flask app
    tags_set = set()
    
    for rule in app.url_map.iter_rules():
        if rule.endpoint == 'static':
            continue
            
        # Get the view function
        view_func = app.view_functions.get(rule.endpoint)
        if not view_func:
            continue
            
        # Check if the function has swagger documentation
        swagger_doc = getattr(view_func, '_swagger_doc', None)
        
        path = rule.rule
        # Convert Flask route parameters to OpenAPI format
        path = re.sub(r'<(?:int:)?(\w+)>', r'{\1}', path)
        path = re.sub(r'<(?:string:)?(\w+)>', r'{\1}', path)
        path = re.sub(r'<(?:float:)?(\w+)>', r'{\1}', path)
        path = re.sub(r'<(?:uuid:)?(\w+)>', r'{\1}', path)
        path = re.sub(r'<(?:path:)?(\w+)>', r'{\1}', path)
        
        if path not in openapi_spec["paths"]:
            openapi_spec["paths"][path] = {}
            
        methods = rule.methods or set()
        for method in methods:
            if method in ['HEAD', 'OPTIONS']:
                continue
                
            method_lower = method.lower()
            
            if swagger_doc:
                # Auto-generate tags from route path if not provided and auto_tags is enabled
                final_tags = swagger_doc.get('tags', [])
                if swagger_doc.get('auto_tags', True) and not final_tags:
                    final_tags = _extract_tags_from_route_path(rule.rule)
                
                # Use provided swagger documentation
                operation = {
                    "summary": swagger_doc.get('summary', f"{method} {path}"),
                    "description": swagger_doc.get('description', ""),
                    "tags": final_tags,
                    "responses": swagger_doc.get('responses', {
                        "200": {"description": "Success"}
                    })
                }
                
                # Add request body if provided
                if swagger_doc.get('request_body'):
                    operation["requestBody"] = {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": swagger_doc['request_body']
                            }
                        }
                    }
                
                # Add parameters if provided
                if swagger_doc.get('parameters'):
                    operation["parameters"] = swagger_doc['parameters']
                
                # Add security if provided
                if swagger_doc.get('security'):
                    operation["security"] = swagger_doc['security']
                
                # Mark as deprecated if specified
                if swagger_doc.get('deprecated'):
                    operation["deprecated"] = True
                
                # Collect tags
                tags_set.update(final_tags)
                
            else:
                # Generate basic documentation
                operation = {
                    "summary": f"{method} {path}",
                    "description": f"Endpoint: {rule.endpoint}",
                    "tags": ["Undocumented"],
                    "responses": {
                        "200": {"description": "Success"}
                    }
                }
                tags_set.add("Undocumented")
            
            openapi_spec["paths"][path][method_lower] = operation
    
    # Generate tags list
    openapi_spec["tags"] = [{"name": tag} for tag in sorted(tags_set)]
    
    return openapi_spec

def register_swagger_routes(app: Flask):
    """
    Register swagger documentation routes.
    
    Args:
        app: Flask application instance
    """
    
    @app.route('/swagger')
    def swagger_ui():
        """Serve Swagger UI for API documentation."""
        swagger_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SimpleChat API Documentation</title>
    <link rel="stylesheet" type="text/css" href="/static/swagger-ui/swagger-ui.css" />
    <style>
        html {
            box-sizing: border-box;
            overflow: -moz-scrollbars-vertical;
            overflow-y: scroll;
        }
        *, *:before, *:after {
            box-sizing: inherit;
        }
        body {
            margin:0;
            background: #fafafa;
        }
        .swagger-ui .topbar {
            background-color: #1976d2;
        }
        .swagger-ui .topbar .download-url-wrapper {
            display: none;
        }
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
    <script src="/static/swagger-ui/swagger-ui-standalone-preset.js"></script>
    <script>
        window.onload = function() {
            const ui = SwaggerUIBundle({
                url: '/swagger.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [
                    SwaggerUIBundle.presets.apis,
                    SwaggerUIStandalonePreset
                ],
                plugins: [
                    SwaggerUIBundle.plugins.DownloadUrl
                ],
                layout: "StandaloneLayout",
                validatorUrl: null,
                docExpansion: "list",
                defaultModelsExpandDepth: 2,
                defaultModelExpandDepth: 2,
                displayRequestDuration: true,
                tryItOutEnabled: true,
                supportedSubmitMethods: ['get', 'post', 'put', 'delete', 'patch', 'head', 'options']
            });
        };
    </script>
</body>
</html>
        """
        return swagger_html
    
    @app.route('/swagger.json')
    def swagger_json():
        """Serve OpenAPI specification as JSON."""
        spec = extract_route_info(app)
        return jsonify(spec)
    
    @app.route('/api/swagger/routes')
    def list_documented_routes():
        """List all routes and their documentation status."""
        routes = []
        
        for rule in app.url_map.iter_rules():
            if rule.endpoint == 'static':
                continue
                
            view_func = app.view_functions.get(rule.endpoint)
            if not view_func:
                continue
                
            swagger_doc = getattr(view_func, '_swagger_doc', None)
            
            route_info = {
                'path': rule.rule,
                'methods': list((rule.methods or set()) - {'HEAD', 'OPTIONS'}),
                'endpoint': rule.endpoint,
                'documented': swagger_doc is not None,
                'summary': swagger_doc.get('summary', '') if swagger_doc else '',
                'tags': swagger_doc.get('tags', []) if swagger_doc else []
            }
            routes.append(route_info)
        
        return jsonify({
            'routes': routes,
            'total_routes': len(routes),
            'documented_routes': len([r for r in routes if r['documented']]),
            'undocumented_routes': len([r for r in routes if not r['documented']])
        })

# Utility function to create common response schemas
def create_response_schema(success_schema: Optional[Dict[str, Any]] = None, error_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Create a standard response schema dictionary.
    
    Args:
        success_schema: Schema for successful response (200)
        error_schema: Schema for error responses (4xx, 5xx)
        
    Returns:
        Dictionary of response schemas
    """
    responses = {}
    
    if success_schema:
        responses["200"] = {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": success_schema
                }
            }
        }
    
    if error_schema:
        responses["400"] = {
            "description": "Bad Request",
            "content": {
                "application/json": {
                    "schema": error_schema
                }
            }
        }
        responses["401"] = {
            "description": "Unauthorized",
            "content": {
                "application/json": {
                    "schema": error_schema
                }
            }
        }
        responses["403"] = {
            "description": "Forbidden", 
            "content": {
                "application/json": {
                    "schema": error_schema
                }
            }
        }
        responses["500"] = {
            "description": "Internal Server Error",
            "content": {
                "application/json": {
                    "schema": error_schema
                }
            }
        }
    
    return responses

# Common schema definitions
COMMON_SCHEMAS = {
    "error_response": {
        "type": "object",
        "properties": {
            "error": {
                "type": "string",
                "description": "Error message"
            }
        },
        "required": ["error"]
    },
    "success_response": {
        "type": "object", 
        "properties": {
            "success": {
                "type": "boolean",
                "description": "Operation success status"
            },
            "message": {
                "type": "string", 
                "description": "Success message"
            }
        },
        "required": ["success"]
    },
    "paginated_response": {
        "type": "object",
        "properties": {
            "page": {
                "type": "integer",
                "description": "Current page number"
            },
            "page_size": {
                "type": "integer", 
                "description": "Items per page"
            },
            "total_count": {
                "type": "integer",
                "description": "Total number of items"
            }
        }
    }
}

def get_auth_security():
    """Get standard authentication security requirements."""
    return [{"bearerAuth": []}, {"sessionAuth": []}]

def create_parameter(name: str, location: str, param_type: str = "string", required: bool = False, description: str = "") -> Dict[str, Any]:
    """
    Create a parameter definition for OpenAPI.
    
    Args:
        name: Parameter name
        location: Parameter location (query, path, header, cookie)
        param_type: Parameter type (string, integer, boolean, etc.)
        required: Whether parameter is required
        description: Parameter description
        
    Returns:
        Parameter definition dictionary
    """
    return {
        "name": name,
        "in": location,
        "required": required,
        "description": description,
        "schema": {
            "type": param_type
        }
    }