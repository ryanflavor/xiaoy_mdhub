### **5. Epics**

#### **High-Level Plan**

* **Epic 1: Project Foundation & Core Service**: Establish the project skeleton and a minimal, end-to-end data pipeline from a single hardcoded source to a ZeroMQ publisher.
* **Epic 2: Database Integration & Web Account Management**: Replace hardcoded configurations with a dynamic, database-driven system, complete with a backend API and frontend UI for managing the account pool.
* **Epic 3: High-Availability & Failover Engine**: Implement the core intelligence, including health monitoring, automated failover logic, and the "hard restart" self-healing mechanism.
* **Epic 4: Full-Featured Monitoring Dashboard**: Build out the complete web interface with real-time status visualization, interactive controls, and the log viewer.

***

#### **Epic 1: Project Foundation & Core Service**

**Goal**: To build the project's skeleton and a minimal, end-to-end data pipeline: successfully receive `TickData` from a single hardcoded CTP account and publish it via ZeroMQ. This validates the core technical architecture.

* **Story 1.1: Project Scaffolding**
  * **As a** developer, **I want** to set up a standard Monorepo project structure with distinct packages for the backend, frontend, and shared code, **so that** we have a clean, organized, and scalable foundation for all future development.
  * **Acceptance Criteria**:
    1. A new Git repository is initialized.
    2. A root `package.json` is configured for workspaces.
    3. The directory structure `apps/api`, `apps/web`, and `packages/shared` is created.
    4. Basic `README.md` and `.gitignore` files are created.

* **Story 1.2: Core Service Application Shell**
  * **As a** the system, **I want** to initialize a basic FastAPI application within the `apps/api` package that can be started and stopped, **so that** we have a runnable server process to host all backend logic.
  * **Acceptance Criteria**:
    1. `fastapi` and `uvicorn` are added as dependencies.
    2. A `/health` endpoint is created that returns `{"status": "ok"}`.
    3. The application can be successfully started.

* **Story 1.3: Single Account Tick Ingestion**
  * **As a** the system, **I want** to connect to a single, hardcoded CTP test account upon startup, **so that** I can establish a connection to a live data source and begin ingesting `TickData`.
  * **Acceptance Criteria**:
    1. The service initializes a `vnpy_ctp` gateway instance using hardcoded credentials.
    2. Connection status is logged to the console.
    3. Received `TickData` for a subscribed test contract is logged to the console.

* **Story 1.4: ZMQ Tick Publishing**
  * **As a** a downstream client, **I want** to subscribe to a ZeroMQ endpoint and receive the `TickData` being ingested by the core service, **so that** the end-to-end data distribution pipeline is validated.
  * **Acceptance Criteria**:
    1. A ZeroMQ PUB socket is bound to a configured port.
    2. Each received tick is serialized using `msgpack`.
    3. The serialized tick is published on a topic corresponding to its `vt_symbol`.
    4. A separate test script can subscribe and successfully receive the ticks.

***

#### **Epic 2: Database Integration & Web Account Management**

**Goal**: To replace the hardcoded account logic with a dynamic, database-driven system, complete with a backend API and a frontend UI for managing the active account pool.

* **Story 2.1: Account Data Model & DB Connection**
  * **As a** developer, **I want** to define a data model for market data accounts and establish a reliable connection from the core service to a database, **so that** we have a persistent storage layer for all account configurations.
  * **Acceptance Criteria**:
    1. An `MarketDataAccount` data model is defined in code.
    2. The core service connects to the configured database on startup.
    3. A database migration script is created to set up the `accounts` table.
    4. A test account can be programmatically added and read.

* **Story 2.2: Account Management Backend API (CRUD)**
  * **As a** a frontend developer, **I want** to use a set of REST API endpoints to Create, Read, Update, and Delete (CRUD) account configurations, **so that** I can manage accounts programmatically.
  * **Acceptance Criteria**:
    1. `POST /api/accounts` endpoint is created to add an account.
    2. `GET /api/accounts` endpoint is created to list all accounts.
    3. `PUT /api/accounts/{id}` endpoint is created to update an account.
    4. `DELETE /api/accounts/{id}` endpoint is created to remove an account.
    5. All endpoints are documented in the auto-generated Swagger UI.

* **Story 2.3: Service Integration with DB Accounts**
  * **As a** the system, **I want** to query the database on startup to get the list of active accounts, instead of using hardcoded credentials, **so that** my data source pool is dynamically configurable.
  * **Acceptance Criteria**:
    1. Hardcoded account credentials from Epic 1 are removed.
    2. On startup, the service queries the database for all accounts where `is_enabled` is true.
    3. A gateway instance is initialized for each active account found.

* **Story 2.4: Frontend Account Management Page**
  * **As a** a system administrator, **I want** a page in the web dashboard where I can see all configured accounts and use a toggle to enable or disable them, **so that** I can easily manage the live data source pool.
  * **Acceptance Criteria**:
    1. An "Account Management" page is created in the Next.js app.
    2. The page fetches and displays all accounts from the `GET /api/accounts` API.
    3. Each account has a toggle switch to update its `is_enabled` status via the `PUT /api/accounts/{id}` API.

***

#### **Epic 3: High-Availability & Failover Engine**

**Goal**: To implement the automated health monitoring and failover system, transforming the service into a truly resilient and reliable data hub.

* **Story 3.1: Health Monitoring Service**
  * **As a** the system, **I want** to continuously monitor the health of all active data sources using multiple dimensions, **so that** I can have a real-time, accurate understanding of each source's status.
  * **Acceptance Criteria**:
    1. A `HealthMonitor` service module is created.
    2. It maintains a state (`HEALTHY`, `UNHEALTHY`, etc.) for each active gateway.
    3. It periodically checks the `vnpy` connection status and the "canary" contract heartbeat.
    4. Any status change is logged and published to an internal event bus.

* **Story 3.2: Automated Failover Logic**
  * **As a** the system, **I want** the Quote Aggregation Engine to listen for health status changes and automatically switch to a backup data source when a primary source fails, **so that** downstream clients experience zero data interruption.
  * **Acceptance Criteria**:
    1. The aggregation engine subscribes to gateway status events.
    2. When a primary source is marked `UNHEALTHY`, the engine finds the next-highest priority healthy backup.
    3. Contract subscriptions are seamlessly switched to the new backup source.
    4. The failover event is logged in detail.

* **Story 3.3: "Hard Restart" Recovery Mechanism**
  * **As a** the system, **I want** to automatically attempt to recover a failed gateway by performing a full process restart, **so that** the system's redundancy can be restored without manual intervention.
  * **Acceptance Criteria**:
    1. After a gateway is marked `UNHEALTHY`, a configurable cool-down period is triggered.
    2. After the cool-down, the `GatewayManager` is instructed to terminate the failed gateway's process.
    3. The `GatewayManager` then relaunches a new, clean process for that gateway.
    4. The `HealthMonitor` tracks the recovery of the restarting gateway.

***

#### **Epic 4: Full-Featured Monitoring Dashboard**

**Goal**: To build the complete user-facing web interface, making the system's internal state transparent and providing full manual control to the user.

* **Story 4.1: Backend WebSocket Integration**
  * **As a** a frontend developer, **I want** a WebSocket endpoint on the FastAPI backend that continuously broadcasts system status events, **so that** the web dashboard can receive real-time data without polling.
  * **Acceptance Criteria**:
    1. A `/ws` WebSocket endpoint is created in FastAPI.
    2. Gateway status updates and system logs are pushed to all connected clients.
    3. The Next.js frontend can successfully connect and receive messages.

* **Story 4.2: Main Status Dashboard UI**
  * **As a** a system administrator, **I want** to see a main dashboard page that visualizes the real-time status of all active gateways at a glance, **so that** I can quickly assess the overall health of the system.
  * **Acceptance Criteria**:
    1. The main dashboard page is created in Next.js.
    2. It displays each active gateway's ID, type, priority, and real-time health status received via WebSocket.
    3. The "canary" contract monitor UI is implemented.
    4. All UI components are built using `Shadcn/ui`.

* **Story 4.3: Interactive Gateway Controls**
  * **As a** a system administrator, **I want** to have "Start," "Stop," and "Hard Restart" buttons for each gateway on the dashboard, **so that** I can perform direct manual intervention.
  * **Acceptance Criteria**:
    1. Control buttons are added to each gateway's display on the dashboard.
    2. Clicking a button sends a REST API request to the backend (e.g., `POST /api/accounts/{id}/restart`).
    3. The backend executes the requested action via the `GatewayManager`.
    4. The dashboard UI is updated in real-time to reflect the new state.

* **Story 4.4: Real-time Log Viewer**
  * **As a** a system administrator, **I want** a dedicated log viewer page that displays a live stream of system logs with filtering capabilities, **so that** I can perform real-time monitoring and troubleshooting.
  * **Acceptance Criteria**:
    1. A "Logs" page is created in Next.js.
    2. It displays a real-time feed of log messages received via WebSocket.
    3. UI controls are provided to filter logs by level (INFO, WARN, ERROR).
    4. `ERROR` level logs are visually highlighted.
