---
template_version: 1.0
created_date: 2025-05-31
last_updated: 2025-05-31
endpoint_type: REST
supports_swagger: true
---

# {ENDPOINT_NAME}

## Overview
**Endpoint**: `{HTTP_METHOD} {ENDPOINT_PATH}`
**Purpose**: {ENDPOINT_PURPOSE}
**Group**: {ENDPOINT_GROUP}

## Authentication
- **Required**: {YES/NO}
- **Type**: {AUTH_TYPE}
- **Scopes**: {AUTH_SCOPES}

## Request

### Path Parameters
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| {PARAM} | {TYPE} | {YES/NO} | {DESCRIPTION} |

### Query Parameters
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| {PARAM} | {TYPE} | {YES/NO} | {DEFAULT} | {DESCRIPTION} |

### Headers
```
{REQUIRED_HEADERS}
Content-Type: application/json
Authorization: Bearer {token}
```

### Request Body
```json
{
  "field1": "type",
  "field2": "type",
  "required_fields": ["field1"]
}
```

### Example Request
```curl
curl -X {METHOD} \
  "{BASE_URL}{ENDPOINT_PATH}" \
  -H "Authorization: Bearer {token}" \
  -H "Content-Type: application/json" \
  -d '{REQUEST_BODY}'
```

## Response

### Success Response
**Status Code**: `{SUCCESS_CODE}`

```json
{
  "status": "success",
  "data": {
    "field1": "value1",
    "field2": "value2"
  }
}
```

### Error Responses
| Status Code | Error Code | Description |
|-------------|------------|-------------|
| {CODE} | {ERROR_CODE} | {DESCRIPTION} |

### Example Error Response
```json
{
  "status": "error",
  "code": "ERROR_CODE",
  "message": "Error description"
}
```

## Rate Limiting
- **Plan Limits**: {RATE_LIMITS}
- **Burst Allowed**: {YES/NO}

## Examples

### Python
```python
{PYTHON_EXAMPLE}
```

### JavaScript
```javascript
{JS_EXAMPLE}
```

### Swagger/OpenAPI
```yaml
paths:
  {ENDPOINT_PATH}:
    {METHOD}:
      summary: {SUMMARY}
      parameters:
        - name: {PARAM}
          in: {LOCATION}
          required: {REQUIRED}
          schema:
            type: {TYPE}
```

## Notes
- {IMPORTANT_NOTE_1}
- {IMPORTANT_NOTE_2}

## Related Documentation
- [Authentication](./AUTH_TEMPLATE.md)
- [Error Codes](./ERROR_TEMPLATE.md)
- [Rate Limiting](./RATE_LIMIT_GUIDE.md)

