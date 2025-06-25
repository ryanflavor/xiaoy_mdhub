/**
 * Gateway Service Tests
 */

import { GatewayService } from '@/services/gateway-service';
import { GatewayControlResponse } from '@xiaoy-mdhub/shared-types';

// Mock the ApiClient
jest.mock('@/services/api-client', () => ({
  ApiClient: jest.fn().mockImplementation(() => ({
    post: jest.fn(),
  })),
}));

describe('GatewayService', () => {
  let gatewayService: GatewayService;
  let mockApiClient: any;

  beforeEach(() => {
    gatewayService = new GatewayService();
    mockApiClient = (gatewayService as any).apiClient;
    jest.clearAllMocks();
  });

  const mockSuccessResponse = {
    data: {
      success: true,
      message: 'Gateway action completed successfully',
      gateway_id: 'test_gateway',
      action: 'start',
      timestamp: '2025-06-25T10:30:45.123Z',
    } as GatewayControlResponse,
    status: 200,
    statusText: 'OK',
  };

  describe('startGateway', () => {
    it('calls the correct API endpoint with proper data', async () => {
      mockApiClient.post.mockResolvedValue(mockSuccessResponse);

      const result = await gatewayService.startGateway('test_gateway');

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/accounts/test_gateway/start',
        {
          gateway_id: 'test_gateway',
          action: 'start',
        }
      );
      expect(result).toEqual(mockSuccessResponse);
    });

    it('handles API errors', async () => {
      const errorResponse = new Error('Network error');
      mockApiClient.post.mockRejectedValue(errorResponse);

      await expect(gatewayService.startGateway('test_gateway')).rejects.toThrow('Network error');
    });
  });

  describe('stopGateway', () => {
    it('calls the correct API endpoint with proper data', async () => {
      const stopResponse = {
        ...mockSuccessResponse,
        data: { ...mockSuccessResponse.data, action: 'stop' as const },
      };
      mockApiClient.post.mockResolvedValue(stopResponse);

      const result = await gatewayService.stopGateway('test_gateway');

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/accounts/test_gateway/stop',
        {
          gateway_id: 'test_gateway',
          action: 'stop',
        }
      );
      expect(result.data.action).toBe('stop');
    });
  });

  describe('restartGateway', () => {
    it('calls the correct API endpoint with proper data', async () => {
      const restartResponse = {
        ...mockSuccessResponse,
        data: { ...mockSuccessResponse.data, action: 'restart' as const },
      };
      mockApiClient.post.mockResolvedValue(restartResponse);

      const result = await gatewayService.restartGateway('test_gateway');

      expect(mockApiClient.post).toHaveBeenCalledWith(
        '/api/accounts/test_gateway/restart',
        {
          gateway_id: 'test_gateway',
          action: 'restart',
        }
      );
      expect(result.data.action).toBe('restart');
    });
  });

  describe('controlGateway', () => {
    it('delegates to correct method based on action', async () => {
      const startSpy = jest.spyOn(gatewayService, 'startGateway').mockResolvedValue(mockSuccessResponse);
      const stopSpy = jest.spyOn(gatewayService, 'stopGateway').mockResolvedValue(mockSuccessResponse);
      const restartSpy = jest.spyOn(gatewayService, 'restartGateway').mockResolvedValue(mockSuccessResponse);

      await gatewayService.controlGateway('start', 'test_gateway');
      expect(startSpy).toHaveBeenCalledWith('test_gateway');

      await gatewayService.controlGateway('stop', 'test_gateway');
      expect(stopSpy).toHaveBeenCalledWith('test_gateway');

      await gatewayService.controlGateway('restart', 'test_gateway');
      expect(restartSpy).toHaveBeenCalledWith('test_gateway');

      startSpy.mockRestore();
      stopSpy.mockRestore();
      restartSpy.mockRestore();
    });

    it('throws error for unsupported action', async () => {
      await expect(
        gatewayService.controlGateway('invalid' as any, 'test_gateway')
      ).rejects.toThrow('Unsupported gateway action: invalid');
    });
  });
});