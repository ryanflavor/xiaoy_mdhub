### **2. High-Level Architecture**

#### **2.1. Technical Summary**

The system is designed as a **Modular Monolith** backend service, containerized with Docker, responsible for data aggregation and distribution. It is paired with a modern **Next.js** frontend dashboard for management and monitoring. The backend, built with Python and FastAPI, will handle connections to multiple CTP and SOPT gateways, perform real-time health checks, and execute automated failovers. A hybrid **REST API and WebSocket** interface facilitates communication between the frontend and backend, while a **ZeroMQ** message bus handles the high-throughput distribution of cleansed `TickData` to internal strategy clients.

#### **2.2. Platform and Infrastructure**

* **Platform**: The entire system will be deployed on a dedicated **Ubuntu 24.04** server.
* **Deployment Model**:
  * **Backend & Databases**: Deployed as a set of coordinated **Docker containers** managed via `docker-compose`. This ensures environment consistency and simplifies dependency management.
  * **Frontend**: The Next.js web dashboard will be deployed to **Vercel**, which offers seamless CI/CD, global CDN, and first-class support for Next.js.
* **Repository Structure**: A **Monorepo** structure will be used to manage all code (backend, frontend, shared types) in a single Git repository.

#### **2.3. High-Level Architecture Diagram**

This C4-style container diagram illustrates the primary components and their interactions.

```mermaid
graph TD
    subgraph "User's Workstation"
        user[Quantitative Developer<br/>[Person]]
    end
    
    subgraph "Vercel Platform"
        dashboard[Web Dashboard<br/>[Container: Next.js]]
    end

    subgraph "Ubuntu 24.04 Server (Docker)"
        subgraph "Market Data Hub Service"
            api[API & WebSocket<br/>[Component: FastAPI]]
            aggregator[Aggregation & Failover Engine<br/>[Component: Python]]
            monitor[Health Monitor<br/>[Component: Python]]
            zmq[Data Distribution Hub<br/>[Component: ZeroMQ PUB]]
        end
        
        db[(Database<br/>[Container: MySQL/Mongo])]
    end
    
    subgraph "External Exchanges"
        ctp_gw[CTP Gateway API]
        sopt_gw[SOPT Gateway API]
    end

    user -- "Manages & Monitors via HTTPS" --> dashboard
    dashboard -- "REST API Calls / WebSocket<br/>[HTTPS]" --> api
    api -- "Controls & Reads from" --> aggregator
    api -- "Reads State from" --> monitor
    aggregator -- "Receives Data from" --> ctp_gw
    aggregator -- "Receives Data from" --> sopt_gw
    monitor -- "Monitors Gateways in" --> aggregator
    aggregator -- "Stores/Reads Config from" --> db
    aggregator -- "Publishes Ticks to" --> zmq
```

#### **2.4. Architectural Patterns**

* **Modular Monolith**: The backend service runs in a single process but is internally structured into loosely-coupled modules (data access, aggregation, monitoring) to facilitate maintenance and future scalability.
* **Repository Pattern**: The backend will use this pattern to abstract database interactions, allowing for flexible support of both MySQL and MongoDB.
* **Event-Driven**: The internal `vnpy` core operates on an event-driven model, which we will extend for inter-module communication within the backend.
* **Publish/Subscribe**: ZeroMQ will be used for a high-performance, one-to-many distribution of tick data to subscribing clients.
