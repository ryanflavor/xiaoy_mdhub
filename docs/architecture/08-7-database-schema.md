### **7. Database Schema**

For a SQL implementation (MySQL), the `accounts` table will be structured as follows:

```sql
CREATE TABLE market_data_accounts (
    id VARCHAR(255) PRIMARY KEY,
    gateway_type VARCHAR(50) NOT NULL,
    settings JSON NOT NULL,
    priority INT NOT NULL DEFAULT 2,
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```
