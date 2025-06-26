# Market Data Hub - Fullstack Integration Architecture

## Executive Summary

This document outlines the complete web-API integration solution for the Market Data Hub, transforming the current functional backend (with 4 real CTP/SOPT accounts) into a fully operational MVP with live web dashboard capabilities.

**Current Status**: Backend operational ✅ | Frontend built ✅ | Integration gaps identified 🔧
**Target**: Fully functional MVP with real-time trading gateway monitoring

---

## 🎯 Integration Objectives

### Primary Goals
1. **Real-time Gateway Monitoring**: Display live CTP/SOPT connection status ("连接成功"/"连接断开")
2. **Interactive Controls**: Enable start/stop/restart gateway operations from web interface
3. **Live Logging**: Stream backend logs to web dashboard in real-time
4. **Contract Monitoring**: Display canary contract health and tick data
5. **System Health**: Comprehensive dashboard showing all 4 account statuses

### Success Criteria
- Web dashboard reflects actual gateway connection states within 2 seconds
- Gateway control actions (start/stop/restart) complete with visual feedback
- Real-time logs display with <1 second latency
- MVP demonstrates professional trading system UI/UX

---

## 🏗️ Current Architecture Analysis

### Backend Architecture (FastAPI) - ✅ FUNCTIONAL
```
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Application (Port 8000)                             │
├─────────────────────────────────────────────────────────────┤
│ • Gateway Manager: 4 real accounts configured               │
│   - 兴鑫1号-兴证期货-SOPT (Priority 1)                      │
│   - 兴鑫1号-兴证期货-CTP (Priority 2)                       │
│   - 佳成2号-国富期货-CTP (Priority 3)                       │
│   - 佳成2号-国富期货-SOPT (Priority 4)                      │
│                                                             │
│ • Real CTP Connections: Returns "连接成功"/"连接断开"        │
│ • WebSocket Server: /ws endpoint for real-time events       │
│ • Health Monitor: Canary contracts (rb2601, au2512)         │
│ • Database: SQLite with account configurations              │
│ • ZeroMQ Publisher: High-performance tick distribution      │
└─────────────────────────────────────────────────────────────┘
```

### Frontend Architecture (Next.js) - ✅ BUILT
```
┌─────────────────────────────────────────────────────────────┐
│ Next.js Dashboard (Port 3000)                              │
├─────────────────────────────────────────────────────────────┤
│ • Professional UI: Shadcn/ui + Tailwind CSS                │
│ • Type-Safe: Comprehensive TypeScript interfaces           │
│ • State Management: Zustand stores (app, gateway, logs)    │
│ • Real-time Client: WebSocket with auto-reconnection       │
│ • API Client: HTTP client with error handling              │
│ • Dashboard Components: Gateway cards, health summary      │
└─────────────────────────────────────────────────────────────┘
```

### Integration Gaps - 🔧 NEEDS FIXING
1. **Environment Configuration**: Missing `.env` files
2. **Data Transformation**: Dashboard data format mismatch
3. **WebSocket Verification**: Real-time connection needs testing
4. **Error Handling**: Offline/error state fallbacks

---

## 🚀 Integration Implementation Plan

### Phase 1: Environment Configuration (5 minutes)

**Frontend Environment** (`apps/web/.env.local`):
```bash
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws
NEXT_PUBLIC_ENVIRONMENT=development
```

**Backend Environment** (`apps/api/.env`):
```bash
DATABASE_URL=sqlite:///./mdhub.db
LOG_LEVEL=INFO
ENVIRONMENT=development
ENABLE_CTP_GATEWAY=true
ENABLE_CTP_MOCK=false
CORS_ORIGINS=["http://localhost:3000"]
```

### Phase 2: Data Transformation Fix (15 minutes)

**Current API Response** (`GET /health`):
```json
{
  "status": "ok",
  "gateway_manager": {
    "accounts": [
      {
        "gateway_id": "xinxin1_xingzheng_sopt",
        "gateway_type": "SOPT",
        "connection_status": "connected",
        "connection_duration": 1234.56,
        "last_tick_time": "2024-01-15T10:30:00Z"
      }
    ]
  },
  "health_monitor": {
    "canary_contracts": ["rb2601.SHFE", "au2512.SHFE"],
    "last_health_check": "2024-01-15T10:29:58Z"
  }
}
```

**Frontend Expected Format**:
```json
{
  "gateways": [
    {
      "gateway_id": "xinxin1_xingzheng_sopt",
      "current_status": "connected",
      "gateway_type": "SOPT",
      "connection_duration": 1234.56,
      "last_update": "2024-01-15T10:30:00Z"
    }
  ],
  "system_health": {
    "total_gateways": 4,
    "healthy_gateways": 2,
    "connecting_gateways": 1,
    "disconnected_gateways": 1
  },
  "canary_contracts": [
    {
      "symbol": "rb2601.SHFE",
      "status": "healthy",
      "last_tick": "2024-01-15T10:29:58Z"
    }
  ]
}
```

**Solution**: Update `apps/web/src/hooks/useDashboardData.ts`:
```typescript
const transformHealthResponse = (healthData: any): DashboardData => {
  const gateways = healthData.gateway_manager?.accounts || [];
  const healthy = gateways.filter(g => g.connection_status === 'connected').length;
  
  return {
    gateways: gateways.map(gateway => ({
      gateway_id: gateway.gateway_id,
      current_status: gateway.connection_status,
      gateway_type: gateway.gateway_type,
      connection_duration: gateway.connection_duration,
      last_update: gateway.last_tick_time
    })),
    system_health: {
      total_gateways: gateways.length,
      healthy_gateways: healthy,
      connecting_gateways: gateways.filter(g => g.connection_status === 'connecting').length,
      disconnected_gateways: gateways.filter(g => g.connection_status === 'disconnected').length
    },
    canary_contracts: healthData.health_monitor?.canary_contracts?.map(symbol => ({
      symbol,
      status: 'healthy', // Derive from health_monitor data
      last_tick: healthData.health_monitor.last_health_check
    })) || []
  };
};
```

### Phase 3: WebSocket Real-time Integration (10 minutes)

**Verify WebSocket Messages**:
```typescript
// Backend sends these message types:
interface WebSocketMessage {
  type: 'gateway_status' | 'gateway_control' | 'system_log' | 'health_update';
  data: any;
  timestamp: string;
}

// Example gateway status message:
{
  "type": "gateway_status",
  "data": {
    "gateway_id": "xinxin1_xingzheng_ctp",
    "status": "connected", // or "disconnected"
    "message": "连接成功" // or "连接断开"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Frontend WebSocket Handler** (`apps/web/src/services/websocket.ts`):
```typescript
const handleMessage = (message: WebSocketMessage) => {
  switch (message.type) {
    case 'gateway_status':
      // Update gateway store with new connection status
      updateGatewayStatus(message.data.gateway_id, message.data.status);
      // Show toast notification with Chinese message
      showToast(message.data.message);
      break;
    case 'system_log':
      // Add to log store for real-time log viewer
      addLogEntry(message.data);
      break;
  }
};
```

### Phase 4: Error Handling & Resilience (15 minutes)

**React Error Boundary** (`apps/web/src/components/ErrorBoundary.tsx`):
```typescript
const ErrorBoundary = ({ children }) => {
  // Handle API connection failures
  // Display fallback UI when backend unavailable
  // Provide retry mechanisms
};
```

**Offline State Management**:
```typescript
const useConnectionStatus = () => {
  // Monitor API connectivity
  // Display offline indicator
  // Queue actions for when connection restored
};
```

---

## 🔄 Real-time Data Flow Architecture

### Connection Establishment Flow
```
1. Frontend loads → Check API health endpoint
2. Establish WebSocket connection to /ws
3. Backend broadcasts gateway status changes
4. Frontend updates UI in real-time
5. User actions (start/stop) → API calls → WebSocket notifications
```

### Data Synchronization Pattern
```
┌─────────────┐    HTTP     ┌─────────────┐    vnpy     ┌─────────────┐
│   Web UI    │◄──────────►│   FastAPI   │◄──────────►│ CTP Gateway │
│             │   WebSocket │             │   Events    │             │
└─────────────┘◄───────────►└─────────────┘             └─────────────┘
       ▲                           │                            │
       │        Real-time          │                            │
       └───────  Updates ──────────┘               "连接成功"/"连接断开"
```

---

## 📊 MVP Feature Mapping

### Dashboard Components ↔ Backend Services

| Frontend Component | Backend Service | Data Source | Status |
|-------------------|----------------|-------------|---------|
| `GatewayStatusCard` | `GatewayManager.get_gateway_status()` | vnpy connection state | ✅ Ready |
| `SystemHealthSummary` | `HealthMonitor.get_system_health()` | Database + connections | ✅ Ready |
| `CanaryMonitor` | `HealthMonitor.check_canary_contracts()` | Tick data freshness | ✅ Ready |
| `GatewayControls` | `POST /api/accounts/{id}/start` | Gateway lifecycle | ✅ Ready |
| `LogViewer` | WebSocket log stream | `structlog` output | 🔧 Needs integration |

### Real-time Event Mapping

| User Action | API Endpoint | WebSocket Event | UI Update |
|-------------|--------------|-----------------|-----------|
| Start Gateway | `POST /api/accounts/{id}/start` | `gateway_control` → `gateway_status` | Status card + toast |
| Stop Gateway | `POST /api/accounts/{id}/stop` | `gateway_control` → `gateway_status` | Status card + toast |
| Gateway Connects | Automatic (vnpy) | `gateway_status` | Status change animation |
| Tick Data Received | Automatic (vnpy) | `health_update` | Canary monitor update |

---

## 🧪 Testing & Validation Strategy

### Integration Testing Checklist
- [ ] **Environment Setup**: Both `.env` files created and API connects
- [ ] **Dashboard Load**: Web dashboard displays 4 configured accounts
- [ ] **Real-time Status**: Gateway connection changes reflect immediately
- [ ] **Control Actions**: Start/stop buttons trigger actual gateway operations
- [ ] **Log Streaming**: Backend logs appear in web log viewer
- [ ] **Error Handling**: Graceful behavior when API unavailable
- [ ] **Chinese Messages**: "连接成功"/"连接断开" displayed correctly

### Performance Validation
- [ ] **Dashboard Load Time**: <2 seconds initial load
- [ ] **WebSocket Latency**: <1 second for status updates
- [ ] **Gateway Control Response**: <3 seconds for start/stop actions
- [ ] **Log Streaming Rate**: Handle >100 log entries/second
- [ ] **Memory Usage**: Frontend stable under continuous operation

### User Experience Validation
- [ ] **Visual Feedback**: Loading states, success/error indications
- [ ] **Responsive Design**: Works on desktop and tablet
- [ ] **Dark Theme**: Consistent styling across all components
- [ ] **Toast Notifications**: Non-intrusive status updates
- [ ] **Error Recovery**: Clear instructions when things go wrong

---

## 🚀 Deployment Readiness

### Development Environment
```bash
# Terminal 1: Start API
cd apps/api
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Start Web
cd apps/web
npm run dev

# Terminal 3: Monitor logs
cd apps/api
tail -f logs/mdhub.log
```

### Production Considerations
- **Security**: API authentication, CORS configuration
- **Performance**: Connection pooling, caching strategies
- **Monitoring**: Health checks, performance metrics
- **Scaling**: Load balancing, database optimization

---

## 📈 Success Metrics

### Technical Metrics
- **API Response Time**: <100ms for health endpoint
- **WebSocket Connection**: <2 seconds to establish
- **Gateway Status Accuracy**: 100% reflection of actual state
- **Error Rate**: <1% for critical operations

### Business Metrics
- **User Experience**: Seamless gateway monitoring and control
- **Operational Efficiency**: Reduced manual intervention needs
- **System Reliability**: 99.9% uptime for monitoring dashboard
- **Data Accuracy**: Real-time sync with actual market connections

---

## 🔧 Implementation Commands

### Quick Start (Execute in order):
```bash
# 1. Create environment files
echo "NEXT_PUBLIC_API_BASE_URL=http://localhost:8000" > apps/web/.env.local
echo "DATABASE_URL=sqlite:///./mdhub.db" > apps/api/.env

# 2. Start services
npm run api:dev &
npm run web:dev &

# 3. Test integration
curl http://localhost:8000/health
curl http://localhost:3000

# 4. Verify WebSocket
# Open browser developer tools → Network → WS tab
# Should see WebSocket connection to ws://localhost:8000/ws
```

---

## 📋 Next Steps Priority Order

1. **[HIGH] Environment Configuration** - 5 minutes setup
2. **[HIGH] Data Transformation Fix** - 15 minutes coding
3. **[MEDIUM] WebSocket Testing** - 10 minutes verification
4. **[MEDIUM] Error Handling** - 15 minutes robustness
5. **[LOW] UI Polish** - Optional enhancements

**Total Implementation Time**: 45 minutes to working MVP
**Expected Result**: Fully functional web dashboard with live CTP gateway monitoring

---

*Generated by Winston - Architect 🏗️*
*Document serves as complete implementation guide for Market Data Hub web-API integration*


# if encounter 
terminate called after throwing an instance of 'std::runtime_error'
what(): locale::facet::_S_create_c_locale name not valid

'''bash
sudo locale-gen zh_CN.GB18030
'''