#!/usr/bin/env python3
"""
APIDESIGNER Agent v7.0 - API Architecture and Contract Specialist Python Implementation
Comprehensive API design, specification, and contract testing functionality
"""

import asyncio
import hashlib
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

# Optional imports for enhanced functionality
try:
    import jsonschema

    HAS_JSONSCHEMA = True
except ImportError:
    HAS_JSONSCHEMA = False

try:
    from openapi_spec_validator import validate_spec

    HAS_OPENAPI_VALIDATOR = True
except ImportError:
    HAS_OPENAPI_VALIDATOR = False

try:
    import graphql
    from graphql import build_schema
    from graphql import validate as validate_graphql

    HAS_GRAPHQL = True
except ImportError:
    HAS_GRAPHQL = False


class APIType(Enum):
    """API types supported"""

    REST = "REST"
    GRAPHQL = "GraphQL"
    GRPC = "gRPC"
    WEBSOCKET = "WebSocket"
    EVENT_DRIVEN = "Event-Driven"


class APIVersion(Enum):
    """API versioning strategies"""

    URL_PATH = "url_path"  # /api/v1/resource
    HEADER = "header"  # Accept: application/vnd.api+json;version=1
    QUERY_PARAM = "query_param"  # /api/resource?version=1
    SUBDOMAIN = "subdomain"  # v1.api.example.com


@dataclass
class APIEndpoint:
    """API endpoint definition"""

    path: str
    method: str
    description: str
    parameters: List[Dict[str, Any]] = field(default_factory=list)
    request_body: Optional[Dict[str, Any]] = None
    responses: Dict[int, Dict[str, Any]] = field(default_factory=dict)
    security: List[str] = field(default_factory=list)
    deprecated: bool = False
    tags: List[str] = field(default_factory=list)


@dataclass
class APISpecification:
    """Complete API specification"""

    title: str
    version: str
    description: str
    base_url: str
    api_type: APIType
    endpoints: List[APIEndpoint] = field(default_factory=list)
    schemas: Dict[str, Any] = field(default_factory=dict)
    security_schemes: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class OpenAPIGenerator:
    """Generates OpenAPI 3.0 specifications"""

    def __init__(self):
        self.spec = {
            "openapi": "3.0.0",
            "info": {},
            "servers": [],
            "paths": {},
            "components": {
                "schemas": {},
                "responses": {},
                "parameters": {},
                "securitySchemes": {},
            },
        }

    def generate_spec(self, api_spec: APISpecification) -> Dict[str, Any]:
        """Generate complete OpenAPI specification"""
        # Info section
        self.spec["info"] = {
            "title": api_spec.title,
            "version": api_spec.version,
            "description": api_spec.description,
        }

        # Servers
        self.spec["servers"] = [
            {"url": api_spec.base_url, "description": "Primary API server"}
        ]

        # Paths
        for endpoint in api_spec.endpoints:
            path = endpoint.path
            if path not in self.spec["paths"]:
                self.spec["paths"][path] = {}

            operation = {
                "summary": endpoint.description,
                "tags": endpoint.tags,
                "parameters": self._generate_parameters(endpoint.parameters),
                "responses": self._generate_responses(endpoint.responses),
            }

            if endpoint.request_body:
                operation["requestBody"] = self._generate_request_body(
                    endpoint.request_body
                )

            if endpoint.security:
                operation["security"] = [{scheme: [] for scheme in endpoint.security}]

            if endpoint.deprecated:
                operation["deprecated"] = True

            self.spec["paths"][path][endpoint.method.lower()] = operation

        # Components
        self.spec["components"]["schemas"] = api_spec.schemas
        self.spec["components"]["securitySchemes"] = api_spec.security_schemes

        return self.spec

    def _generate_parameters(
        self, parameters: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate parameter definitions"""
        result = []
        for param in parameters:
            result.append(
                {
                    "name": param.get("name"),
                    "in": param.get("in", "query"),
                    "required": param.get("required", False),
                    "schema": param.get("schema", {"type": "string"}),
                    "description": param.get("description", ""),
                }
            )
        return result

    def _generate_request_body(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Generate request body definition"""
        return {
            "required": request_body.get("required", True),
            "content": {"application/json": {"schema": request_body.get("schema", {})}},
        }

    def _generate_responses(
        self, responses: Dict[int, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate response definitions"""
        result = {}
        for status_code, response in responses.items():
            result[str(status_code)] = {
                "description": response.get("description", ""),
                "content": (
                    {"application/json": {"schema": response.get("schema", {})}}
                    if "schema" in response
                    else {}
                ),
            }
        return result

    def validate_spec(self) -> Tuple[bool, List[str]]:
        """Validate OpenAPI specification"""
        errors = []

        if HAS_OPENAPI_VALIDATOR:
            try:
                validate_spec(self.spec)
                return True, []
            except Exception as e:
                errors.append(str(e))
                return False, errors
        else:
            # Basic validation
            if not self.spec.get("info"):
                errors.append("Missing info section")
            if not self.spec.get("paths"):
                errors.append("No paths defined")

            return len(errors) == 0, errors


class GraphQLSchemaGenerator:
    """Generates GraphQL schemas"""

    def __init__(self):
        self.type_definitions = []
        self.query_definitions = []
        self.mutation_definitions = []
        self.subscription_definitions = []

    def add_type(self, name: str, fields: Dict[str, str]):
        """Add a GraphQL type"""
        field_defs = []
        for field_name, field_type in fields.items():
            field_defs.append(f"  {field_name}: {field_type}")

        type_def = f"type {name} {{\n" + "\n".join(field_defs) + "\n}"
        self.type_definitions.append(type_def)

    def add_query(self, name: str, args: Dict[str, str], return_type: str):
        """Add a GraphQL query"""
        arg_list = ", ".join([f"{k}: {v}" for k, v in args.items()])
        query_def = f"  {name}({arg_list}): {return_type}"
        self.query_definitions.append(query_def)

    def add_mutation(self, name: str, args: Dict[str, str], return_type: str):
        """Add a GraphQL mutation"""
        arg_list = ", ".join([f"{k}: {v}" for k, v in args.items()])
        mutation_def = f"  {name}({arg_list}): {return_type}"
        self.mutation_definitions.append(mutation_def)

    def generate_schema(self) -> str:
        """Generate complete GraphQL schema"""
        schema_parts = []

        # Add type definitions
        schema_parts.extend(self.type_definitions)

        # Add Query type
        if self.query_definitions:
            schema_parts.append(
                "type Query {\n" + "\n".join(self.query_definitions) + "\n}"
            )

        # Add Mutation type
        if self.mutation_definitions:
            schema_parts.append(
                "type Mutation {\n" + "\n".join(self.mutation_definitions) + "\n}"
            )

        # Add Subscription type
        if self.subscription_definitions:
            schema_parts.append(
                "type Subscription {\n"
                + "\n".join(self.subscription_definitions)
                + "\n}"
            )

        return "\n\n".join(schema_parts)

    def validate_schema(self, schema_str: str) -> Tuple[bool, List[str]]:
        """Validate GraphQL schema"""
        if HAS_GRAPHQL:
            try:
                build_schema(schema_str)
                return True, []
            except Exception as e:
                return False, [str(e)]
        else:
            # Basic validation
            if "type Query" not in schema_str and "type Mutation" not in schema_str:
                return False, ["Schema must have at least Query or Mutation type"]
            return True, []


class APIContractTester:
    """Generates and validates API contracts"""

    def __init__(self):
        self.contracts = []
        self.test_results = {}

    def generate_contract(self, endpoint: APIEndpoint) -> Dict[str, Any]:
        """Generate contract for endpoint"""
        contract = {
            "description": f"Contract for {endpoint.method} {endpoint.path}",
            "request": {
                "method": endpoint.method,
                "path": endpoint.path,
                "parameters": endpoint.parameters,
                "body": endpoint.request_body,
            },
            "response": {
                "status": 200,
                "body": endpoint.responses.get(200, {}).get("schema", {}),
            },
        }

        self.contracts.append(contract)
        return contract

    def generate_pact_file(self, consumer: str, provider: str) -> Dict[str, Any]:
        """Generate Pact contract file"""
        pact = {
            "consumer": {"name": consumer},
            "provider": {"name": provider},
            "interactions": [],
        }

        for contract in self.contracts:
            interaction = {
                "description": contract["description"],
                "request": contract["request"],
                "response": contract["response"],
            }
            pact["interactions"].append(interaction)

        return pact

    def validate_contract(
        self, contract: Dict[str, Any], actual_response: Dict[str, Any]
    ) -> bool:
        """Validate response against contract"""
        expected = contract["response"]

        # Check status code
        if actual_response.get("status") != expected.get("status"):
            return False

        # Check response body schema
        if HAS_JSONSCHEMA and "body" in expected:
            try:
                jsonschema.validate(actual_response.get("body", {}), expected["body"])
                return True
            except jsonschema.ValidationError:
                return False

        return True


class MockServiceGenerator:
    """Generates mock services from API specifications"""

    def __init__(self):
        self.mocks = {}

    def generate_mock_response(
        self, endpoint: APIEndpoint, status_code: int = 200
    ) -> Dict[str, Any]:
        """Generate mock response for endpoint"""
        response_spec = endpoint.responses.get(status_code, {})
        schema = response_spec.get("schema", {})

        return self._generate_from_schema(schema)

    def _generate_from_schema(self, schema: Dict[str, Any]) -> Any:
        """Generate data from JSON schema"""
        schema_type = schema.get("type", "object")

        if schema_type == "object":
            result = {}
            properties = schema.get("properties", {})
            for prop_name, prop_schema in properties.items():
                result[prop_name] = self._generate_from_schema(prop_schema)
            return result
        elif schema_type == "array":
            items_schema = schema.get("items", {})
            return [self._generate_from_schema(items_schema) for _ in range(3)]
        elif schema_type == "string":
            return schema.get("example", "sample_string")
        elif schema_type == "number":
            return schema.get("example", 42.0)
        elif schema_type == "integer":
            return schema.get("example", 42)
        elif schema_type == "boolean":
            return schema.get("example", True)
        else:
            return None

    def generate_mock_server_code(self, api_spec: APISpecification) -> str:
        """Generate mock server implementation"""
        if api_spec.api_type == APIType.REST:
            return self._generate_express_mock(api_spec)
        elif api_spec.api_type == APIType.GRAPHQL:
            return self._generate_graphql_mock(api_spec)
        else:
            return "# Mock server generation not supported for this API type"

    def _generate_express_mock(self, api_spec: APISpecification) -> str:
        """Generate Express.js mock server"""
        code = """const express = require('express');
const app = express();
app.use(express.json());

"""

        for endpoint in api_spec.endpoints:
            mock_response = self.generate_mock_response(endpoint)
            code += f"""
app.{endpoint.method.lower()}('{endpoint.path}', (req, res) => {{
    res.json({json.dumps(mock_response, indent=2)});
}});
"""

        code += """
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Mock server running on port ${PORT}`);
});
"""
        return code

    def _generate_graphql_mock(self, api_spec: APISpecification) -> str:
        """Generate GraphQL mock server"""
        return """const { ApolloServer, gql } = require('apollo-server');

const typeDefs = gql`
  # GraphQL schema here
`;

const resolvers = {
  Query: {
    // Mock resolvers
  }
};

const server = new ApolloServer({ typeDefs, resolvers });

server.listen().then(({ url }) => {
  console.log(`Mock GraphQL server ready at ${url}`);
});
"""


class APIDESIGNERPythonExecutor:
    """Main executor for APIDESIGNER agent in Python mode"""

    def __init__(self):
        self.agent_name = "APIDESIGNER"
        self.version = "9.0.0"
        self.start_time = datetime.now()

        self.openapi_gen = OpenAPIGenerator()
        self.graphql_gen = GraphQLSchemaGenerator()
        self.contract_tester = APIContractTester()
        self.mock_gen = MockServiceGenerator()
        self.specifications = {}
        self.metrics = {
            "specs_generated": 0,
            "contracts_created": 0,
            "mocks_generated": 0,
            "validation_success_rate": 0.0,
        }

    async def execute_command(
        self, command: str, context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Execute APIDESIGNER command"""
        try:
            # Parse command
            cmd_parts = command.strip().split()
            action = cmd_parts[0] if cmd_parts else ""

            # Route to appropriate handler
            if action == "design_rest_api":
                return await self.design_rest_api(context)
            elif action == "design_graphql_api":
                return await self.design_graphql_api(context)
            elif action == "generate_openapi":
                return await self.generate_openapi(context)
            elif action == "generate_graphql_schema":
                return await self.generate_graphql_schema(context)
            elif action == "create_contract_tests":
                return await self.create_contract_tests(context)
            elif action == "generate_mock_service":
                return await self.generate_mock_service(context)
            elif action == "validate_api_spec":
                return await self.validate_api_spec(context)
            elif action == "add_api_versioning":
                return await self.add_api_versioning(context)
            elif action == "generate_sdk":
                return await self.generate_sdk(context)
            elif action == "create_postman_collection":
                return await self.create_postman_collection(context)
            elif action == "analyze_breaking_changes":
                return await self.analyze_breaking_changes(context)
            elif action == "generate_api_documentation":
                return await self.generate_api_documentation(context)
            elif action == "design_pagination":
                return await self.design_pagination(context)
            elif action == "implement_rate_limiting":
                return await self.implement_rate_limiting(context)
            else:
                return await self.handle_unknown_command(command, context)

        except Exception as e:
            return {"status": "error", "error": str(e), "command": command}

    async def design_rest_api(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Design RESTful API"""
        api_name = context.get("name", "API")
        resources = context.get("resources", [])

        api_spec = APISpecification(
            title=api_name,
            version="1.0.0",
            description=context.get("description", "RESTful API"),
            base_url=context.get("base_url", "https://api.example.com"),
            api_type=APIType.REST,
        )

        # Generate CRUD endpoints for each resource
        for resource in resources:
            resource_name = resource["name"]
            resource_path = f"/{resource_name.lower()}s"

            # List endpoint
            api_spec.endpoints.append(
                APIEndpoint(
                    path=resource_path,
                    method="GET",
                    description=f"List all {resource_name}s",
                    parameters=[
                        {"name": "limit", "in": "query", "schema": {"type": "integer"}},
                        {
                            "name": "offset",
                            "in": "query",
                            "schema": {"type": "integer"},
                        },
                    ],
                    responses={
                        200: {
                            "description": "Success",
                            "schema": {
                                "type": "array",
                                "items": resource.get("schema", {}),
                            },
                        }
                    },
                    tags=[resource_name],
                )
            )

            # Get endpoint
            api_spec.endpoints.append(
                APIEndpoint(
                    path=f"{resource_path}/{{id}}",
                    method="GET",
                    description=f"Get {resource_name} by ID",
                    parameters=[
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    responses={
                        200: {
                            "description": "Success",
                            "schema": resource.get("schema", {}),
                        },
                        404: {"description": "Not found"},
                    },
                    tags=[resource_name],
                )
            )

            # Create endpoint
            api_spec.endpoints.append(
                APIEndpoint(
                    path=resource_path,
                    method="POST",
                    description=f"Create new {resource_name}",
                    request_body={
                        "required": True,
                        "schema": resource.get("schema", {}),
                    },
                    responses={
                        201: {
                            "description": "Created",
                            "schema": resource.get("schema", {}),
                        },
                        400: {"description": "Bad request"},
                    },
                    tags=[resource_name],
                )
            )

            # Update endpoint
            api_spec.endpoints.append(
                APIEndpoint(
                    path=f"{resource_path}/{{id}}",
                    method="PUT",
                    description=f"Update {resource_name}",
                    parameters=[
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    request_body={
                        "required": True,
                        "schema": resource.get("schema", {}),
                    },
                    responses={
                        200: {
                            "description": "Updated",
                            "schema": resource.get("schema", {}),
                        },
                        404: {"description": "Not found"},
                    },
                    tags=[resource_name],
                )
            )

            # Delete endpoint
            api_spec.endpoints.append(
                APIEndpoint(
                    path=f"{resource_path}/{{id}}",
                    method="DELETE",
                    description=f"Delete {resource_name}",
                    parameters=[
                        {
                            "name": "id",
                            "in": "path",
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    responses={
                        204: {"description": "Deleted"},
                        404: {"description": "Not found"},
                    },
                    tags=[resource_name],
                )
            )

        # Store specification
        self.specifications[api_name] = api_spec
        self.metrics["specs_generated"] += 1

        # Create apidesigner files and documentation
        await self._create_apidesigner_files(
            result, context if "context" in locals() else {}
        )
        return {
            "status": "success",
            "api_type": "REST",
            "resources": len(resources),
            "endpoints": len(api_spec.endpoints),
            "methods": list(set(e.method for e in api_spec.endpoints)),
        }

    async def design_graphql_api(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Design GraphQL API"""
        api_name = context.get("name", "GraphQL API")
        types = context.get("types", [])

        # Add types
        for type_def in types:
            self.graphql_gen.add_type(type_def["name"], type_def["fields"])

        # Add queries
        queries = context.get("queries", [])
        for query in queries:
            self.graphql_gen.add_query(
                query["name"], query.get("args", {}), query["return_type"]
            )

        # Add mutations
        mutations = context.get("mutations", [])
        for mutation in mutations:
            self.graphql_gen.add_mutation(
                mutation["name"], mutation.get("args", {}), mutation["return_type"]
            )

        # Generate schema
        schema = self.graphql_gen.generate_schema()

        # Validate schema
        is_valid, errors = self.graphql_gen.validate_schema(schema)

        self.metrics["specs_generated"] += 1

        return {
            "status": "success" if is_valid else "warning",
            "api_type": "GraphQL",
            "types": len(types),
            "queries": len(queries),
            "mutations": len(mutations),
            "schema_valid": is_valid,
            "errors": errors if not is_valid else [],
            "schema": schema,
        }

    async def generate_openapi(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate OpenAPI specification"""
        api_name = context.get(
            "api_name",
            list(self.specifications.keys())[0] if self.specifications else "API",
        )

        if api_name not in self.specifications:
            return {"status": "error", "error": f"API '{api_name}' not found"}

        api_spec = self.specifications[api_name]
        openapi_spec = self.openapi_gen.generate_spec(api_spec)

        # Validate specification
        is_valid, errors = self.openapi_gen.validate_spec()

        # Save to file
        output_path = Path(context.get("output_path", "openapi.yaml"))
        with open(output_path, "w") as f:
            yaml.dump(openapi_spec, f, default_flow_style=False)

        return {
            "status": "success" if is_valid else "warning",
            "spec_version": "3.0.0",
            "paths": len(openapi_spec["paths"]),
            "operations": sum(
                len(methods) for methods in openapi_spec["paths"].values()
            ),
            "schemas": len(openapi_spec["components"]["schemas"]),
            "valid": is_valid,
            "errors": errors,
            "output_path": str(output_path),
        }

    async def generate_graphql_schema(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate GraphQL schema file"""
        schema = self.graphql_gen.generate_schema()

        if not schema:
            return {"status": "error", "error": "No GraphQL schema defined"}

        output_path = Path(context.get("output_path", "schema.graphql"))
        output_path.write_text(schema)

        return {
            "status": "success",
            "schema_file": str(output_path),
            "size": len(schema),
        }

    async def create_contract_tests(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Create contract tests for API"""
        api_name = context.get(
            "api_name",
            list(self.specifications.keys())[0] if self.specifications else None,
        )

        if not api_name or api_name not in self.specifications:
            return {"status": "error", "error": "API specification not found"}

        api_spec = self.specifications[api_name]

        # Generate contracts for all endpoints
        for endpoint in api_spec.endpoints:
            self.contract_tester.generate_contract(endpoint)

        # Generate Pact file
        consumer = context.get("consumer", "Consumer")
        provider = context.get("provider", api_name)
        pact = self.contract_tester.generate_pact_file(consumer, provider)

        # Save Pact file
        output_path = Path(context.get("output_path", "pact.json"))
        with open(output_path, "w") as f:
            json.dump(pact, f, indent=2)

        self.metrics["contracts_created"] += len(self.contract_tester.contracts)

        return {
            "status": "success",
            "contracts_created": len(self.contract_tester.contracts),
            "pact_file": str(output_path),
            "consumer": consumer,
            "provider": provider,
        }

    async def generate_mock_service(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate mock service implementation"""
        api_name = context.get(
            "api_name",
            list(self.specifications.keys())[0] if self.specifications else None,
        )

        if not api_name or api_name not in self.specifications:
            return {"status": "error", "error": "API specification not found"}

        api_spec = self.specifications[api_name]

        # Generate mock responses
        mock_responses = {}
        for endpoint in api_spec.endpoints:
            key = f"{endpoint.method} {endpoint.path}"
            mock_responses[key] = self.mock_gen.generate_mock_response(endpoint)

        # Generate mock server code
        server_code = self.mock_gen.generate_mock_server_code(api_spec)

        # Save mock server
        output_path = Path(context.get("output_path", "mock-server.js"))
        output_path.write_text(server_code)

        self.metrics["mocks_generated"] += 1

        return {
            "status": "success",
            "mock_endpoints": len(mock_responses),
            "server_file": str(output_path),
            "api_type": api_spec.api_type.value,
        }

    async def validate_api_spec(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Validate API specification"""
        spec_path = Path(context.get("spec_path", "openapi.yaml"))

        if not spec_path.exists():
            return {"status": "error", "error": "Specification file not found"}

        # Load specification
        with open(spec_path) as f:
            if spec_path.suffix == ".yaml":
                spec = yaml.safe_load(f)
            else:
                spec = json.load(f)

        # Validate based on type
        if "openapi" in spec:
            self.openapi_gen.spec = spec
            is_valid, errors = self.openapi_gen.validate_spec()
        else:
            is_valid = False
            errors = ["Unknown specification format"]

        return {
            "status": "success" if is_valid else "error",
            "valid": is_valid,
            "errors": errors,
            "spec_type": "OpenAPI" if "openapi" in spec else "Unknown",
        }

    async def add_api_versioning(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Add versioning strategy to API"""
        strategy = APIVersion(context.get("strategy", "url_path"))
        version = context.get("version", "v1")

        recommendations = []

        if strategy == APIVersion.URL_PATH:
            recommendations.append(f"Use URL path versioning: /api/{version}/resource")
            recommendations.append("Update base URL in specification")
        elif strategy == APIVersion.HEADER:
            recommendations.append(
                "Use header versioning: Accept: application/vnd.api+json;version=1"
            )
            recommendations.append("Add version parameter to Accept header")
        elif strategy == APIVersion.QUERY_PARAM:
            recommendations.append(
                f"Use query parameter: /api/resource?version={version}"
            )
            recommendations.append("Add version as optional query parameter")
        elif strategy == APIVersion.SUBDOMAIN:
            recommendations.append(f"Use subdomain: {version}.api.example.com")
            recommendations.append("Configure DNS and routing for version subdomains")

        return {
            "status": "success",
            "strategy": strategy.value,
            "version": version,
            "recommendations": recommendations,
        }

    async def generate_sdk(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SDK for API"""
        language = context.get("language", "javascript")
        api_name = context.get("api_name", "API")

        # Generate basic SDK structure
        if language == "javascript":
            sdk_code = f"""class {api_name}Client {{
    constructor(apiKey, baseUrl = 'https://api.example.com') {{
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
    }}
    
    async request(endpoint, options = {{}}) {{
        const response = await fetch(`${{this.baseUrl}}${{endpoint}}`, {{
            ...options,
            headers: {{
                'Authorization': `Bearer ${{this.apiKey}}`,
                'Content-Type': 'application/json',
                ...options.headers
            }}
        }});
        return response.json();
    }}
}}

module.exports = {api_name}Client;
"""
        elif language == "python":
            sdk_code = f"""import requests

class {api_name}Client:
    def __init__(self, api_key, base_url='https://api.example.com'):
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update({{
            'Authorization': f'Bearer {{api_key}}',
            'Content-Type': 'application/json'
        }})
    
    def request(self, endpoint, method='GET', **kwargs):
        url = f'{{self.base_url}}{{endpoint}}'
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
"""
        else:
            sdk_code = "# SDK generation not supported for this language"

        # Save SDK
        ext = "js" if language == "javascript" else "py"
        output_path = Path(context.get("output_path", f"{api_name.lower()}-sdk.{ext}"))
        output_path.write_text(sdk_code)

        return {"status": "success", "language": language, "sdk_file": str(output_path)}

    async def create_postman_collection(
        self, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create Postman collection from API spec"""
        api_name = context.get(
            "api_name",
            list(self.specifications.keys())[0] if self.specifications else None,
        )

        if not api_name or api_name not in self.specifications:
            return {"status": "error", "error": "API specification not found"}

        api_spec = self.specifications[api_name]

        # Create Postman collection
        collection = {
            "info": {
                "name": api_spec.title,
                "description": api_spec.description,
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "item": [],
        }

        # Add requests for each endpoint
        for endpoint in api_spec.endpoints:
            item = {
                "name": endpoint.description,
                "request": {
                    "method": endpoint.method,
                    "header": [],
                    "url": {
                        "raw": f"{{{{base_url}}}}{endpoint.path}",
                        "host": ["{{base_url}}"],
                        "path": endpoint.path.split("/")[1:],
                    },
                },
            }

            if endpoint.request_body:
                item["request"]["body"] = {
                    "mode": "raw",
                    "raw": json.dumps(
                        self.mock_gen._generate_from_schema(
                            endpoint.request_body.get("schema", {})
                        ),
                        indent=2,
                    ),
                }

            collection["item"].append(item)

        # Save collection
        output_path = Path(context.get("output_path", f"{api_name}-postman.json"))
        with open(output_path, "w") as f:
            json.dump(collection, f, indent=2)

        return {
            "status": "success",
            "collection_name": api_spec.title,
            "requests": len(collection["item"]),
            "output_path": str(output_path),
        }

    async def analyze_breaking_changes(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze breaking changes between API versions"""
        old_spec_path = Path(context.get("old_spec", "openapi-v1.yaml"))
        new_spec_path = Path(context.get("new_spec", "openapi-v2.yaml"))

        breaking_changes = []
        non_breaking_changes = []

        # Load specifications
        try:
            with open(old_spec_path) as f:
                old_spec = (
                    yaml.safe_load(f)
                    if old_spec_path.suffix == ".yaml"
                    else json.load(f)
                )
            with open(new_spec_path) as f:
                new_spec = (
                    yaml.safe_load(f)
                    if new_spec_path.suffix == ".yaml"
                    else json.load(f)
                )
        except FileNotFoundError as e:
            return {"status": "error", "error": str(e)}

        # Check for removed endpoints
        old_paths = set(old_spec.get("paths", {}).keys())
        new_paths = set(new_spec.get("paths", {}).keys())

        removed_paths = old_paths - new_paths
        if removed_paths:
            breaking_changes.append(f"Removed endpoints: {', '.join(removed_paths)}")

        # Check for changed parameters
        for path in old_paths & new_paths:
            old_ops = old_spec["paths"][path]
            new_ops = new_spec["paths"][path]

            for method in old_ops:
                if method in new_ops:
                    old_params = old_ops[method].get("parameters", [])
                    new_params = new_ops[method].get("parameters", [])

                    old_required = {p["name"] for p in old_params if p.get("required")}
                    new_required = {p["name"] for p in new_params if p.get("required")}

                    new_required_params = new_required - old_required
                    if new_required_params:
                        breaking_changes.append(
                            f"{method.upper()} {path}: New required parameters: {', '.join(new_required_params)}"
                        )

        # Check for added endpoints (non-breaking)
        added_paths = new_paths - old_paths
        if added_paths:
            non_breaking_changes.append(f"Added endpoints: {', '.join(added_paths)}")

        return {
            "status": "success",
            "breaking_changes": breaking_changes,
            "non_breaking_changes": non_breaking_changes,
            "is_backward_compatible": len(breaking_changes) == 0,
        }

    async def generate_api_documentation(
        self, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate API documentation"""
        api_name = context.get(
            "api_name",
            list(self.specifications.keys())[0] if self.specifications else None,
        )

        if not api_name or api_name not in self.specifications:
            return {"status": "error", "error": "API specification not found"}

        api_spec = self.specifications[api_name]

        # Generate markdown documentation
        doc = f"# {api_spec.title} API Documentation\n\n"
        doc += f"Version: {api_spec.version}\n\n"
        doc += f"{api_spec.description}\n\n"
        doc += f"Base URL: `{api_spec.base_url}`\n\n"

        # Group endpoints by tags
        endpoints_by_tag = {}
        for endpoint in api_spec.endpoints:
            for tag in endpoint.tags or ["General"]:
                if tag not in endpoints_by_tag:
                    endpoints_by_tag[tag] = []
                endpoints_by_tag[tag].append(endpoint)

        # Document each group
        for tag, endpoints in endpoints_by_tag.items():
            doc += f"## {tag}\n\n"

            for endpoint in endpoints:
                doc += f"### {endpoint.method} {endpoint.path}\n\n"
                doc += f"{endpoint.description}\n\n"

                if endpoint.parameters:
                    doc += "**Parameters:**\n\n"
                    for param in endpoint.parameters:
                        required = "required" if param.get("required") else "optional"
                        doc += f"- `{param['name']}` ({param.get('in', 'query')}, {required}): {param.get('description', '')}\n"
                    doc += "\n"

                if endpoint.request_body:
                    doc += "**Request Body:**\n\n```json\n"
                    example = self.mock_gen._generate_from_schema(
                        endpoint.request_body.get("schema", {})
                    )
                    doc += json.dumps(example, indent=2)
                    doc += "\n```\n\n"

                doc += "**Responses:**\n\n"
                for status_code, response in endpoint.responses.items():
                    doc += f"- `{status_code}`: {response.get('description', '')}\n"
                doc += "\n"

        # Save documentation
        output_path = Path(context.get("output_path", f"{api_name}-api-docs.md"))
        output_path.write_text(doc)

        return {
            "status": "success",
            "documentation_file": str(output_path),
            "endpoints_documented": len(api_spec.endpoints),
            "tags": list(endpoints_by_tag.keys()),
        }

    async def design_pagination(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Design pagination strategy"""
        strategy = context.get("strategy", "cursor")

        if strategy == "cursor":
            design = {
                "type": "Cursor-based pagination",
                "parameters": {
                    "cursor": "Opaque cursor for next page",
                    "limit": "Number of items per page",
                },
                "response": {
                    "data": "Array of items",
                    "cursor": {
                        "next": "Cursor for next page",
                        "previous": "Cursor for previous page",
                    },
                },
                "benefits": [
                    "Consistent results even with data changes",
                    "Better performance for large datasets",
                    "No skipped items",
                ],
            }
        elif strategy == "offset":
            design = {
                "type": "Offset-based pagination",
                "parameters": {
                    "offset": "Number of items to skip",
                    "limit": "Number of items per page",
                },
                "response": {
                    "data": "Array of items",
                    "total": "Total number of items",
                    "offset": "Current offset",
                    "limit": "Current limit",
                },
                "benefits": [
                    "Simple to implement",
                    "Easy to jump to specific pages",
                    "Intuitive for users",
                ],
            }
        else:
            design = {
                "type": "Page-based pagination",
                "parameters": {
                    "page": "Page number (1-indexed)",
                    "per_page": "Items per page",
                },
                "response": {
                    "data": "Array of items",
                    "page": "Current page",
                    "per_page": "Items per page",
                    "total_pages": "Total number of pages",
                },
                "benefits": [
                    "User-friendly",
                    "Easy navigation",
                    "Clear page boundaries",
                ],
            }

        return {"status": "success", "pagination_design": design}

    async def implement_rate_limiting(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Design rate limiting strategy"""
        strategy = context.get("strategy", "token_bucket")
        limits = context.get("limits", {"requests": 100, "window": 60})

        implementation = {
            "strategy": strategy,
            "limits": limits,
            "headers": {
                "X-RateLimit-Limit": str(limits["requests"]),
                "X-RateLimit-Remaining": "Remaining requests",
                "X-RateLimit-Reset": "Unix timestamp of reset",
            },
            "error_response": {
                "status": 429,
                "error": "Too Many Requests",
                "retry_after": limits["window"],
            },
        }

        if strategy == "token_bucket":
            implementation["details"] = {
                "algorithm": "Token bucket",
                "tokens": limits["requests"],
                "refill_rate": f"{limits['requests']} per {limits['window']} seconds",
                "burst_capacity": limits["requests"],
            }

        return {"status": "success", "rate_limiting": implementation}

    async def handle_unknown_command(
        self, command: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle unknown commands"""
        return {
            "status": "error",
            "error": f"Unknown command: {command}",
            "available_commands": [
                "design_rest_api",
                "design_graphql_api",
                "generate_openapi",
                "generate_graphql_schema",
                "create_contract_tests",
                "generate_mock_service",
                "validate_api_spec",
                "add_api_versioning",
                "generate_sdk",
                "create_postman_collection",
                "analyze_breaking_changes",
                "generate_api_documentation",
                "design_pagination",
                "implement_rate_limiting",
            ],
        }

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        return {
            "specs_generated": self.metrics["specs_generated"],
            "contracts_created": self.metrics["contracts_created"],
            "mocks_generated": self.metrics["mocks_generated"],
            "validation_success_rate": f"{self.metrics['validation_success_rate']:.1f}%",
        }

    def get_capabilities(self) -> List[str]:
        """Get APIDESIGNER capabilities"""
        return [
            "design_openapi_spec",
            "design_graphql_schema",
            "test_api_contracts",
            "generate_mock_services",
            "create_rest_endpoints",
            "implement_authentication",
            "design_webhooks",
            "implement_rate_limiting",
            "api_versioning",
            "specification_validation",
            "contract_testing",
            "mock_generation",
            "endpoint_design",
            "schema_design",
            "security_integration",
        ]

    def get_status(self) -> Dict[str, Any]:
        """Get APIDESIGNER status"""
        uptime = (datetime.now() - self.start_time).total_seconds()

        return {
            "agent_name": self.agent_name,
            "version": self.version,
            "status": "healthy",
            "uptime_seconds": uptime,
            "metrics": self.get_metrics(),
            "specifications": len(self.specifications),
            "capabilities": len(self.get_capabilities()),
            "components": {
                "openapi_generator": "operational",
                "graphql_generator": "operational",
                "contract_tester": "operational",
                "mock_generator": "operational",
            },
        }

    # Example usage

    async def _create_apidesigner_files(
        self, result_data: Dict[str, Any], context: Dict[str, Any]
    ):
        """Create apidesigner files and artifacts using declared tools"""
        try:
            import json
            import os
            import time
            from pathlib import Path

            # Create directories
            main_dir = Path("api_specifications")
            docs_dir = Path("api_documentation")

            os.makedirs(main_dir, exist_ok=True)
            os.makedirs(docs_dir / "endpoints", exist_ok=True)
            os.makedirs(docs_dir / "schemas", exist_ok=True)
            os.makedirs(docs_dir / "examples", exist_ok=True)
            os.makedirs(docs_dir / "tests", exist_ok=True)

            timestamp = int(time.time())

            # 1. Create main result file
            result_file = main_dir / f"apidesigner_result_{timestamp}.json"
            with open(result_file, "w") as f:
                json.dump(result_data, f, indent=2, default=str)

            # 2. Create implementation script
            script_file = docs_dir / "endpoints" / f"apidesigner_implementation.py"
            script_content = f'''#!/usr/bin/env python3
"""
APIDESIGNER Implementation Script
Generated by APIDESIGNER Agent at {datetime.now().isoformat()}
"""

import asyncio
import json
from typing import Dict, Any

class ApidesignerImplementation:
    """
    Implementation for apidesigner operations
    """
    
    def __init__(self):
        self.agent_name = "APIDESIGNER"
        self.result_data = result_data
        
    async def execute(self) -> Dict[str, Any]:
        """Execute apidesigner implementation"""
        print(f"Executing {self.agent_name} implementation")
        
        # Implementation logic here
        await asyncio.sleep(0.1)
        
        return {
            "status": "completed",
            "agent": self.agent_name,
            "execution_time": "{datetime.now().isoformat()}"
        }
        
    def get_artifacts(self) -> Dict[str, Any]:
        """Get created artifacts"""
        return {
            "files_created": [
                "openapi.yaml",
                "postman_collection.json",
                "api_tests.py"
            ],
            "directories": ['endpoints', 'schemas', 'examples', 'tests'],
            "description": "API specifications and documentation"
        }

if __name__ == "__main__":
    impl = ApidesignerImplementation()
    result = asyncio.run(impl.execute())
    print(f"Result: {result}")
'''

            with open(script_file, "w") as f:
                f.write(script_content)

            os.chmod(script_file, 0o755)

            # 3. Create README
            readme_content = f"""# APIDESIGNER Output

Generated by APIDESIGNER Agent at {datetime.now().isoformat()}

## Description
API specifications and documentation

## Files Created
- Main result: `{result_file.name}`
- Implementation: `{script_file.name}`

## Directory Structure
- `endpoints/` - endpoints related files
- `schemas/` - schemas related files
- `examples/` - examples related files
- `tests/` - tests related files

## Usage
```bash
# Run the implementation
python3 {script_file}

# View results
cat {result_file}
```

---
Last updated: {datetime.now().isoformat()}
"""

            with open(docs_dir / "README.md", "w") as f:
                f.write(readme_content)

            print(
                f"APIDESIGNER files created successfully in {main_dir} and {docs_dir}"
            )

        except Exception as e:
            print(f"Failed to create apidesigner files: {e}")


if __name__ == "__main__":

    async def main():
        executor = APIDESIGNERPythonExecutor()

        # Design REST API
        result = await executor.execute_command(
            "design_rest_api",
            {
                "name": "UserService",
                "description": "User management service",
                "base_url": "https://api.example.com/v1",
                "resources": [
                    {
                        "name": "User",
                        "schema": {
                            "type": "object",
                            "properties": {
                                "id": {"type": "string"},
                                "email": {"type": "string"},
                                "name": {"type": "string"},
                            },
                        },
                    }
                ],
            },
        )
        print(f"REST API design: {result}")

        # Generate OpenAPI spec
        openapi_result = await executor.execute_command(
            "generate_openapi", {"api_name": "UserService"}
        )
        print(f"OpenAPI generation: {openapi_result}")

        # Create contract tests
        contracts = await executor.execute_command(
            "create_contract_tests",
            {
                "api_name": "UserService",
                "consumer": "Frontend",
                "provider": "UserService",
            },
        )
        print(f"Contract tests: {contracts}")

        # Get metrics
        print(f"Metrics: {executor.get_metrics()}")

    asyncio.run(main())
