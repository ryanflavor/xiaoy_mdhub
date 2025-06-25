# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Local High-Availability Market Data Hub** - A robust, monorepo-based market data aggregation system for quantitative trading with automated failover between CTP and SOPT data sources. Built with Python 3.12 + FastAPI backend and Next.js 14 + TypeScript frontend.

## Architecture

**Modular Monolith** with clear separation:
- **Backend**: Python 3.12 + FastAPI + vnpy ecosystem + ZeroMQ publisher
- **Frontend**: Next.js 14 + TypeScript + Shadcn/ui + Zustand state management  
- **Data Distribution**: ZeroMQ with msgpack serialization (<5ms latency)
- **Databases**: MySQL + MongoDB + Redis
- **Deployment**: Docker containers with compose orchestration

Key services:
- `gateway_manager.py` - Manages CTP/SOPT gateway connections with failover
- `quote_aggregation_engine.py` - Data aggregation and failover logic
- `health_monitor.py` - System health monitoring with "canary" contracts
- `websocket_manager.py` - Real-time web communication
- `zmq_publisher.py` - High-performance tick data distribution

## Development Commands

### Monorepo Commands (run from root)
```bash
npm run dev              # Start all services in dev mode
npm run build            # Build all packages using Turbo
npm run lint             # Lint all packages  
npm run test             # Run all tests
npm run type-check       # TypeScript type checking across packages
npm run format           # Format code with Prettier
npm run clean            # Clean all build artifacts

# Service-specific development
npm run api:dev          # Start Python FastAPI backend
npm run web:dev          # Start Next.js frontend

# Installation and setup
npm run install:all      # Install all dependencies (Node.js + Python)
npm run install:api      # Install Python dependencies only
npm run setup:vnpy       # Install vnpy trading dependencies (Ubuntu 24.04)

# Docker operations
npm run docker:build     # Build Docker containers
npm run docker:up        # Start services with Docker Compose
npm run docker:down      # Stop Docker services
npm run local:setup      # Complete local development setup
```

### Frontend Commands (apps/web/)
```bash
npm run dev              # Next.js development server
npm run build            # Production build
npm run start            # Start production server
npm run lint             # ESLint checking
npm run type-check       # TypeScript type checking
npm run test             # Jest tests
```

### Backend Commands (apps/api/)
```bash
# Development server
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Code quality (no automated scripts - run manually)
pytest                   # Run test suite
black .                  # Code formatting
isort .                  # Import sorting
mypy .                   # Type checking
```

## Key Directories

```
apps/api/app/
├── api/routes/          # API endpoint definitions
├── services/            # Core business logic
│   ├── gateway_manager.py        # CTP/SOPT gateway management
│   ├── quote_aggregation_engine.py  # Data aggregation + failover
│   ├── health_monitor.py         # System health monitoring
│   ├── websocket_manager.py      # Real-time communication
│   └── zmq_publisher.py          # ZeroMQ data distribution
├── models/              # Database models and schemas
└── gateways/           # Trading gateway implementations

apps/web/src/
├── app/                # Next.js App Router pages
├── components/         # Reusable React components (Shadcn/ui)
├── services/           # API client and service layers
├── store/              # Zustand state management
└── hooks/              # Custom React hooks

packages/
├── shared-types/       # TypeScript interfaces shared between apps
├── ui/                 # Shared React component library
└── libs/               # vnpy_ctp and vnpy_sopt trading libraries
```

## Critical Dependencies

**Backend (Python 3.12):**
- `vnpy==4.0.0` - Core trading framework (fixed version)
- `vnpy_ctp==6.7.7.2` - CTP gateway (must be exact version)
- `vnpy_sopt==3.7.1.0` - SOPT options gateway (must be exact version)
- `fastapi==0.104.1` - Web framework
- `pyzmq==26.3.0` - ZeroMQ messaging
- `numpy>=2.2.3` - Required by vnpy 4.0.0

**Frontend:**
- `next==14.0.4` - React framework
- `typescript==5.3.2` - Type system
- `zustand==4.4.7` - State management
- Shadcn/ui component library (Radix UI primitives)

## Development Workflow

1. **Story-driven development** - All work starts with user stories in `docs/stories/`
2. **Type-first approach** - Shared types defined in `packages/shared-types/`
3. **Component-driven UI** - Reusable components in `packages/ui/`
4. **API-first backend** - OpenAPI documentation at `http://localhost:8000/docs`

## Code Quality Standards

- **TypeScript**: Strict mode enabled, no `any` types
- **Python**: Black formatting, isort imports, mypy type checking
- **Testing**: Jest (frontend), pytest (backend) with >80% coverage goal
- **Linting**: ESLint (TypeScript), flake8 (Python)

## Environment Setup

**Requirements:**
- Ubuntu 24.04 (target OS)
- Node.js >=18.0.0, npm >=8.0.0
- Python >=3.12
- Docker and Docker Compose

**Critical Setup Steps:**
1. Install vnpy system dependencies: `./scripts/install-vnpy-deps.sh`
2. Install vnpy components: `npm run setup:vnpy`
3. Copy environment files: `cp apps/api/.env.example apps/api/.env`
4. Install all dependencies: `npm run install:all`

## Agent Integration

This repository uses Cursor IDE agents with specialized roles:
- `@dev` - Full-stack developer for implementation
- `@architect` - System architect for design decisions
- Both follow story-centric development with sequential task execution

## URLs and Endpoints

- Web Dashboard: http://localhost:3000
- API Documentation: http://localhost:8000/docs  
- API Health: http://localhost:8000/health
- ZeroMQ Publisher: tcp://localhost:5555

## Testing Strategy

- **Unit Tests**: Individual component/service testing
- **Integration Tests**: API endpoint and database testing  
- **Performance Tests**: <5ms latency validation for tick data
- **Health Monitoring**: "Canary" contract validation for gateway health