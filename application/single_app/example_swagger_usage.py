# example_swagger_usage.py

"""
Example demonstrating how to use the swagger_wrapper system.

This file shows how to retrofit existing routes with swagger documentation
and how to create new routes with comprehensive API documentation.
"""

from flask import Flask, jsonify, request
from swagger_wrapper import (
    swagger_route, 
    register_swagger_routes, 
    create_response_schema, 
    get_auth_security,
    create_parameter,
    COMMON_SCHEMAS
)

def register_example_routes(app: Flask):
    """Example of how to register routes with swagger documentation."""
    
    # Example 1: Simple route with basic documentation
    @app.route('/api/example/hello', methods=['GET'])
    @swagger_route(
        summary="Simple Hello World",
        description="Returns a simple hello world message",
        tags=["Examples"],
        responses={
            200: {
                "description": "Success",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    )
    def hello_world():
        return jsonify({"message": "Hello, World!"})
    
    # Example 2: Route with request body and comprehensive responses
    @app.route('/api/example/user', methods=['POST'])
    @swagger_route(
        summary="Create User",
        description="Create a new user in the system",
        tags=["Users", "Examples"],
        request_body={
            "type": "object",
            "properties": {
                "name": {
                    "type": "string", 
                    "description": "User's full name",
                    "example": "John Doe"
                },
                "email": {
                    "type": "string",
                    "format": "email", 
                    "description": "User's email address",
                    "example": "john.doe@example.com"
                },
                "age": {
                    "type": "integer",
                    "minimum": 18,
                    "maximum": 120,
                    "description": "User's age",
                    "example": 25
                }
            },
            "required": ["name", "email"]
        },
        responses={
            200: {
                "description": "User created successfully",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "success": {"type": "boolean"},
                                "user_id": {"type": "string", "format": "uuid"},
                                "message": {"type": "string"}
                            }
                        }
                    }
                }
            },
            400: {
                "description": "Bad Request",
                "content": {
                    "application/json": {
                        "schema": COMMON_SCHEMAS["error_response"]
                    }
                }
            }
        },
        security=get_auth_security()
    )
    def create_user():
        data = request.get_json()
        if not data or not data.get('name') or not data.get('email'):
            return jsonify({"error": "Name and email are required"}), 400
        
        # Simulate user creation
        import uuid
        user_id = str(uuid.uuid4())
        
        return jsonify({
            "success": True,
            "user_id": user_id,
            "message": f"User {data['name']} created successfully"
        })
    
    # Example 3: Route with path parameters and query parameters
    @app.route('/api/example/user/<user_id>', methods=['GET'])
    @swagger_route(
        summary="Get User by ID",
        description="Retrieve user information by user ID",
        tags=["Users", "Examples"],
        parameters=[
            create_parameter("user_id", "path", "string", True, "Unique user identifier"),
            create_parameter("include_profile", "query", "boolean", False, "Include user profile data"),
            create_parameter("format", "query", "string", False, "Response format (json, xml)")
        ],
        responses={
            200: {
                "description": "User found",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "user_id": {"type": "string"},
                                "name": {"type": "string"},
                                "email": {"type": "string"},
                                "created_at": {"type": "string", "format": "date-time"},
                                "profile": {
                                    "type": "object",
                                    "description": "User profile (only if include_profile=true)"
                                }
                            }
                        }
                    }
                }
            },
            404: {
                "description": "User not found",
                "content": {
                    "application/json": {
                        "schema": COMMON_SCHEMAS["error_response"]
                    }
                }
            }
        },
        security=get_auth_security()
    )
    def get_user(user_id):
        include_profile = request.args.get('include_profile', 'false').lower() == 'true'
        
        # Simulate user lookup
        user_data = {
            "user_id": user_id,
            "name": "John Doe",
            "email": "john.doe@example.com",
            "created_at": "2024-01-01T12:00:00Z"
        }
        
        if include_profile:
            user_data["profile"] = {
                "bio": "Software developer",
                "location": "San Francisco, CA"
            }
        
        return jsonify(user_data)
    
    # Example 4: Route with pagination
    @app.route('/api/example/users', methods=['GET'])
    @swagger_route(
        summary="List Users",
        description="Get a paginated list of users",
        tags=["Users", "Examples"],
        parameters=[
            create_parameter("page", "query", "integer", False, "Page number (default: 1)"),
            create_parameter("page_size", "query", "integer", False, "Items per page (default: 10)"),
            create_parameter("search", "query", "string", False, "Search term for filtering users")
        ],
        responses={
            200: {
                "description": "List of users",
                "content": {
                    "application/json": {
                        "schema": {
                            "allOf": [
                                COMMON_SCHEMAS["paginated_response"],
                                {
                                    "type": "object",
                                    "properties": {
                                        "users": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "user_id": {"type": "string"},
                                                    "name": {"type": "string"},
                                                    "email": {"type": "string"}
                                                }
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    }
                }
            }
        },
        security=get_auth_security()
    )
    def list_users():
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 10))
        search = request.args.get('search', '')
        
        # Simulate user list
        users = [
            {"user_id": "1", "name": "John Doe", "email": "john@example.com"},
            {"user_id": "2", "name": "Jane Smith", "email": "jane@example.com"},
        ]
        
        if search:
            users = [u for u in users if search.lower() in u['name'].lower() or search.lower() in u['email'].lower()]
        
        return jsonify({
            "users": users,
            "page": page,
            "page_size": page_size,
            "total_count": len(users)
        })

# Example of how to retrofit an existing route file
def retrofit_existing_route_example():
    """
    Example showing how to add swagger documentation to existing routes.
    
    For existing route files, you would:
    1. Import the swagger_wrapper functions at the top
    2. Add @swagger_route decorators to existing route functions
    3. No other changes needed!
    """
    
    # Before (existing route):
    """
    @app.route('/api/documents', methods=['GET'])
    @login_required
    @user_required
    def api_get_user_documents():
        # existing implementation
        pass
    """
    
    # After (with swagger documentation):
    """
    from swagger_wrapper import swagger_route, create_parameter, get_auth_security, COMMON_SCHEMAS
    
    @app.route('/api/documents', methods=['GET'])
    @swagger_route(
        summary="Get user documents",
        description="Retrieve a paginated list of documents for the authenticated user",
        tags=["Documents"],
        parameters=[
            create_parameter("page", "query", "integer", False, "Page number"),
            create_parameter("page_size", "query", "integer", False, "Items per page"),
            create_parameter("search", "query", "string", False, "Search term")
        ],
        responses={
            200: {
                "description": "List of documents",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "documents": {"type": "array"},
                                "page": {"type": "integer"},
                                "page_size": {"type": "integer"},
                                "total_count": {"type": "integer"}
                            }
                        }
                    }
                }
            }
        },
        security=get_auth_security()
    )
    @login_required
    @user_required
    def api_get_user_documents():
        # existing implementation unchanged
        pass
    """

if __name__ == '__main__':
    # Example of setting up a Flask app with swagger
    app = Flask(__name__)
    
    # Register swagger routes (adds /swagger and /swagger.json endpoints)
    register_swagger_routes(app)
    
    # Register your documented routes
    register_example_routes(app)
    
    app.run(debug=True)