### **2. Requirements**

#### **Functional Requirements (FR)**

* **FR1**: The system must load its active account configurations from a database (which supports both MySQL and MongoDB).
* **FR2**: A web dashboard must provide an interface for users to enable or disable accounts in the active data source pool.
* **FR3**: The system must aggregate `TickData` from all active sources in the pool.
* **FR4**: For any given contract, the system must select and forward only the first-arriving tick to ensure lowest latency.
* **FR5**: The system must cleanse incoming data, discarding anomalous ticks with invalid prices or volumes.
* **FR6**: The system must monitor the health of each gateway by checking its direct connection status and by monitoring a data heartbeat from high-liquidity "canary" contracts.
* **FR7**: Upon detecting a health anomaly in a primary source, the system must automatically trigger a failover to a healthy backup source.
* **FR8**: Following a failure, the system must perform a "hard restart" (terminate and relaunch the process) of the failed gateway to ensure a clean reconnection.
* **FR9**: The system must distribute the final, aggregated `TickData` stream to clients over the LAN via a ZeroMQ PUB/SUB mechanism.
* **FR10**: The web dashboard must display the real-time operational status of each gateway in the pool.
* **FR11**: The web dashboard must display a real-time stream of system logs, which can be filtered by severity level (e.g., INFO, WARN, ERROR).
* **FR12**: The web dashboard must provide manual controls to start, stop, and "hard restart" individual gateways.

#### **Non-Functional Requirements (NFR)**

* **NFR1**: The entire application must be containerized using Docker for deployment.
* **NFR2**: The system's scheduled start and stop must be managed by a host-level `cron` job that controls the Docker container.
* **NFR3**: The backend service must be developed in **Python 3.12**.
* **NFR4**: The web dashboard frontend must be developed using Next.js and TypeScript.
* **NFR5**: The project must use the following pinned dependency versions: `vnpy` (v4.1.0), `vnpy_ctp` (v6.7.7.2), and `vnpy_sopt` (v3.7.1.0).
* **NFR6**: The system must achieve greater than 99.9% service availability.
* **NFR7**: The median end-to-end tick latency (from gateway ingress to client egress) must be below 5 milliseconds.
* **NFR8**: The web dashboard must be protected by a simple username and password authentication mechanism.
* **NFR9**: System events logged at the `ERROR` level must trigger an email notification to `ryanflavor@163.com`.
