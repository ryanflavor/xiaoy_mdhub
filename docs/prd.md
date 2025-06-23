### **Product Requirements Document: Local High-Availability Market Data Hub**

**Version**: 1.0
**Date**: June 23, 2025
**Author**: John, Product Manager

#### **Change Log**

| Date       | Version | Description                                              | Author |
| :--------- | :------ | :------------------------------------------------------- | :----- |
| 2025-06-23 | 1.0     | Initial draft created and approved through all sections. | John   |

### **1. Goals and Background Context**

#### **Goals**

The primary goals of this project are to:

- Increase the development efficiency of quantitative strategies.
- Ensure the continuous and stable operation of these trading strategies.
- Establish a robust and extensible foundation for future data services, such as bar generation or Greeks calculation.

#### **Background Context**

Directly relying on individual trading APIs like CTP or SOPT for quantitative strategies introduces significant operational risks. These include single points of failure, inconsistent data quality, unpredictable latency, and high management complexity for multiple accounts. This project aims to solve these pain points by creating a centralized, high-availability market data hub that provides a single, reliable, and cleansed stream of `TickData` to all internal strategies.

### **2. Requirements**

#### **Functional Requirements (FR)**

- **FR1**: The system must load its active account configurations from a database (which supports both MySQL and MongoDB).
- **FR2**: A web dashboard must provide an interface for users to enable or disable accounts in the active data source pool.
- **FR3**: The system must aggregate `TickData` from all active sources in the pool.
- **FR4**: For any given contract, the system must select and forward only the first-arriving tick to ensure lowest latency.
- **FR5**: The system must cleanse incoming data, discarding anomalous ticks with invalid prices or volumes.
- **FR6**: The system must monitor the health of each gateway by checking its direct connection status and by monitoring a data heartbeat from high-liquidity "canary" contracts.
- **FR7**: Upon detecting a health anomaly in a primary source, the system must automatically trigger a failover to a healthy backup source.
- **FR8**: Following a failure, the system must perform a "hard restart" (terminate and relaunch the process) of the failed gateway to ensure a clean reconnection.
- **FR9**: The system must distribute the final, aggregated `TickData` stream to clients over the LAN via a ZeroMQ PUB/SUB mechanism.
- **FR10**: The web dashboard must display the real-time operational status of each gateway in the pool.
- **FR11**: The web dashboard must display a real-time stream of system logs, which can be filtered by severity level (e.g., INFO, WARN, ERROR).
- **FR12**: The web dashboard must provide manual controls to start, stop, and "hard restart" individual gateways.

#### **Non-Functional Requirements (NFR)**

- **NFR1**: The entire application must be containerized using Docker for deployment.
- **NFR2**: The system's scheduled start and stop must be managed by a host-level `cron` job that controls the Docker container.
- **NFR3**: The backend service must be developed in **Python 3.12**.
- **NFR4**: The web dashboard frontend must be developed using Next.js and TypeScript.
- **NFR5**: The project must use the following pinned dependency versions: `vnpy` (v4.1.0), `vnpy_ctp` (v6.7.7.2), and `vnpy_sopt` (v3.7.1.0).
- **NFR6**: The system must achieve greater than 99.9% service availability.
- **NFR7**: The median end-to-end tick latency (from gateway ingress to client egress) must be below 5 milliseconds.
- **NFR8**: The web dashboard must be protected by a simple username and password authentication mechanism.
- **NFR9**: System events logged at the `ERROR` level must trigger an email notification to `ryanflavor@163.com`.

### **3. User Interface Design Goals**

#### **Overall UX Vision**

Our goal is to create a professional, data-dense, and highly responsive operations dashboard. The design will prioritize information clarity and control convenience over elaborate visual aesthetics. The core vision is to enable a user to quickly and accurately assess the health of the entire market data hub from a single interface and intervene when necessary.

#### **Key Interaction Paradigms**

- **Real-time Updates**: The dashboard's core data (gateway status, logs) must be pushed in real-time via WebSockets, eliminating the need for manual refreshes.
- **Direct Manipulation**: Users must be able to directly and instantly control backend services (e.g., start, stop gateways) via UI buttons.
- **Drill-Down Exploration**: Users should be able to click a high-level summary item (like an "error" status) to navigate to more detailed information (like specific error logs).

#### **Core Screens and Views**

1.  **Status Dashboard**: A central view showing the real-time health, priority, and key metrics for all gateways in the account pool.
2.  **Account Management**: An interface for managing the data source pool by enabling or disabling accounts stored in the database.
3.  **Log Viewer**: A dedicated view for streaming real-time system logs, with functionality to filter by severity level.

#### **Accessibility**

The project will target **WCAG 2.1 Level A** as a baseline, ensuring all interactive elements are keyboard-accessible and that color contrast is sufficient for a professional work environment.

#### **Branding**

A clean, professional "tech-ops" aesthetic will be used. The interface will feature a **dark mode** theme by default to reduce eye strain during long monitoring sessions.

#### **Target Device and Platforms**

The primary target is **desktop web browsers**, as the dashboard is intended for use on large-screen workstations. The design will be responsive to ensure usability on tablets as well.

### **4. Technical Assumptions**

#### **Repository Structure**

The project will use a **Monorepo** structure to manage the backend, frontend, and shared packages in a single repository, simplifying dependency management and code sharing.

#### **Service Architecture**

The MVP will be built as a **Modular Monolith**. The core service will run as a single, deployable Python application, but its internal logic will be separated into the distinct, loosely-coupled modules defined in the Project Brief.

#### **Testing requirements**

A layered testing strategy is required:

1.  **Unit Tests**: For core algorithms and utility functions.
2.  **Integration Tests**: For interactions between internal modules.
3.  **End-to-End (E2E) Tests**: For critical user workflows.

#### **Additional Technical Assumptions and Requests**

- **Backend**: Python 3.12, FastAPI.
- **Frontend**: TypeScript, Next.js, Shadcn/ui, Zustand.
- **Communication**: A hybrid model of REST API (for control) and WebSockets (for real-time data push).
- **Data Distribution**: ZeroMQ (pyzmq) for internal tick data distribution.
- **Database**: Support for both MySQL and MongoDB for account management.
- **Dependencies**: Pinned versions for `vnpy`, `vnpy_ctp`, `vnpy_sopt` are mandatory.
- **Deployment**: Must be deployed as a Docker container.
- **Scheduling**: System start/stop will be managed by a host-level `cron` job.

### **5. Epics**

#### **High-Level Plan**

- **Epic 1: Project Foundation & Core Service**: Establish the project skeleton and a minimal, end-to-end data pipeline from a single hardcoded source to a ZeroMQ publisher.
- **Epic 2: Database Integration & Web Account Management**: Replace hardcoded configurations with a dynamic, database-driven system, complete with a backend API and frontend UI for managing the account pool.
- **Epic 3: High-Availability & Failover Engine**: Implement the core intelligence, including health monitoring, automated failover logic, and the "hard restart" self-healing mechanism.
- **Epic 4: Full-Featured Monitoring Dashboard**: Build out the complete web interface with real-time status visualization, interactive controls, and the log viewer.

---

#### **Epic 1: Project Foundation & Core Service**

**Goal**: To build the project's skeleton and a minimal, end-to-end data pipeline: successfully receive `TickData` from a single hardcoded CTP account and publish it via ZeroMQ. This validates the core technical architecture.

- **Story 1.1: Project Scaffolding**
  - **As a** developer, **I want** to set up a standard Monorepo project structure with distinct packages for the backend, frontend, and shared code, **so that** we have a clean, organized, and scalable foundation for all future development.
  - **Acceptance Criteria**:
    1.  A new Git repository is initialized.
    2.  A root `package.json` is configured for workspaces.
    3.  The directory structure `apps/api`, `apps/web`, and `packages/shared` is created.
    4.  Basic `README.md` and `.gitignore` files are created.

- **Story 1.2: Core Service Application Shell**
  - **As a** the system, **I want** to initialize a basic FastAPI application within the `apps/api` package that can be started and stopped, **so that** we have a runnable server process to host all backend logic.
  - **Acceptance Criteria**:
    1.  `fastapi` and `uvicorn` are added as dependencies.
    2.  A `/health` endpoint is created that returns `{"status": "ok"}`.
    3.  The application can be successfully started.

- **Story 1.3: Single Account Tick Ingestion**
  - **As a** the system, **I want** to connect to a single, hardcoded CTP test account upon startup, **so that** I can establish a connection to a live data source and begin ingesting `TickData`.
  - **Acceptance Criteria**:
    1.  The service initializes a `vnpy_ctp` gateway instance using hardcoded credentials.
    2.  Connection status is logged to the console.
    3.  Received `TickData` for a subscribed test contract is logged to the console.

- **Story 1.4: ZMQ Tick Publishing**
  - **As a** a downstream client, **I want** to subscribe to a ZeroMQ endpoint and receive the `TickData` being ingested by the core service, **so that** the end-to-end data distribution pipeline is validated.
  - **Acceptance Criteria**:
    1.  A ZeroMQ PUB socket is bound to a configured port.
    2.  Each received tick is serialized using `msgpack`.
    3.  The serialized tick is published on a topic corresponding to its `vt_symbol`.
    4.  A separate test script can subscribe and successfully receive the ticks.

---

#### **Epic 2: Database Integration & Web Account Management**

**Goal**: To replace the hardcoded account logic with a dynamic, database-driven system, complete with a backend API and a frontend UI for managing the active account pool.

- **Story 2.1: Account Data Model & DB Connection**
  - **As a** developer, **I want** to define a data model for market data accounts and establish a reliable connection from the core service to a database, **so that** we have a persistent storage layer for all account configurations.
  - **Acceptance Criteria**:
    1.  An `MarketDataAccount` data model is defined in code.
    2.  The core service connects to the configured database on startup.
    3.  A database migration script is created to set up the `accounts` table.
    4.  A test account can be programmatically added and read.

- **Story 2.2: Account Management Backend API (CRUD)**
  - **As a** a frontend developer, **I want** to use a set of REST API endpoints to Create, Read, Update, and Delete (CRUD) account configurations, **so that** I can manage accounts programmatically.
  - **Acceptance Criteria**:
    1.  `POST /api/accounts` endpoint is created to add an account.
    2.  `GET /api/accounts` endpoint is created to list all accounts.
    3.  `PUT /api/accounts/{id}` endpoint is created to update an account.
    4.  `DELETE /api/accounts/{id}` endpoint is created to remove an account.
    5.  All endpoints are documented in the auto-generated Swagger UI.

- **Story 2.3: Service Integration with DB Accounts**
  - **As a** the system, **I want** to query the database on startup to get the list of active accounts, instead of using hardcoded credentials, **so that** my data source pool is dynamically configurable.
  - **Acceptance Criteria**:
    1.  Hardcoded account credentials from Epic 1 are removed.
    2.  On startup, the service queries the database for all accounts where `is_enabled` is true.
    3.  A gateway instance is initialized for each active account found.

- **Story 2.4: Frontend Account Management Page**
  - **As a** a system administrator, **I want** a page in the web dashboard where I can see all configured accounts and use a toggle to enable or disable them, **so that** I can easily manage the live data source pool.
  - **Acceptance Criteria**:
    1.  An "Account Management" page is created in the Next.js app.
    2.  The page fetches and displays all accounts from the `GET /api/accounts` API.
    3.  Each account has a toggle switch to update its `is_enabled` status via the `PUT /api/accounts/{id}` API.

---

#### **Epic 3: High-Availability & Failover Engine**

**Goal**: To implement the automated health monitoring and failover system, transforming the service into a truly resilient and reliable data hub.

- **Story 3.1: Health Monitoring Service**
  - **As a** the system, **I want** to continuously monitor the health of all active data sources using multiple dimensions, **so that** I can have a real-time, accurate understanding of each source's status.
  - **Acceptance Criteria**:
    1.  A `HealthMonitor` service module is created.
    2.  It maintains a state (`HEALTHY`, `UNHEALTHY`, etc.) for each active gateway.
    3.  It periodically checks the `vnpy` connection status and the "canary" contract heartbeat.
    4.  Any status change is logged and published to an internal event bus.

- **Story 3.2: Automated Failover Logic**
  - **As a** the system, **I want** the Quote Aggregation Engine to listen for health status changes and automatically switch to a backup data source when a primary source fails, **so that** downstream clients experience zero data interruption.
  - **Acceptance Criteria**:
    1.  The aggregation engine subscribes to gateway status events.
    2.  When a primary source is marked `UNHEALTHY`, the engine finds the next-highest priority healthy backup.
    3.  Contract subscriptions are seamlessly switched to the new backup source.
    4.  The failover event is logged in detail.

- **Story 3.3: "Hard Restart" Recovery Mechanism**
  - **As a** the system, **I want** to automatically attempt to recover a failed gateway by performing a full process restart, **so that** the system's redundancy can be restored without manual intervention.
  - **Acceptance Criteria**:
    1.  After a gateway is marked `UNHEALTHY`, a configurable cool-down period is triggered.
    2.  After the cool-down, the `GatewayManager` is instructed to terminate the failed gateway's process.
    3.  The `GatewayManager` then relaunches a new, clean process for that gateway.
    4.  The `HealthMonitor` tracks the recovery of the restarting gateway.

---

#### **Epic 4: Full-Featured Monitoring Dashboard**

**Goal**: To build the complete user-facing web interface, making the system's internal state transparent and providing full manual control to the user.

- **Story 4.1: Backend WebSocket Integration**
  - **As a** a frontend developer, **I want** a WebSocket endpoint on the FastAPI backend that continuously broadcasts system status events, **so that** the web dashboard can receive real-time data without polling.
  - **Acceptance Criteria**:
    1.  A `/ws` WebSocket endpoint is created in FastAPI.
    2.  Gateway status updates and system logs are pushed to all connected clients.
    3.  The Next.js frontend can successfully connect and receive messages.

- **Story 4.2: Main Status Dashboard UI**
  - **As a** a system administrator, **I want** to see a main dashboard page that visualizes the real-time status of all active gateways at a glance, **so that** I can quickly assess the overall health of the system.
  - **Acceptance Criteria**:
    1.  The main dashboard page is created in Next.js.
    2.  It displays each active gateway's ID, type, priority, and real-time health status received via WebSocket.
    3.  The "canary" contract monitor UI is implemented.
    4.  All UI components are built using `Shadcn/ui`.

- **Story 4.3: Interactive Gateway Controls**
  - **As a** a system administrator, **I want** to have "Start," "Stop," and "Hard Restart" buttons for each gateway on the dashboard, **so that** I can perform direct manual intervention.
  - **Acceptance Criteria**:
    1.  Control buttons are added to each gateway's display on the dashboard.
    2.  Clicking a button sends a REST API request to the backend (e.g., `POST /api/accounts/{id}/restart`).
    3.  The backend executes the requested action via the `GatewayManager`.
    4.  The dashboard UI is updated in real-time to reflect the new state.

- **Story 4.4: Real-time Log Viewer**
  - **As a** a system administrator, **I want** a dedicated log viewer page that displays a live stream of system logs with filtering capabilities, **so that** I can perform real-time monitoring and troubleshooting.
  - **Acceptance Criteria**:
    1.  A "Logs" page is created in Next.js.
    2.  It displays a real-time feed of log messages received via WebSocket.
    3.  UI controls are provided to filter logs by level (INFO, WARN, ERROR).
    4.  `ERROR` level logs are visually highlighted.

### **6. Checklist Results Report**

- **Executive Summary**: The PRD is assessed as highly complete and robust, with a "High" readiness for the architecture phase. Its key strengths are a clear MVP scope, a strong focus on high-availability, and detailed technical requirements.
- **Final Decision**: ✅ **READY FOR ARCHITECT**.
