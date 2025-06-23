### **Project Brief: Local High-Availability Market Data Hub**

**Version**: 1.0
**Date**: June 23, 2025
**Author**: John, Product Manager

#### **1. Executive Summary**
This project aims to build a high-availability market data hub running on a local area network (LAN). It will aggregate multiple data sources (initially CTP and SOPT) to provide a unified, stable, and cleansed data interface for quantitative trading strategies focused on options and futures. The core objective is to solve the unreliability of single data sources and simplify the complexity of integrating multiple APIs for trading strategies. Through multi-account automatic failover, intelligent data cleansing, and an alert system, this hub will provide a trusted data service for internal quantitative strategies that is far more reliable than any single source.

#### **2. Problem Statement**
Directly relying on a single API for quantitative trading presents significant pain points, including single points of failure, inconsistent data quality, unpredictable latency, high complexity in managing multiple accounts, and a lack of centralized monitoring. These issues pose a direct threat to the stable operation of strategies and the accuracy of trading decisions.

#### **3. Proposed Solution**
The solution is composed of five core modules:
* **Module 1: Data Access & Management**: Centrally controlled via a web interface, this module dynamically loads and manages enabled CTP, SOPT, and other market data gateway instances from a database (supporting both MySQL and MongoDB).
* **Module 2: Quote Aggregation & Arbitration Engine**: Selects the fastest-arriving `TickData` on a first-arrival basis ("racing" mode). It automatically fails over to backup sources based on priority and performs data deduplication and cleansing (e.g., discarding ticks with anomalous price or volume).
* **Module 3: Health Monitoring & Failover System**: Monitors the health of data feeds by checking the gateway connection status and a data heartbeat from high-liquidity "canary" contracts. Upon detecting an anomaly, it will execute a "Hard Restart" (kill and restart the process) of the faulty gateway and instruct the aggregation engine to failover.
* **Module 4: Data Distribution Hub**: Utilizes ZeroMQ (ZMQ) with a Publish/Subscribe (PUB/SUB) pattern to efficiently broadcast the cleansed `TickData` and system status logs, serialized with `msgpack`, across the LAN.
* **Module 5: Web Monitoring Dashboard**: Built with FastAPI and Next.js, it provides features for managing the account pool, monitoring gateway status with manual controls, viewing "canary" contract health, and a real-time, level-filterable log viewer.

#### **4. Target Users**
The primary user is the company's internal **Quantitative Strategy Developer/Researcher**. This user has a strong technical background, is proficient in Python and the `vn.py` ecosystem, and has a core need for a stable, reliable, plug-and-play source of high-quality market data, allowing them to focus on strategy development.

#### **5. Goals & Success Metrics**
* **Core Objectives**: Increase strategy development efficiency, ensure the continuous operation of trading strategies, and establish an extensible foundation for data services.
* **User Experience**: Easy integration, trusted data quality, and seamless failover.
* **Key Performance Indicators (KPIs)**: Service Availability > 99.9%; median End-to-End Tick Latency < 5ms; Abnormal Tick Interception Rate > 99%; Failover Success Rate = 100%.

#### **6. MVP Scope**
* **In Scope**: Database-driven account management, multi-source `TickData` aggregation, high-availability failover, abnormal tick data cleansing, web monitoring dashboard, and ZMQ data distribution.
* **Out of Scope**: Any trading-related functionality, `Bar` (candlestick) data synthesis, and calculation of option `Greeks` or other indicators.

#### **7. Post-MVP Vision**
* **Bar Generation Service**: An independent extension pack that subscribes to the MVP's `TickData` stream to generate `Bar` data for various intervals and publishes it on new topics.
* **Greeks Calculation Service**: Another extension pack to subscribe to the `TickData` stream, calculate option Greeks, and publish the results.

#### **8. Technical Considerations**
* **Platform Requirements**:
    * **Target Platform**: Ubuntu 24.04
    * **Deployment Method**: Docker containerization
* **Technology Preferences**:
    * **Backend**: Python 3.12, FastAPI
    * **Frontend**: TypeScript, Next.js, Shadcn/ui, Zustand (for state management)
    * **Communication Architecture**: REST API (for control commands) + WebSockets (for real-time status updates)
    * **Database**: Support for both MySQL and MongoDB
    * **Core Dependency Versions**: `vnpy` (v4.1.0), `vnpy_ctp` (v6.7.7.2), `vnpy_sopt` (v3.7.1.0)
* **Operational Requirements**:
    * **Scheduled Start/Stop**: The system must be managed by a host-level `cron` job to automatically start before market open and shut down after market close on trading days.

#### **9. Constraints & Assumptions**
* **Assumptions**: The LAN environment is stable and has low latency; the user is responsible for providing valid API credentials; exchange APIs are relatively stable.
* **Constraints**: Initial deployment will be on a server with a 16-core/32-thread CPU and 96GB of RAM, subject to adjustment based on observed resource consumption.

#### **10. Risks & Open Questions**
* **Primary Risks**: Upstream API changes, performance bottlenecks during extreme market volatility, the data hub service itself being a single point of failure, and database credential security.
* **Decided Questions**: Hardware specifications, alert recipient (`ryanflavor@163.com`), simple dashboard authentication (`admin`/`123456`), and deferral of historical data features have been confirmed.

---
#### **11. Next Steps**

**Handoff Prompt for Product Manager (PM)**:
This Project Brief provides the complete context for defining the product requirements. The Product Manager (John) should now begin the creation of the **Product Requirements Document (PRD)** based on this brief. Please systematically decompose the solution into specific Epics, User Stories, and Acceptance Criteria, paying special attention to incorporating the operational automation (scheduled start/stop) and web-based management features as non-functional requirements.