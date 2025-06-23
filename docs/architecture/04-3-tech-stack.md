### **3. Tech Stack**

This table represents the single source of truth for technologies and versions to be used in the project.

| Category               | Technology            | Version | Rationale                                         |
| :--------------------- | :-------------------- | :------ | :------------------------------------------------ |
| **Backend Language**   | Python                | 3.12    | Performance improvements and stability.           |
| **Backend Framework**  | FastAPI               | Latest  | High-performance, async support, auto-docs.       |
| **Frontend Framework** | Next.js               | Latest  | First-class React framework with SSG/SSR.         |
| **Frontend Language**  | TypeScript            | Latest  | Type safety for robust frontend code.             |
| **UI Component Lib**   | Shadcn/ui             | Latest  | Consistent, accessible, and modern UI components. |
| **Database**           | MySQL / MongoDB       | Latest  | Flexible support for relational and NoSQL stores. |
| **Core Trading Lib**   | vnpy                  | 4.1.0   | Pinned version for stability.                     |
| **CTP Adapter**        | vnpy_ctp              | 6.7.7.2 | Pinned version for stability.                     |
| **SOPT Adapter**       | vnpy_sopt             | 3.7.1.0 | Pinned version for stability.                     |
| **Deployment**         | Docker                | Latest  | Containerization for consistency and isolation.   |
| **Data Distribution**  | ZeroMQ (pyzmq)        | Latest  | High-speed, low-latency messaging.                |
| **Communication**      | REST API & WebSockets | N/A     | Hybrid model for control and real-time updates.   |
