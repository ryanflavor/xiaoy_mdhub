### **4. Data Models**

The primary data model for configuration is the `MarketDataAccount`. It will be represented by the following structure, which can be mapped to both SQL and NoSQL databases.

```typescript
// Located in packages/shared/types.ts
export interface MarketDataAccount {
  id: string; // Unique identifier (e.g., 'ctp_main_account')
  gateway_type: "ctp" | "sopt";
  settings: {
    // vnpy gateway settings object
    userID?: string;
    password?: string;
    brokerID?: string;
    mdAddress?: string;
    tdAddress?: string;
    // ... other settings for SOPT etc.
  };
  priority: number; // Lower is higher priority (e.g., 1 is primary)
  is_enabled: boolean; // Whether the service should use this account
  description?: string; // Optional user-friendly name
}
```
