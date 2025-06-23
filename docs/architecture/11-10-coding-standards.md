### **10. Coding Standards**

- **Type Sharing**: All types shared between the frontend (Next.js/TypeScript) and backend (data models sent over API) MUST be defined in the `packages/shared-types` directory to ensure consistency.
- **Environment Variables**: All sensitive information (API keys, database URIs, passwords) MUST be managed via environment variables and never be hardcoded. A `.env.example` file will be maintained.
- **API Communication**: The frontend must use a dedicated service layer (e.g., API client class) to communicate with the backend, abstracting away the `fetch` or `axios` calls.
