# AUTOMATIC_SWAGGER_SCHEMA_GENERATION Feature

## Overview and Purpose
This feature provides automatic schema generation for Flask API endpoints using Abstract Syntax Tree (AST) analysis. It eliminates the need to manually define OpenAPI response schemas and parameter definitions by automatically inferring them from function code.

**Version implemented:** 0.229.064

**Dependencies:**
- Flask web framework
- Python AST module for code analysis
- Python inspect module for function introspection
- textwrap module for source code normalization

## Technical Specifications

### Architecture Overview
The automatic schema generation system consists of several key components:

1. **Enhanced @swagger_route Decorator**: Extended with `auto_schema` parameter
2. **AST Analysis Engine**: Parses function source code to extract return patterns
3. **Schema Inference System**: Converts AST nodes to OpenAPI JSON schemas
4. **Parameter Detection**: Analyzes function signatures for path/query parameters

### Core Functions

#### 1. swagger_route Decorator
```python
@swagger_route()  # Fully automatic - no parameters needed!
def get_user_data():
    """Fetch user data from the database."""
    return jsonify({"result": "success", "count": 42})
```

**Enhanced Parameters:**
- `auto_schema: bool = True` - Enable/disable automatic response schema generation
- `auto_summary: bool = True` - Enable/disable automatic summary from function name
- `auto_description: bool = True` - Enable/disable automatic description from docstring
- `auto_tags: bool = True` - Enable/disable automatic tags from route path
- All original parameters still available for manual override when needed

#### 2. _analyze_function_returns()
Analyzes function return statements using AST parsing to generate response schemas:
- Detects `jsonify()` calls and extracts dictionary structures
- Handles tuple returns like `(jsonify(...), 400)` for status codes
- Supports nested objects and arrays
- Generates proper OpenAPI 3.0 response definitions

#### 3. _analyze_function_parameters()
Analyzes function signatures to generate parameter documentation:
- Extracts parameters from function signature using `inspect.signature()`
- Infers types from type annotations
- Detects path parameters from route patterns
- Generates OpenAPI parameter schemas

#### 4. _ast_to_schema()
Converts AST nodes to JSON Schema format:
- Handles dictionary literals with property extraction
- Supports arrays, strings, integers, floats, booleans
- Includes example values from literal values
- Provides fallback types for complex expressions

#### 5. _generate_summary_from_function_name()
Converts function names to human-readable summaries:
- Transforms snake_case to Title Case
- `get_user_profile` → `"Get User Profile"`
- `fetch_analytics_data` → `"Fetch Analytics Data"`

#### 6. _extract_tags_from_route_path()
Extracts meaningful tags from URL paths:
- Filters out common prefixes (`api`, `v1`, `v2`, etc.)
- Skips parameter segments (`<int:user_id>`)
- Capitalizes meaningful segments
- `/api/users/profile` → `["Users", "Profile"]`
- `/api/admin/reports/analytics` → `["Admin", "Reports", "Analytics"]`

### File Structure
```
application/single_app/
├── swagger_wrapper.py          # Core automatic schema generation system
├── route_backend_models.py     # Example documented endpoints
└── static/swagger-ui/          # Local Swagger UI assets
    ├── swagger-ui.css
    ├── swagger-ui-bundle.js
    └── swagger-ui-standalone-preset.js
```

### API Endpoints
- `GET /swagger` - Interactive Swagger UI documentation
- `GET /swagger.json` - OpenAPI 3.0 specification JSON
- `GET /api/swagger/routes` - Route documentation status report

## Usage Instructions

### Basic Usage (Fully Automatic)
```python
@app.route('/api/users/<int:user_id>')
@swagger_route()  # No parameters needed!
def get_user_profile(user_id: int):
    """Retrieve detailed profile information for a specific user account."""
    return jsonify({
        "user_id": user_id,
        "name": "John Doe",
        "email": "john@example.com",
        "active": True,
        "created_at": "2024-01-01T00:00:00Z"
    })
```

**Automatically generates:**
- **Summary**: `"Get User Profile"` (from function name `get_user_profile`)
- **Description**: `"Retrieve detailed profile information for a specific user account."` (from docstring)
- **Tags**: `["Users"]` (from path segment `/api/users/...`)
- **Parameters**: Path parameter `user_id` as integer type (from function signature)
- **Response Schema**: 5 properties with correct types and example values (from `jsonify()` call analysis)

### Manual Override Mode
```python
@app.route('/api/complex')
@swagger_route(
    summary="Complex endpoint",
    tags=["Advanced"],
    auto_schema=False,  # Disable automatic generation
    responses={
        "200": {
            "description": "Custom response definition",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "custom_field": {"type": "string"}
                        }
                    }
                }
            }
        }
    }
)
def complex_endpoint():
    return jsonify({"custom_field": "value"})
```

### Error Response Handling
```python
@app.route('/api/data')
@swagger_route(
    summary="Data endpoint with error handling",
    tags=["Data"]
)
def data_endpoint():
    """Endpoint that can return different status codes."""
    error_type = request.args.get('error')
    
    if error_type == 'not_found':
        return jsonify({"error": "Resource not found"}), 404
    elif error_type == 'bad_request':
        return jsonify({"error": "Invalid parameters"}), 400
    
    return jsonify({
        "data": [1, 2, 3],
        "success": True
    })
```

**Automatically detects:**
- Multiple return paths with different status codes
- Error response schemas for 400, 404 status codes
- Success response schema for 200 status code

### Integration Examples

#### With Flask-RESTful Style
```python
@app.route('/api/search')
@swagger_route(
    summary="Search items",
    tags=["Search"]
)
def search_items(query: str = "", limit: int = 10, offset: int = 0):
    """Search for items with pagination support."""
    results = perform_search(query, limit, offset)
    
    return jsonify({
        "query": query,
        "limit": limit,
        "offset": offset,
        "total": len(results),
        "items": results
    })
```

#### With Type Annotations
```python
from typing import List, Optional

@app.route('/api/bulk-process')
@swagger_route(
    summary="Bulk process items",
    tags=["Processing"]
)
def bulk_process(items: List[str], async_mode: bool = False):
    """Process multiple items in bulk."""
    return jsonify({
        "processed_items": len(items),
        "async": async_mode,
        "job_id": str(uuid.uuid4()) if async_mode else None
    })
```

## Testing and Validation

### Functional Tests
Located in: `functional_tests/test_automatic_swagger_schema_generation.py`

The test suite validates:
- Basic automatic schema generation
- Parameter detection from function signatures
- Response schema extraction from return statements
- Manual override functionality
- Docstring usage as descriptions
- Integration with Flask routing

### Test Coverage
- **Response Schema Generation**: Tests jsonify() call parsing
- **Parameter Detection**: Tests path and query parameter inference
- **Type Inference**: Tests type annotation support
- **Error Handling**: Tests fallback to default schemas
- **Integration**: Tests with real Flask applications

### Manual Testing Steps
1. Start the application with swagger routes registered
2. Visit `/swagger` to view interactive documentation
3. Verify auto-generated schemas match expected structure
4. Test API endpoints through Swagger UI
5. Check `/api/swagger/routes` for documentation coverage

## Performance Considerations

### AST Parsing Performance
- AST parsing is performed once during route registration (startup time)
- Parsed schemas are cached in function metadata
- No runtime performance impact on API requests
- Source code analysis adds ~1-2ms per route during startup

### Memory Usage
- Generated schemas are stored as function attributes
- Minimal memory overhead (~1KB per documented route)
- No impact on request/response payload sizes

### Known Limitations

#### 1. Complex Return Logic
The AST analysis works best with simple return statements. Complex conditional logic may not be fully captured:

```python
# Good - automatically detected
def simple_endpoint():
    return jsonify({"status": "ok"})

# Limited - only first return path detected
def complex_endpoint():
    if complex_condition():
        return jsonify({"type": "A", "data": get_a()})
    else:
        return jsonify({"type": "B", "data": get_b()})
```

#### 2. Dynamic Response Structures
Responses built dynamically at runtime are not analyzable:

```python
# Not detectable by AST analysis
def dynamic_endpoint():
    response_data = build_dynamic_response()
    return jsonify(response_data)
```

#### 3. External Function Calls
Return values from external functions cannot be analyzed:

```python
# Limited detection - will show basic object schema
def external_call_endpoint():
    return jsonify(external_service.get_data())
```

## Cross-References

### Related Features
- **Swagger UI Integration**: Core documentation interface
- **OpenAPI 3.0 Generation**: Standards-compliant specification generation
- **Content Security Policy**: Local asset serving for security compliance

### Related Files
- `swagger_wrapper.py`: Core implementation
- `route_backend_models.py`: Example implementations
- `functional_tests/test_automatic_swagger_schema_generation.py`: Validation tests

### Configuration Dependencies
- Flask application configuration
- Static file serving for Swagger UI assets
- CSP headers allowing local resource loading

## Maintenance

### Adding New Type Support
To support additional Python types in schema generation, extend the `_ast_to_schema()` function:

```python
elif isinstance(node, ast.Constant):
    value = node.value
    if isinstance(value, datetime):
        return {"type": "string", "format": "date-time", "example": value.isoformat()}
    # ... existing type handling
```

### Extending AST Analysis
For more complex return pattern detection, extend the `ReturnVisitor` class:

```python
class ReturnVisitor(ast.NodeVisitor):
    def visit_If(self, node):
        # Handle conditional returns
        # ... custom logic
        self.generic_visit(node)
```

### Performance Optimization
- Consider caching AST parsing results for identical function signatures
- Implement lazy loading for schema generation on first access
- Add configuration option to disable auto-schema for specific routes

This feature significantly reduces the manual effort required to maintain API documentation while ensuring consistency between code and documentation.