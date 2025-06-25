"use client";

import React, { useCallback } from 'react';
import { LogFilter as LogFilterType, LogLevel } from '@xiaoy-mdhub/shared-types';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X, Search, Filter } from 'lucide-react';

interface LogFilterProps {
  filter: LogFilterType;
  onFilterChange: (filter: LogFilterType) => void;
  availableModules: string[];
  availableGateways: string[];
  className?: string;
}

const LOG_LEVELS: LogLevel[] = ['DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL'];

export function LogFilterComponent({ 
  filter, 
  onFilterChange, 
  availableModules, 
  availableGateways, 
  className 
}: LogFilterProps) {
  const handleLevelChange = useCallback((value: string) => {
    onFilterChange({
      ...filter,
      level: value === 'ALL' ? undefined : value as LogLevel,
    });
  }, [filter, onFilterChange]);

  const handleModuleChange = useCallback((value: string) => {
    onFilterChange({
      ...filter,
      module: value === 'ALL' ? undefined : value,
    });
  }, [filter, onFilterChange]);

  const handleGatewayChange = useCallback((value: string) => {
    onFilterChange({
      ...filter,
      gatewayId: value === 'ALL' ? undefined : value,
    });
  }, [filter, onFilterChange]);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filter,
      search: e.target.value || undefined,
    });
  }, [filter, onFilterChange]);

  const handleStartDateChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filter,
      startDate: e.target.value ? new Date(e.target.value) : undefined,
    });
  }, [filter, onFilterChange]);

  const handleEndDateChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    onFilterChange({
      ...filter,
      endDate: e.target.value ? new Date(e.target.value) : undefined,
    });
  }, [filter, onFilterChange]);

  const clearFilters = useCallback(() => {
    onFilterChange({});
  }, [onFilterChange]);

  const hasActiveFilters = !!(
    filter.level || 
    filter.module || 
    filter.gatewayId || 
    filter.search || 
    filter.startDate || 
    filter.endDate
  );

  const getLogLevelBadgeVariant = (level: LogLevel | "ALL") => {
    switch (level) {
      case 'DEBUG':
        return 'outline';
      case 'INFO':
        return 'secondary';
      case 'WARN':
        return 'outline';
      case 'ERROR':
        return 'destructive';
      case 'CRITICAL':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Filter className="h-5 w-5" />
            Log Filters
          </CardTitle>
          {hasActiveFilters && (
            <Button
              variant="outline"
              size="sm"
              onClick={clearFilters}
              className="h-8"
            >
              <X className="h-4 w-4 mr-1" />
              Clear All
            </Button>
          )}
        </div>
        {hasActiveFilters && (
          <div className="flex flex-wrap gap-2 mt-2">
            {filter.level && (
              <Badge variant={getLogLevelBadgeVariant(filter.level)} className="text-xs">
                Level: {filter.level}
              </Badge>
            )}
            {filter.module && (
              <Badge variant="outline" className="text-xs">
                Module: {filter.module}
              </Badge>
            )}
            {filter.gatewayId && (
              <Badge variant="outline" className="text-xs">
                Gateway: {filter.gatewayId}
              </Badge>
            )}
            {filter.search && (
              <Badge variant="outline" className="text-xs">
                Search: {filter.search}
              </Badge>
            )}
            {(filter.startDate || filter.endDate) && (
              <Badge variant="outline" className="text-xs">
                Date Range
              </Badge>
            )}
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Log Level Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Log Level</label>
          <Select
            value={filter.level || 'ALL'}
            onValueChange={handleLevelChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select log level" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Levels</SelectItem>
              {LOG_LEVELS.map((level) => (
                <SelectItem key={level} value={level}>
                  <div className="flex items-center gap-2">
                    <Badge 
                      variant={getLogLevelBadgeVariant(level)} 
                      className="text-xs px-2 py-0"
                    >
                      {level}
                    </Badge>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Module Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Module</label>
          <Select
            value={filter.module || 'ALL'}
            onValueChange={handleModuleChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select module" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Modules</SelectItem>
              {availableModules.map((module) => (
                <SelectItem key={module} value={module}>
                  {module}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Gateway Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Gateway</label>
          <Select
            value={filter.gatewayId || 'ALL'}
            onValueChange={handleGatewayChange}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select gateway" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ALL">All Gateways</SelectItem>
              {availableGateways.map((gateway) => (
                <SelectItem key={gateway} value={gateway}>
                  {gateway}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Text Search */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Search Text</label>
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              type="text"
              placeholder="Search log messages..."
              value={filter.search || ''}
              onChange={handleSearchChange}
              className="pl-10"
            />
          </div>
        </div>

        {/* Date Range Filter */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Date Range</label>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <Input
                type="datetime-local"
                value={filter.startDate ? filter.startDate.toISOString().slice(0, 16) : ''}
                onChange={handleStartDateChange}
                placeholder="Start date"
                className="text-xs"
              />
            </div>
            <div>
              <Input
                type="datetime-local"
                value={filter.endDate ? filter.endDate.toISOString().slice(0, 16) : ''}
                onChange={handleEndDateChange}
                placeholder="End date"
                className="text-xs"
              />
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}