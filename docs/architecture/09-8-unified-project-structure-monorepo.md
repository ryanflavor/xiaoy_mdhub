### **8. Unified Project Structure (Monorepo)**

```
/
├── apps/
│   ├── api/          # Python/FastAPI Backend Service
│   └── web/          # Next.js Frontend Dashboard
├── packages/
│   ├── shared-types/ # Shared TypeScript interfaces (e.g., MarketDataAccount)
│   └── ui/           # (Optional) Shared React components
├── docker-compose.yml # For local development environment
├── package.json       # Root package.json for monorepo scripts
└── turborepo.json     # Monorepo configuration
```
