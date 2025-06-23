# Story 1.1: Project Scaffolding

**Epic**: Epic 1 - Project Foundation & Core Service  
**Priority**: Critical (Blocks all other development)  
**Complexity**: Medium  
**Story ID**: 1.1

## User Story

**As a** developer,  
**I want** to set up a standard Monorepo project structure with distinct packages for the backend, frontend, and shared code,  
**so that** we have a clean, organized, and scalable foundation for all future development.

## Detailed Acceptance Criteria

### AC1: Initialize Git Repository
- [ ] Create new Git repository in current directory
- [ ] Add initial `.gitignore` with Python, Node.js, and Docker exclusions
- [ ] Create initial commit with project structure

### AC2: Configure Root Package.json
- [ ] Create root `package.json` with workspace configuration
- [ ] Configure scripts for monorepo management
- [ ] Set up Turborepo configuration in `turborepo.json`
- [ ] Include workspace paths: `"workspaces": ["apps/*", "packages/*"]`

### AC3: Create Monorepo Directory Structure
```
/
├── apps/
│   ├── api/          # Python/FastAPI Backend Service
│   └── web/          # Next.js Frontend Dashboard  
├── packages/
│   ├── shared-types/ # Shared TypeScript interfaces
│   └── ui/           # (Optional) Shared React components
├── docker-compose.yml # For local development
├── package.json       # Root package.json
└── turborepo.json     # Monorepo configuration
```

### AC4: Backend Package Foundation (apps/api/)
- [ ] Create `apps/api/` directory
- [ ] Add `requirements.txt` with FastAPI, uvicorn, vnpy dependencies
- [ ] Create basic Python package structure with `__init__.py`
- [ ] Add `pyproject.toml` or `setup.py` for package configuration

### AC5: Frontend Package Foundation (apps/web/)
- [ ] Create `apps/web/` directory  
- [ ] Initialize Next.js TypeScript project
- [ ] Add Shadcn/ui configuration
- [ ] Configure Zustand for state management

### AC6: Shared Packages Setup
- [ ] Create `packages/shared-types/` with TypeScript interfaces
- [ ] Create `packages/ui/` for shared components (optional)
- [ ] Configure proper TypeScript path resolution between packages

### AC7: Documentation Files
- [ ] Create comprehensive `README.md` with setup instructions
- [ ] Add `CONTRIBUTING.md` with development guidelines  
- [ ] Include architecture overview and getting started guide

## Technical Implementation Notes

### Dependencies to Install
**Backend**: 
- `fastapi==0.104.1`
- `uvicorn[standard]`
- `vnpy==4.1.0`
- `vnpy_ctp==6.7.7.2`
- `vnpy_sopt==3.7.1.0`

**Frontend**: 
- `next@latest`
- `typescript`
- `@types/node`
- `shadcn/ui`
- `zustand`

**Monorepo**: 
- `turbo`
- `npm-run-all`

### Key Configuration Files
- Root `package.json` must include workspace definitions
- `turborepo.json` for build pipeline configuration  
- Docker-compose setup for local development environment
- Proper `.gitignore` covering Python, Node.js, Docker artifacts

## Definition of Done
- [ ] Developer can run `npm install` at root and install all dependencies
- [ ] Both `apps/api` and `apps/web` directories exist with basic structure
- [ ] README provides clear setup and run instructions
- [ ] Git repository is properly initialized and configured
- [ ] Monorepo structure matches PRD specifications exactly

## Notes
- This story blocks all other Epic 1 development
- Must be completed before Story 1.2: Core Service Application Shell
- Architecture reference: docs/architecture/09-8-unified-project-structure-monorepo.md
- PRD reference: docs/prd/06-5-epics.md

---
**Created by**: Bob (Scrum Master)  
**Date**: 2025-06-23  
**Status**: Ready for Development