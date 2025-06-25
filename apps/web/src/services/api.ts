/**
 * Main API service aggregator
 * Provides centralized access to all API services
 */

export { ApiClient, type ApiResponse, type ApiError } from './api-client';
export { gatewayService, GatewayService } from './gateway-service';

// Re-export existing services
export * from './account-service';