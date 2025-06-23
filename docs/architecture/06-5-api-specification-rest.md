### **5. API Specification (REST)**

The backend will expose a REST API for management. The core endpoints are defined below.

```yaml
openapi: 3.0.0
info:
  title: Market Data Hub Management API
  version: 1.0.0
paths:
  /api/accounts:
    get:
      summary: List all configured accounts
      responses:
        "200":
          description: A list of MarketDataAccount objects.
    post:
      summary: Create a new account
      responses:
        "201":
          description: The newly created account.
  /api/accounts/{accountId}:
    put:
      summary: Update an existing account
      parameters:
        - name: accountId
          in: path
          required: true
          schema:
            type: string
      responses:
        "200":
          description: The updated account.
  /api/accounts/{accountId}/{action}:
    post:
      summary: Perform an action on a gateway
      parameters:
        - name: accountId
          in: path
          required: true
        - name: action
          in: path
          required: true
          schema:
            type: string
            enum: [start, stop, restart]
      responses:
        "202":
          description: Action accepted.
```
