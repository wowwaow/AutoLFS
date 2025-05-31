---
template_version: 1.0
created_date: 2025-05-31
last_updated: 2025-05-31
supports_swagger: true
swagger_version: "3.0.0"
template_type: main
---

# {API_NAME} Documentation

## Overview
{Provide a high-level overview of your API, including its purpose and main features}

### Quick Reference
- **Base URL**: `{BASE_URL}`
- **Current Version**: `{API_VERSION}`
- **Support Status**: {SUPPORT_STATUS}
- **Security Protocol**: {SECURITY_PROTOCOL}

## Authentication & Authorization

### Authentication Methods
{List and describe supported authentication methods}

#### Method 1: {AUTH_METHOD_NAME}
- **Type**: {AUTH_TYPE}
- **Headers**:
  ```
  Authorization: Bearer {token}
  ```
- **Example**:
  ```curl
  curl -H "Authorization: Bearer your-token-here" {BASE_URL}/endpoint
  ```

### Authorization Levels
| Level | Access | Description |
|-------|---------|------------|
| {LEVEL_1} | {ACCESS_SCOPE} | {DESCRIPTION} |

## API Endpoints

### Endpoint Groups
1. [Group 1](#group-1)
2. [Group 2](#group-2)

### Group 1
{Include endpoint group description}

#### Endpoint 1
{Use ENDPOINT_TEMPLATE.md structure}

## Request/Response Formats

### Standard Request Format
```json
{
  "field1": "type",
  "field2": "type",
  "required_fields": ["field1"]
}
```

### Standard Response Format
```json
{
  "status": "success|error",
  "data": {},
  "message": "string",
  "timestamp": "ISO8601"
}
```

## Error Handling

### Error Response Format
```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "Human readable message",
  "details": {},
  "timestamp": "ISO8601"
}
```

### Common Error Codes
| Code | Message | Description |
|------|---------|------------|
| {ERROR_CODE} | {MESSAGE} | {DESCRIPTION} |

## Rate Limiting

### Limits
| Plan | Rate | Period | Burst |
|------|------|--------|-------|
| {PLAN} | {RATE} | {PERIOD} | {BURST} |

### Headers
```
X-RateLimit-Limit: {limit}
X-RateLimit-Remaining: {remaining}
X-RateLimit-Reset: {reset_time}
```

## Versioning

### Version History
| Version | Status | Released | EOL Date |
|---------|--------|----------|----------|
| {VERSION} | {STATUS} | {DATE} | {EOL_DATE} |

### Version Support Policy
{Describe version support policy and migration guidelines}

## Integration Examples

### Example 1: Basic Integration
```python
{EXAMPLE_CODE}
```

### Example 2: Authentication Flow
```javascript
{EXAMPLE_CODE}
```

## OpenAPI/Swagger Integration
```yaml
openapi: 3.0.0
info:
  title: {API_NAME}
  version: {API_VERSION}
paths:
  /{endpoint}:
    get:
      summary: {SUMMARY}
```

## Security Best Practices
1. {SECURITY_PRACTICE_1}
2. {SECURITY_PRACTICE_2}

## Related Documentation
- [Authentication Guide](./AUTH_TEMPLATE.md)
- [Error Codes Reference](./ERROR_TEMPLATE.md)
- [Integration Guide](./INTEGRATION_TEMPLATE.md)
- [Version History](./VERSION_TEMPLATE.md)

