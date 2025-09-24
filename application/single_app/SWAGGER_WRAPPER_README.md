# Swagger Route Wrapper System

This system provides a simple way to automatically generate Swagger/OpenAPI documentation for Flask routes in the SimpleChat application.

## Version: 0.229.061

## What It Does

The swagger wrapper system allows you to:

1. **Add API documentation to existing routes** without changing the route logic
2. **Automatically generate a Swagger UI** at `/swagger` 
3. **Provide a JSON API specification** at `/swagger.json`
4. **List all routes and their documentation status** at `/api/swagger/routes`

## Quick Start

### 1. Setup (Already Done)

The swagger system is already integrated into the main application. The following routes are automatically available:

- **`/swagger`** - Interactive Swagger UI for browsing and testing APIs
- **`/swagger.json`** - OpenAPI 3.0 specification in JSON format  
- **`/api/swagger/routes`** - List of all routes and their documentation status

### 2. Document Existing Routes

To add documentation to existing routes, simply import the swagger wrapper and add the `@swagger_route` decorator:

```python
# At the top of your route file
from swagger_wrapper import swagger_route, get_auth_security, COMMON_SCHEMAS

# Add documentation to existing routes
@app.route('/api/example', methods=['GET'])
@swagger_route(
    summary="Get Example Data",
    description="Retrieves example data for the authenticated user",
    tags=["Examples"],
    responses={
        200: {
            "description": "Success",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "data": {"type": "array"},
                            "total": {"type": "integer"}
                        }
                    }
                }
            }
        }
    },
    security=get_auth_security()
)
@login_required  # Existing decorators remain unchanged
@user_required
def get_example():
    # Existing route logic remains unchanged
    return jsonify({"data": [], "total": 0})
```

## Example: Real Implementation

The `route_backend_models.py` file has been updated as a working example. It shows how to document three endpoints:

- `GET /api/models/gpt` - Get GPT model deployments
- `GET /api/models/embedding` - Get embedding model deployments  
- `GET /api/models/image` - Get image generation model deployments

Visit `/swagger` after starting the application to see these documented endpoints in action.

## Swagger Route Decorator Options

```python
@swagger_route(
    summary="Brief endpoint description",                    # Required: Short summary
    description="Detailed endpoint description",             # Optional: Longer description
    tags=["Category", "Subcategory"],                       # Optional: Grouping tags
    request_body={...},                                     # Optional: Request body schema
    responses={200: {...}, 400: {...}},                    # Optional: Response schemas
    parameters=[...],                                       # Optional: Query/path parameters
    security=get_auth_security(),                           # Optional: Auth requirements
    deprecated=False                                        # Optional: Mark as deprecated
)
```

## Helper Functions

### Authentication
```python
from swagger_wrapper import get_auth_security

# Standard auth for routes requiring login
security=get_auth_security()  # Returns [{"bearerAuth": []}, {"sessionAuth": []}]
```

### Common Schemas
```python
from swagger_wrapper import COMMON_SCHEMAS

# Use predefined schemas
COMMON_SCHEMAS["error_response"]      # Standard error response
COMMON_SCHEMAS["success_response"]    # Standard success response  
COMMON_SCHEMAS["paginated_response"]  # Pagination metadata
```

### Parameter Creation
```python 
from swagger_wrapper import create_parameter

# Create parameter definitions
create_parameter("page", "query", "integer", False, "Page number")
create_parameter("user_id", "path", "string", True, "User identifier")
```

### Response Schemas
```python
from swagger_wrapper import create_response_schema

# Generate standard response patterns
responses = create_response_schema(
    success_schema={"type": "object", "properties": {...}},
    error_schema=COMMON_SCHEMAS["error_response"]
)
```

## Best Practices

### 1. Consistent Tagging
Use consistent tags to group related endpoints:
```python
tags=["Documents"]           # For document-related endpoints
tags=["Users", "Admin"]      # For user management by admins
tags=["Models", "Azure OpenAI"]  # For AI model endpoints
```

### 2. Comprehensive Responses
Document all possible response codes:
```python
responses={
    200: {"description": "Success", "content": {...}},
    400: {"description": "Bad request", "content": {...}},
    401: {"description": "Unauthorized", "content": {...}},
    403: {"description": "Forbidden", "content": {...}},
    500: {"description": "Server error", "content": {...}}
}
```

### 3. Parameter Documentation
Include all parameters with clear descriptions:
```python
parameters=[
    create_parameter("page", "query", "integer", False, "Page number (default: 1)"),
    create_parameter("page_size", "query", "integer", False, "Items per page (default: 10)"),
    create_parameter("search", "query", "string", False, "Search term for filtering")
]
```

### 4. Request Body Schemas
For POST/PUT/PATCH endpoints, define request body schemas:
```python
request_body={
    "type": "object",
    "properties": {
        "name": {"type": "string", "description": "User name"},
        "email": {"type": "string", "format": "email"}
    },
    "required": ["name", "email"]
}
```

## How to Use the Generated Documentation

### Accessing Documentation
1. Start the application
2. Navigate to `/swagger` in your browser
3. Browse available endpoints organized by tags
4. Click "Try it out" to test endpoints directly

### Testing Endpoints
1. Click on any endpoint in the Swagger UI
2. Click "Try it out" 
3. Fill in required parameters
4. Click "Execute" to send the request
5. View the response directly in the UI

### Integration with Development
- Use `/api/swagger/routes` to see which routes are documented vs undocumented
- The JSON spec at `/swagger.json` can be imported into API testing tools
- Documentation automatically updates when you restart the application

## Benefits

1. **Zero Impact on Existing Code** - Route logic remains unchanged
2. **Self-Documenting** - API documentation stays in sync with code
3. **Interactive Testing** - Built-in UI for testing endpoints  
4. **Standard Format** - Uses OpenAPI 3.0 specification
5. **Easy Maintenance** - Documentation lives alongside route definitions

## Implementation Status

✅ **Core System** - Swagger wrapper and route registration complete  
✅ **Integration** - Added to main application  
✅ **Example** - Backend models routes documented  
⏳ **Expansion** - Ready to document additional route files as needed

## Next Steps

To document additional routes:

1. Import swagger utilities in the route file
2. Add `@swagger_route` decorators to route functions  
3. Test documentation at `/swagger`
4. Iterate on schema definitions for clarity

The system is designed to be incrementally adopted - you can document routes one file at a time without impacting the rest of the application.