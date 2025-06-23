### **4. Technical Assumptions**

#### **Repository Structure**

The project will use a **Monorepo** structure to manage the backend, frontend, and shared packages in a single repository, simplifying dependency management and code sharing.

#### **Service Architecture**

The MVP will be built as a **Modular Monolith**. The core service will run as a single, deployable Python application, but its internal logic will be separated into the distinct, loosely-coupled modules defined in the Project Brief.

#### **Testing requirements**

A layered testing strategy is required:

1. **Unit Tests**: For core algorithms and utility functions.
2. **Integration Tests**: For interactions between internal modules.
3. **End-to-End (E2E) Tests**: For critical user workflows.

#### **Additional Technical Assumptions and Requests**

* **Backend**: Python 3.12, FastAPI.
* **Frontend**: TypeScript, Next.js, Shadcn/ui, Zustand.
* **Communication**: A hybrid model of REST API (for control) and WebSockets (for real-time data push).
* **Data Distribution**: ZeroMQ (pyzmq) for internal tick data distribution.
* **Database**: Support for both MySQL and MongoDB for account management.
* **Dependencies**: Pinned versions for `vnpy`, `vnpy_ctp`, `vnpy_sopt` are mandatory.
* **Deployment**: Must be deployed as a Docker container.
* **Scheduling**: System start/stop will be managed by a host-level `cron` job.
