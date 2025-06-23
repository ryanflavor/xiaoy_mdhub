# Local High-Availability Market Data Hub

A robust, high-availability market data aggregation system designed for quantitative trading strategies. This system provides reliable, cleansed market data through intelligent failover mechanisms and centralized monitoring.

## 🎯 Project Overview

The Market Data Hub solves the critical problem of single points of failure in trading data infrastructure by:

- **Aggregating** multiple data sources (CTP and SOPT) with automatic failover
- **Distributing** cleansed tick data via ZeroMQ with <5ms latency
- **Monitoring** gateway health with real-time alerting
- **Managing** account configurations through a web dashboard

### Key Features

- ✅ **99.9% Availability** with automated failover
- ✅ **<5ms Latency** end-to-end tick distribution
- ✅ **Real-time Monitoring** with health checks and canary contracts
- ✅ **Web Dashboard** for account management and system monitoring
- ✅ **Docker Deployment** with complete containerization

## 🏗️ Architecture

This project follows a **Modular Monolith** architecture with:

- **Backend**: Python 3.12 + FastAPI + vnpy ecosystem
- **Frontend**: Next.js 14 + TypeScript + Shadcn/ui + Zustand
- **Data Distribution**: ZeroMQ with msgpack serialization
- **Databases**: MySQL/MongoDB for account management
- **Deployment**: Docker containers with compose orchestration

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web Dashboard │    │   API Backend    │    │ Market Gateways │
│   (Next.js)     │◄───┤   (FastAPI)      │◄───┤ CTP/SOPT APIs   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │ ZeroMQ Publisher │
                       │ (Tick Data)      │
                       └──────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Ubuntu 24.04** (目标操作系统)
- **Node.js** 18+ and npm 8+
- **Python** 3.12+
- **Docker** and Docker Compose
- **Git**

### Installation

1. **Clone the repository**

   ```bash
   git clone https://github.com/xiaoy/xiaoy_mdhub.git
   cd xiaoy_mdhub
   ```

2. **Install vnpy system dependencies (Ubuntu 24.04)**

   ```bash
   ./scripts/install-vnpy-deps.sh
   ```

3. **Install vnpy required components**

   vnpy_ctp 和 vnpy_sopt 是项目行情源的必需组件：

   ```bash
   npm run setup:vnpy
   ```

4. **Install all dependencies**

   ```bash
   npm run install:all
   ```

5. **Set up environment**

   ```bash
   cp apps/api/.env.example apps/api/.env
   cp apps/web/.env.example apps/web/.env
   # Edit .env files with your configuration
   ```

6. **Start development services**

   ```bash
   # Start databases and backend
   docker-compose up -d mysql mongodb redis

   # Start backend API
   npm run api:dev

   # Start frontend (in another terminal)
   npm run web:dev
   ```

5. **Access the application**
   - **Web Dashboard**: http://localhost:3000
   - **API Documentation**: http://localhost:8000/docs
   - **API Health**: http://localhost:8000/health

## 📁 Project Structure

```
xiaoy_mdhub/
├── apps/
│   ├── api/          # FastAPI backend service
│   │   ├── app/      # Application modules
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   └── web/          # Next.js frontend dashboard
│       ├── src/
│       │   ├── app/      # App router pages
│       │   ├── components/
│       │   ├── store/    # Zustand stores
│       │   └── types/
│       ├── package.json
│       └── next.config.js
├── packages/
│   ├── shared-types/ # TypeScript interfaces
│   └── ui/           # Shared React components
├── docs/             # Project documentation
│   ├── architecture/
│   ├── prd/
│   └── stories/
├── docker-compose.yml
├── package.json      # Root workspace config
└── turbo.json       # Monorepo build config
```

## 🛠️ Development

### Available Scripts

```bash
# Monorepo commands
npm run build         # Build all packages
npm run dev           # Start all services in dev mode
npm run lint          # Lint all packages
npm run test          # Run all tests
npm run clean         # Clean all build artifacts

# Backend commands
npm run api:dev       # Start API in development mode

# Frontend commands
npm run web:dev       # Start web app in development mode

# Package management
npm run install:all   # Install all dependencies
```

### Development Workflow

1. **Story-driven development** - All work starts with user stories in `docs/stories/`
2. **Type-first approach** - Shared types in `packages/shared-types/`
3. **Component-driven UI** - Reusable components in `packages/ui/`
4. **API-first backend** - OpenAPI documentation at `/docs`

### Code Quality

- **TypeScript** strict mode enabled
- **ESLint** and **Prettier** for code formatting
- **Jest** for unit testing
- **Black** and **isort** for Python formatting

## 📊 Monitoring & Operations

### Health Checks

- **Gateway Status**: Real-time connection monitoring
- **Canary Contracts**: High-liquidity contract heartbeats
- **System Metrics**: Performance and availability tracking

### Logging

- **Structured Logging**: JSON format with correlation IDs
- **Log Levels**: DEBUG, INFO, WARN, ERROR
- **Real-time Streaming**: Live log viewer in dashboard
- **Email Alerts**: ERROR level notifications

### Database Management

- **Account Configuration**: Stored in MySQL/MongoDB
- **Dynamic Loading**: Hot-reload account changes
- **Backup Strategy**: Automated daily backups

## 🔧 Configuration

### Environment Variables

**Backend (`apps/api/.env`)**:

```env
DATABASE_URL=mysql://user:pass@localhost:3306/mdhub
MONGODB_URL=mongodb://localhost:27017/mdhub
ZMQ_PUBLISHER_PORT=5555
LOG_LEVEL=INFO
EMAIL_SMTP_HOST=smtp.gmail.com
EMAIL_RECIPIENTS=admin@company.com
```

**Frontend (`apps/web/.env`)**:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

### Trading Accounts

Configure CTP/SOPT accounts via the web dashboard or API:

- Account credentials (encrypted storage)
- Priority levels for failover
- Enable/disable status
- Health check parameters

## 🚢 Deployment

### Production Deployment

1. **Build for production**

   ```bash
   npm run build
   ```

2. **Deploy with Docker**

   ```bash
   docker-compose -f docker-compose.prod.yml up -d
   ```

3. **Set up monitoring**
   - Configure email notifications
   - Set up log aggregation
   - Monitor system metrics

### Scaling Considerations

- **Horizontal scaling**: Multiple hub instances with load balancing
- **Database optimization**: Read replicas and connection pooling
- **Caching**: Redis for session management and frequently accessed data

## 📚 Documentation

- **[Project Brief](docs/project_brief.md)** - High-level project overview
- **[PRD](docs/prd/)** - Detailed product requirements
- **[Architecture](docs/architecture/)** - Technical architecture details
- **[Stories](docs/stories/)** - Development user stories
- **[API Docs](http://localhost:8000/docs)** - Interactive API documentation

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines and coding standards.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/xiaoy/xiaoy_mdhub/issues)
- **Documentation**: [Project Wiki](https://github.com/xiaoy/xiaoy_mdhub/wiki)
- **Email**: ryanflavor@163.com

---

**Built with ❤️ for reliable quantitative trading infrastructure**
