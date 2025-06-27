# Account Management CRUD Implementation Plan

## Current System Analysis
The system already has:
- ✅ Database schema for `market_data_accounts` with SQLite
- ✅ Backend API endpoints for basic CRUD operations (create, read, update, delete)
- ✅ Frontend accounts page with account listing and toggle functionality
- ✅ Trading time management and gateway validation systems

## Required Changes to Support New Account Format

### 1. Update Data Models & Types
- **Backend**: Update `AccountSettings` model in `accounts.py` to support the new account format with Chinese field names
- **Frontend**: Update `AccountSettings` interface in `shared-types/accounts.ts` to match the new format
- Add support for storing the complete account dictionary structure

### 2. Backend API Enhancements
- **Update `/api/accounts` POST endpoint** to handle the new account format
- **Add account validation service** that attempts login during trading hours
- **Update account mapping logic** to transform between old and new formats
- **Add trading time validation** before attempting login verification

### 3. Frontend UI Complete Overhaul
- **Replace existing account list** with full CRUD interface
- **Add account creation form** with fields for the new format
- **Add account editing modal/form** 
- **Add account deletion confirmation**
- **Separate CTP and SOPT account displays** in different sections/tabs
- **Add account priority management UI** with explanation tooltip

### 4. Account Validation System
- **Create validation service** that attempts gateway login during trading hours
- **Add progress indicators** for validation process
- **Handle validation errors** gracefully with user feedback
- **Implement graceful shutdown** of validation connections

### 5. Priority System Enhancement
- **Add priority explanation** in UI (lower number = higher priority for failover)
- **Visual indicators** for primary/backup accounts
- **Drag-and-drop priority management** (optional enhancement)

## Implementation Steps
1. Update backend models and API endpoints ✅
2. Create account validation service ✅
3. Update frontend types and services ✅
4. Build comprehensive CRUD interface ✅
5. Add CTP/SOPT separation ✅
6. Implement account validation flow ✅
7. Add priority management UI ✅
8. **[NEW] Convert form to JSON text input** - Replace individual connection setting fields with JSON textarea
9. Test with existing accounts

## Key Features
- ✅ Full CRUD operations (Create, Read, Update, Delete)
- ✅ Account login validation during trading hours
- ✅ Separate CTP/SOPT displays
- ✅ Priority management with explanations
- ✅ Graceful validation process with progress indicators
- ✅ Support for the new Chinese field account format
- ✅ Maintains backward compatibility with existing accounts
- 🔄 **JSON Text Input Interface** - Users can paste complete account dictionary format directly

## Target Account Format
```json
{
    "broker": "五矿期货",
    "connect_setting": {
        "交易服务器": "101.230.84.252:42205",
        "产品信息": "client_vntech_2.0",
        "产品名称": "client_vntech_2.0",
        "密码": "xxxx",
        "授权编码": "xxxx",
        "用户名": "566606626",
        "经纪商代码": "8888",
        "行情服务器": "101.230.84.252:42213"
    },
    "gateway": {
        "gateway_class": "SoptGateway",
        "gateway_name": "SOPT"
    },
    "market": "个股期权",
    "name": "兴鑫1号"
}
```
```json
{
	"broker": "光大期货",
	"connect_setting": {
		"交易服务器": "180.166.132.67:41205",
		"产品信息": "client_vntech_2.0",
		"产品名称": "client_vntech_2.0",
		"密码": "xxx",
		"授权编码": "xxx",
		"用户名": "30591100",
		"经纪商代码": "6000",
		"行情服务器": "180.166.132.67:41213"
	},
	"gateway": {
		"gateway_class": "CtpGateway",
		"gateway_name": "CTP"
	},
	"market": "期货期权",
	"name": "恒鑫1号"
}
```

## JSON Text Input Implementation Details

### User Experience Flow
1. **账户创建界面改造**:
   - 用户在创建账户时看到一个大型文本区域
   - 可以直接粘贴完整的账户字典JSON格式
   - 系统自动解析JSON并提取基本信息填充其他字段

2. **JSON格式解析**:
   - 自动从JSON中提取`name`、`broker`、`market`信息
   - 根据`gateway.gateway_name`确定gateway_type (CTP/SOPT)
   - 保持`connect_setting`的完整结构

3. **数据库兼容性**:
   - 生成的记录直接兼容现有`mdhub.db`的`market_data_accounts`表
   - `settings`字段存储完整的JSON结构
   - 自动生成合适的账户ID格式

### 技术实现要点
- **JSON验证**: 确保粘贴的内容是有效的JSON格式
- **字段映射**: 自动将JSON字段映射到数据库结构
- **错误处理**: 提供友好的错误提示和格式指导
- **向后兼容**: 保持对现有账户记录的完全兼容
```