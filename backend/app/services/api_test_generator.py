"""
API Test Generator - Parses OpenAPI/Swagger specs and generates test cases using LLM.
"""

import os
import json
import traceback
from typing import Dict, Any, List, Optional
from datetime import datetime

from app.services.llm_client import LLMClient
from app.utils.logger import get_logger

logger = get_logger(__name__)


class OpenAPISpecParser:
    """Parse and analyze OpenAPI/Swagger specification files."""

    @staticmethod
    def parse_spec(file_path: str) -> Dict[str, Any]:
        """
        Parse an OpenAPI spec file (JSON or YAML).

        Returns:
            Full parsed spec with endpoints, schemas, security info.
        """
        import yaml

        with open(file_path, 'r') as f:
            content = f.read()

        # Try JSON first, then YAML
        try:
            spec = json.loads(content)
        except json.JSONDecodeError:
            spec = yaml.safe_load(content)

        # Extract key information
        info = spec.get('info', {})
        servers = spec.get('servers', [])
        paths = spec.get('paths', {})
        components = spec.get('components', {})
        schemas = components.get('schemas', {})
        security_schemes = components.get('securitySchemes', {})

        endpoints = []
        for path, methods in paths.items():
            for method, details in methods.items():
                if method.upper() in ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS'):
                    endpoint = OpenAPISpecParser.extract_endpoint_details(spec, path, method)
                    endpoints.append(endpoint)

        relationships = OpenAPISpecParser.analyze_relationships(endpoints)

        return {
            'info': info,
            'servers': servers,
            'base_url': servers[0].get('url', '') if servers else '',
            'endpoints': endpoints,
            'schemas': schemas,
            'security_schemes': security_schemes,
            'security': spec.get('security', []),
            'relationships': relationships,
            'total_endpoints': len(endpoints)
        }

    @staticmethod
    def extract_endpoint_details(spec: dict, path: str, method: str) -> Dict[str, Any]:
        """Extract detailed information for a single endpoint."""
        details = spec['paths'][path][method]
        components = spec.get('components', {})
        schemas = components.get('schemas', {})

        # Extract parameters
        parameters = details.get('parameters', [])
        # Include path-level parameters
        path_params = spec['paths'][path].get('parameters', [])
        all_params = path_params + parameters

        # Extract request body schema
        request_body = None
        rb = details.get('requestBody', {})
        if rb:
            content = rb.get('content', {})
            for content_type, schema_info in content.items():
                schema = schema_info.get('schema', {})
                # Resolve $ref
                if '$ref' in schema:
                    ref_name = schema['$ref'].split('/')[-1]
                    schema = schemas.get(ref_name, schema)
                request_body = {
                    'content_type': content_type,
                    'schema': schema,
                    'required': rb.get('required', False)
                }
                break

        # Extract response schemas
        responses = {}
        for status_code, resp in details.get('responses', {}).items():
            resp_schema = None
            resp_content = resp.get('content', {})
            for ct, si in resp_content.items():
                s = si.get('schema', {})
                if '$ref' in s:
                    ref_name = s['$ref'].split('/')[-1]
                    s = schemas.get(ref_name, s)
                resp_schema = s
                break
            responses[status_code] = {
                'description': resp.get('description', ''),
                'schema': resp_schema
            }

        return {
            'path': path,
            'method': method.upper(),
            'operation_id': details.get('operationId', ''),
            'summary': details.get('summary', ''),
            'description': details.get('description', ''),
            'tags': details.get('tags', []),
            'parameters': all_params,
            'request_body': request_body,
            'responses': responses,
            'security': details.get('security', [])
        }

    @staticmethod
    def analyze_relationships(endpoints: List[Dict]) -> List[Dict]:
        """Detect CRUD chains and related endpoint groups."""
        relationships = []
        by_tag = {}

        for ep in endpoints:
            for tag in ep.get('tags', ['default']):
                by_tag.setdefault(tag, []).append(ep)

        for tag, eps in by_tag.items():
            methods = {ep['method'] for ep in eps}
            paths = [ep['path'] for ep in eps]

            # Detect CRUD patterns
            has_create = 'POST' in methods
            has_read = 'GET' in methods
            has_update = 'PUT' in methods or 'PATCH' in methods
            has_delete = 'DELETE' in methods

            if has_create and has_read:
                relationships.append({
                    'type': 'crud_chain',
                    'resource': tag,
                    'operations': list(methods),
                    'endpoints': [{'path': ep['path'], 'method': ep['method']} for ep in eps],
                    'has_full_crud': has_create and has_read and has_update and has_delete
                })

        return relationships

    @staticmethod
    def analyze_spec_info(file_path: str) -> Dict[str, Any]:
        """Quick summary analysis of spec for upload response."""
        try:
            spec = OpenAPISpecParser.parse_spec(file_path)
            methods_count = {}
            tags = set()

            for ep in spec['endpoints']:
                m = ep['method']
                methods_count[m] = methods_count.get(m, 0) + 1
                for t in ep.get('tags', []):
                    tags.add(t)

            return {
                'title': spec['info'].get('title', 'Unknown API'),
                'version': spec['info'].get('version', ''),
                'total_endpoints': spec['total_endpoints'],
                'methods': methods_count,
                'tags': list(tags),
                'base_url': spec.get('base_url', ''),
                'has_security': bool(spec.get('security_schemes')),
                'schema_count': len(spec.get('schemas', {})),
                'relationships': len(spec.get('relationships', []))
            }
        except Exception as e:
            logger.error(f"Error analyzing spec: {e}")
            return {
                'title': 'Parse Error',
                'total_endpoints': 0,
                'error': str(e)
            }


class APITestGenerator(LLMClient):
    """Generate API test cases using LLM based on OpenAPI specs."""

    @staticmethod
    def _compact_endpoint(endpoint: Dict) -> Dict:
        """
        Reduce endpoint payload size while preserving test-critical information.
        Keeps: path, method, params, request body schema, response status codes.
        Trims: full response body schemas (replaced with status + description).
        """
        compact = {
            'path': endpoint.get('path'),
            'method': endpoint.get('method'),
            'operation_id': endpoint.get('operation_id', ''),
            'summary': endpoint.get('summary', ''),
            'parameters': endpoint.get('parameters', []),
            'security': endpoint.get('security', []),
        }

        # Keep full request body schema — critical for generating valid test payloads
        rb = endpoint.get('request_body')
        if rb:
            schema = rb.get('schema', {})
            # Trim deeply nested properties beyond 2 levels to control size
            compact['request_body'] = {
                'content_type': rb.get('content_type', 'application/json'),
                'required': rb.get('required', False),
                'schema': APITestGenerator._trim_schema_depth(schema, max_depth=3),
            }

        # For responses, keep status codes + descriptions but drop large body schemas
        compact_responses = {}
        for status_code, resp in endpoint.get('responses', {}).items():
            resp_entry = {'description': resp.get('description', '')}
            # Only include top-level property names from response schema, not full tree
            resp_schema = resp.get('schema')
            if resp_schema and isinstance(resp_schema, dict):
                props = resp_schema.get('properties', {})
                if props:
                    resp_entry['response_fields'] = list(props.keys())
                resp_type = resp_schema.get('type')
                if resp_type:
                    resp_entry['type'] = resp_type
            compact_responses[status_code] = resp_entry
        compact['responses'] = compact_responses

        return compact

    @staticmethod
    def _trim_schema_depth(schema: dict, max_depth: int, current_depth: int = 0) -> dict:
        """Recursively trim a JSON schema to a maximum nesting depth."""
        if not isinstance(schema, dict) or current_depth >= max_depth:
            if isinstance(schema, dict):
                # At max depth, summarize: keep type + required + enum only
                summary = {}
                if 'type' in schema:
                    summary['type'] = schema['type']
                if 'enum' in schema:
                    summary['enum'] = schema['enum']
                if 'required' in schema:
                    summary['required'] = schema['required']
                if 'format' in schema:
                    summary['format'] = schema['format']
                return summary or schema
            return schema

        result = {}
        for key, value in schema.items():
            if key == 'properties' and isinstance(value, dict):
                result[key] = {
                    prop_name: APITestGenerator._trim_schema_depth(
                        prop_schema, max_depth, current_depth + 1
                    )
                    for prop_name, prop_schema in value.items()
                }
            elif key == 'items' and isinstance(value, dict):
                result[key] = APITestGenerator._trim_schema_depth(
                    value, max_depth, current_depth + 1
                )
            elif key in ('oneOf', 'anyOf', 'allOf') and isinstance(value, list):
                result[key] = [
                    APITestGenerator._trim_schema_depth(
                        item, max_depth, current_depth + 1
                    ) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    @staticmethod
    def _get_relevant_schemas(endpoint: Dict, all_schemas: Dict) -> Dict:
        """Extract only schemas referenced by this endpoint instead of dumping all."""
        # Collect $ref names from the endpoint's raw JSON
        endpoint_str = json.dumps(endpoint, default=str)
        relevant = {}
        for schema_name, schema_def in all_schemas.items():
            if schema_name in endpoint_str:
                relevant[schema_name] = APITestGenerator._trim_schema_depth(schema_def, max_depth=2)
        # If nothing matched by name, return a trimmed subset of all schemas
        if not relevant:
            for name, schema_def in list(all_schemas.items())[:10]:
                relevant[name] = APITestGenerator._trim_schema_depth(schema_def, max_depth=1)
        return relevant

    @staticmethod
    def _compact_relationships(relationships: List[Dict]) -> List[Dict]:
        """Reduce relationship payload to essential info for flow test generation."""
        compact = []
        for rel in relationships:
            compact.append({
                'type': rel.get('type', ''),
                'resource': rel.get('resource', ''),
                'operations': rel.get('operations', []),
                'has_full_crud': rel.get('has_full_crud', False),
                'endpoints': [
                    {'path': ep['path'], 'method': ep['method']}
                    for ep in rel.get('endpoints', [])
                ],
            })
        return compact

    def generate_tests_for_endpoint(
        self,
        endpoint: Dict,
        schemas: Dict,
        relationships: List[Dict],
        categories: List[str]
    ) -> List[Dict]:
        """Generate test cases for a single endpoint."""
        system_prompt = (
            "You are an expert API test engineer. Generate comprehensive test cases "
            "for REST API endpoints. Return valid JSON only."
        )

        compact_ep = self._compact_endpoint(endpoint)
        relevant_schemas = self._get_relevant_schemas(endpoint, schemas)

        endpoint_desc = json.dumps(compact_ep, indent=2, default=str)
        schemas_desc = json.dumps(relevant_schemas, indent=2, default=str)

        user_prompt = f"""Generate test cases for this API endpoint:

{endpoint_desc}

Available schemas:
{schemas_desc}

Generate tests for these categories: {', '.join(categories)}

Return a JSON array of test objects with this structure:
[
  {{
    "name": "Test name",
    "category": "positive|negative|edge_case|security|rate_limit|pagination|idempotency",
    "method": "GET|POST|PUT|DELETE|PATCH",
    "path": "/actual/path/with/values",
    "description": "What this test validates",
    "request": {{
      "headers": {{}},
      "query_params": {{}},
      "path_params": {{}},
      "body": null
    }},
    "expected": {{
      "status_code": 200,
      "response_contains": [],
      "response_not_contains": []
    }}
  }}
]

Generate 3-5 tests per selected category. Use realistic test data."""

        try:
            result = self.call(system_prompt, user_prompt, expect_json=True)
            tests = []
            if isinstance(result, list):
                tests = result
            elif isinstance(result, dict) and 'tests' in result:
                tests = result['tests'] if isinstance(result['tests'], list) else []
            # Filter out any non-dict items the LLM may have returned
            return [t for t in tests if isinstance(t, dict)]
        except Exception as e:
            logger.error(f"Error generating tests for {endpoint['method']} {endpoint['path']}: {e}")
            return []

    def generate_relationship_tests(
        self,
        relationships: List[Dict],
        schemas: Dict
    ) -> List[Dict]:
        """Generate cross-endpoint CRUD flow tests."""
        if not relationships:
            return []

        system_prompt = (
            "You are an expert API test engineer specializing in integration testing. "
            "Generate test flows that test relationships between endpoints. Return valid JSON only."
        )

        compact_rels = self._compact_relationships(relationships)
        # Only include schemas whose names appear in relationship resources
        rel_str = json.dumps(compact_rels, default=str)
        relevant_schemas = {
            name: APITestGenerator._trim_schema_depth(defn, max_depth=2)
            for name, defn in schemas.items()
            if name.lower() in rel_str.lower()
        }
        # Fallback: include first few schemas if none matched
        if not relevant_schemas:
            for name, defn in list(schemas.items())[:8]:
                relevant_schemas[name] = APITestGenerator._trim_schema_depth(defn, max_depth=1)

        rel_desc = json.dumps(compact_rels, indent=2, default=str)
        schemas_desc = json.dumps(relevant_schemas, indent=2, default=str)

        user_prompt = f"""Generate integration test flows for these endpoint relationships:

{rel_desc}

Schemas: {schemas_desc}

Return a JSON array of flow tests:
[
  {{
    "name": "CRUD flow test name",
    "category": "relationship",
    "description": "What this flow validates",
    "steps": [
      {{
        "step": 1,
        "action": "Create resource",
        "method": "POST",
        "path": "/resources",
        "body": {{}},
        "expected_status": 201,
        "save_from_response": {{"id": "$.id"}}
      }},
      {{
        "step": 2,
        "action": "Verify creation",
        "method": "GET",
        "path": "/resources/{{id}}",
        "expected_status": 200
      }}
    ]
  }}
]

Generate 2-3 relationship flow tests."""

        try:
            result = self.call(system_prompt, user_prompt, expect_json=True)
            flows = []
            if isinstance(result, list):
                flows = result
            elif isinstance(result, dict) and 'flows' in result:
                flows = result['flows'] if isinstance(result['flows'], list) else []
            # Filter out any non-dict items the LLM may have returned
            return [f for f in flows if isinstance(f, dict)]
        except Exception as e:
            logger.error(f"Error generating relationship tests: {e}")
            return []

    @staticmethod
    def format_as_postman_collection(
        tests: List[Dict],
        flow_tests: List[Dict],
        spec_info: Dict
    ) -> Dict:
        """Format tests as a Postman Collection v2.1."""
        items = []

        # Group tests by category (skip any non-dict items)
        by_category = {}
        for test in tests:
            if not isinstance(test, dict):
                continue
            cat = test.get('category', 'general')
            by_category.setdefault(cat, []).append(test)

        for category, cat_tests in by_category.items():
            folder_items = []
            for test in cat_tests:
                request_body = test.get('request', {}).get('body')
                item = {
                    'name': test.get('name', 'Unnamed Test'),
                    'request': {
                        'method': test.get('method', 'GET'),
                        'header': [
                            {'key': k, 'value': v}
                            for k, v in test.get('request', {}).get('headers', {}).items()
                        ],
                        'url': {
                            'raw': f"{{{{baseUrl}}}}{test.get('path', '/')}",
                            'host': ['{{baseUrl}}'],
                            'path': [p for p in test.get('path', '/').split('/') if p]
                        }
                    }
                }

                if request_body:
                    item['request']['body'] = {
                        'mode': 'raw',
                        'raw': json.dumps(request_body, indent=2),
                        'options': {'raw': {'language': 'json'}}
                    }

                # Add test script
                expected = test.get('expected', {})
                expected_status = expected.get('status_code', 200)
                item['event'] = [{
                    'listen': 'test',
                    'script': {
                        'type': 'text/javascript',
                        'exec': [
                            f'pm.test("{test.get("name", "Test")}", function () {{',
                            f'    pm.response.to.have.status({expected_status});',
                            '});'
                        ]
                    }
                }]

                folder_items.append(item)

            items.append({
                'name': category.replace('_', ' ').title(),
                'item': folder_items
            })

        # Add flow tests as a folder
        if flow_tests:
            flow_items = []
            for flow in flow_tests:
                if not isinstance(flow, dict):
                    continue
                for step in flow.get('steps', []):
                    flow_items.append({
                        'name': f"{flow.get('name', 'Flow')} - Step {step.get('step', '?')}: {step.get('action', '')}",
                        'request': {
                            'method': step.get('method', 'GET'),
                            'url': {
                                'raw': f"{{{{baseUrl}}}}{step.get('path', '/')}",
                                'host': ['{{baseUrl}}'],
                                'path': [p for p in step.get('path', '/').split('/') if p]
                            }
                        }
                    })
            items.append({
                'name': 'Relationship Flow Tests',
                'item': flow_items
            })

        return {
            'info': {
                'name': f"{spec_info.get('title', 'API')} - Test Suite",
                'description': f"Auto-generated test suite for {spec_info.get('title', 'API')}",
                'schema': 'https://schema.getpostman.com/json/collection/v2.1.0/collection.json'
            },
            'variable': [
                {
                    'key': 'baseUrl',
                    'value': spec_info.get('base_url', 'http://localhost:3000'),
                    'type': 'string'
                }
            ],
            'item': items
        }

    @staticmethod
    def format_as_json_suite(
        tests: List[Dict],
        flow_tests: List[Dict],
        spec_info: Dict
    ) -> Dict:
        """Format tests as a generic JSON test suite."""
        return {
            'suite_name': f"{spec_info.get('title', 'API')} Test Suite",
            'generated_at': datetime.utcnow().isoformat(),
            'api_info': spec_info,
            'total_tests': len(tests),
            'total_flows': len(flow_tests),
            'tests': tests,
            'flow_tests': flow_tests
        }


def generate_api_tests_background(job_id: str, spec_path: str, config: dict):
    """Background task for API test generation."""
    from app.db.database import SessionLocal, Job, JobStatusEnum
    from dotenv import load_dotenv

    load_dotenv()
    db = SessionLocal()

    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return

        # Parse spec
        job.progress = 5
        job.message = "Parsing OpenAPI specification..."
        db.commit()

        spec = OpenAPISpecParser.parse_spec(spec_path)
        endpoints = spec['endpoints']
        schemas = spec['schemas']
        relationships = spec['relationships']

        job.progress = 10
        job.message = f"Found {len(endpoints)} endpoints, generating tests..."
        db.commit()

        # Initialize generator
        api_key = config.get('gpt_api_key') or os.getenv('OPENAI_API_KEY')
        gpt_model = config.get('gpt_model', 'gpt-4o-mini')
        gpt_endpoint = config.get('gpt_endpoint')

        generator = APITestGenerator(
            api_key=api_key,
            api_endpoint=gpt_endpoint,
            model=gpt_model
        )

        categories = config.get('test_categories', ['positive', 'negative'])

        # Generate tests per endpoint (batch by 5)
        all_tests = []
        batch_size = 5
        total_batches = (len(endpoints) + batch_size - 1) // batch_size

        for batch_idx in range(total_batches):
            start = batch_idx * batch_size
            end = min(start + batch_size, len(endpoints))
            batch = endpoints[start:end]

            for ep in batch:
                tests = generator.generate_tests_for_endpoint(ep, schemas, relationships, categories)
                all_tests.extend(tests)

            progress = 10 + (70 * (batch_idx + 1) / total_batches)
            job.progress = int(progress)
            job.message = f"Generated tests for {end}/{len(endpoints)} endpoints..."
            db.commit()

        # Generate relationship tests
        job.progress = 80
        job.message = "Generating relationship flow tests..."
        db.commit()

        flow_tests = generator.generate_relationship_tests(relationships, schemas)

        # Filter to only valid dict items with required fields
        all_tests = [t for t in all_tests if isinstance(t, dict) and t.get('method') and t.get('path')]
        flow_tests = [f for f in flow_tests if isinstance(f, dict)]

        job.progress = 90
        job.message = "Formatting output..."
        db.commit()

        # Format outputs
        spec_info = {
            'title': spec['info'].get('title', 'API'),
            'version': spec['info'].get('version', ''),
            'base_url': config.get('base_url', spec.get('base_url', '')),
            'total_endpoints': len(endpoints)
        }

        postman_collection = APITestGenerator.format_as_postman_collection(all_tests, flow_tests, spec_info)
        json_suite = APITestGenerator.format_as_json_suite(all_tests, flow_tests, spec_info)

        # Save outputs
        output_dir = os.path.join("outputs", job_id)
        os.makedirs(output_dir, exist_ok=True)

        postman_path = os.path.join(output_dir, "postman_collection.json")
        with open(postman_path, 'w') as f:
            json.dump(postman_collection, f, indent=2)

        json_suite_path = os.path.join(output_dir, "test_suite.json")
        with open(json_suite_path, 'w') as f:
            json.dump(json_suite, f, indent=2)

        # Save results summary
        results = {
            'total_tests': len(all_tests),
            'total_flows': len(flow_tests),
            'endpoints_covered': len(set(f"{t.get('method', '')} {t.get('path', '')}" for t in all_tests)),
            'categories': {},
            'endpoint_coverage': [],
            'sample_tests': all_tests[:10],
            'sample_flows': flow_tests[:3],
            'spec_info': spec_info,
            'output_format': config.get('output_format', 'postman')
        }

        # Count by category
        for test in all_tests:
            cat = test.get('category', 'general')
            results['categories'][cat] = results['categories'].get(cat, 0) + 1

        # Endpoint coverage
        ep_tests = {}
        for test in all_tests:
            key = f"{test.get('method', '')} {test.get('path', '')}"
            ep_tests[key] = ep_tests.get(key, 0) + 1

        results['endpoint_coverage'] = [
            {'endpoint': k, 'test_count': v}
            for k, v in ep_tests.items()
        ]

        results_path = os.path.join(output_dir, "results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        job.progress = 100
        job.status = JobStatusEnum.COMPLETED
        job.message = f"Generated {len(all_tests)} tests for {len(endpoints)} endpoints"
        job.rows_generated = len(all_tests)
        job.completed_at = datetime.utcnow()
        db.commit()

    except Exception as e:
        logger.error(f"API test generation failed: {e}")
        traceback.print_exc()
        if job:
            job.status = JobStatusEnum.FAILED
            job.error = str(e)[:500]
            job.message = f"Failed: {str(e)[:200]}"
            db.commit()
    finally:
        db.close()
