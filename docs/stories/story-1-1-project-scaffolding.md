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
- [x] Create new Git repository in current directory
- [x] Add initial `.gitignore` with Python, Node.js, and Docker exclusions
- [x] Create initial commit with project structure

### AC2: Configure Root Package.json
- [x] Create root `package.json` with workspace configuration
- [x] Configure scripts for monorepo management
- [x] Set up Turborepo configuration in `turbo.json`
- [x] Include workspace paths: `"workspaces": ["apps/*", "packages/*"]`

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
- [x] Create `apps/api/` directory
- [x] Add `requirements.txt` with FastAPI, uvicorn, vnpy dependencies
- [x] Create basic Python package structure with `__init__.py`
- [x] Add `pyproject.toml` for package configuration

### AC5: Frontend Package Foundation (apps/web/)
- [x] Create `apps/web/` directory  
- [x] Initialize Next.js TypeScript project
- [x] Add Shadcn/ui configuration
- [x] Configure Zustand for state management

### AC6: Shared Packages Setup
- [x] Create `packages/shared-types/` with TypeScript interfaces
- [x] Create `packages/ui/` for shared components (optional)
- [x] Configure proper TypeScript path resolution between packages

### AC7: Documentation Files
- [x] Create comprehensive `README.md` with setup instructions
- [x] Add `CONTRIBUTING.md` with development guidelines  
- [x] Include architecture overview and getting started guide

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