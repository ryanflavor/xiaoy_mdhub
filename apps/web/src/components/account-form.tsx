'use client';

import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { MarketDataAccount, AccountSettings, ConnectSetting, GatewayInfo } from '@xiaoy-mdhub/shared-types/accounts';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Form, FormControl, FormDescription, FormField, FormItem, FormLabel, FormMessage } from '@/components/ui/form';
import { Switch } from '@/components/ui/switch';
import { AlertCircle, Loader2, CheckCircle2 } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { accountService } from '@/services/account-service';
import { useToast } from '@/hooks/use-toast';

// Form schema for account creation/editing
const accountFormSchema = z.object({
  id: z.string().min(1, 'Account ID is required').max(100, 'Account ID too long'),
  gateway_type: z.enum(['ctp', 'sopt'], { required_error: 'Please select a gateway type' }),
  priority: z.number().min(1, 'Priority must be at least 1').max(100, 'Priority cannot exceed 100'),
  is_enabled: z.boolean(),
  description: z.string().optional(),
  
  // JSON text input for account settings
  json_settings: z.string().min(1, 'Account settings JSON is required'),
  
  // Auto-populated fields from JSON (for display/verification)
  broker: z.string().optional(),
  market: z.string().optional(),
  name: z.string().optional(),
  
  // Validation options
  validate_connection: z.boolean(),
  allow_non_trading_validation: z.boolean(),
  use_real_api_validation: z.boolean(),
});

type AccountFormData = z.infer<typeof accountFormSchema>;

interface AccountFormProps {
  account?: MarketDataAccount | null;
  mode: 'create' | 'edit';
  onSubmit: (account: MarketDataAccount) => void;
  onCancel: () => void;
  onValidate?: (accountId: string, gatewayType: string, settings: AccountSettings, validationOptions?: {
    allowNonTradingValidation?: boolean;
    useRealApiValidation?: boolean;
  }) => Promise<boolean>;
}

export function AccountForm({ account, mode, onSubmit, onCancel, onValidate }: AccountFormProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [validationResult, setValidationResult] = useState<{ success: boolean; message: string } | null>(null);
  const [jsonError, setJsonError] = useState<string | null>(null);
  const [parsedSettings, setParsedSettings] = useState<any>(null);
  const [duplicateIdError, setDuplicateIdError] = useState<string | null>(null);
  const { toast } = useToast();

  // Initialize form with default values or existing account data
  const form = useForm<AccountFormData>({
    resolver: zodResolver(accountFormSchema),
    defaultValues: {
      id: account?.id || '',
      gateway_type: account?.gateway_type || 'ctp',
      priority: account?.priority || 1,
      is_enabled: account?.is_enabled ?? true,
      description: account?.description || '',
      
      // JSON settings - convert existing account to JSON string
      json_settings: account?.settings ? JSON.stringify(account.settings, null, 2) : '',
      
      // Auto-populated fields from existing account
      broker: account?.settings?.broker || '',
      market: account?.settings?.market || '',
      name: account?.settings?.name || '',
      
      // Validation options
      validate_connection: true,
      allow_non_trading_validation: false,
      use_real_api_validation: false,
    },
  });

  const watchedGatewayType = form.watch('gateway_type');
  const watchedJsonSettings = form.watch('json_settings');
  const watchedAccountId = form.watch('id');

  // Check for duplicate Account ID
  const checkDuplicateId = React.useCallback(async (accountId: string) => {
    if (!accountId.trim() || mode === 'edit') {
      setDuplicateIdError(null);
      return;
    }

    try {
      const accounts = await accountService.getAllAccounts();
      const duplicateExists = accounts.some(acc => acc.id === accountId.trim());
      
      if (duplicateExists) {
        setDuplicateIdError(`账户ID "${accountId}" 已存在，请使用不同的ID`);
      } else {
        setDuplicateIdError(null);
      }
    } catch (error) {
      // If we can't check for duplicates, allow the form submission to handle it
      setDuplicateIdError(null);
    }
  }, [mode]);

  // Check for duplicates when Account ID changes
  React.useEffect(() => {
    const timeoutId = setTimeout(() => {
      checkDuplicateId(watchedAccountId);
    }, 500); // Debounce for 500ms

    return () => clearTimeout(timeoutId);
  }, [watchedAccountId, checkDuplicateId]);

  // Parse and validate JSON settings when they change
  React.useEffect(() => {
    if (!watchedJsonSettings.trim()) {
      setParsedSettings(null);
      setJsonError(null);
      form.setValue('broker', '');
      form.setValue('market', '');
      form.setValue('name', '');
      // Don't auto-clear Account ID when JSON is cleared
      return;
    }

    try {
      const parsed = JSON.parse(watchedJsonSettings);
      
      // Validate required structure
      if (!parsed.broker || !parsed.connect_setting || !parsed.gateway) {
        setJsonError('JSON must contain "broker", "connect_setting", and "gateway" fields');
        setParsedSettings(null);
        return;
      }

      // Auto-populate fields from parsed JSON
      form.setValue('broker', parsed.broker || '');
      form.setValue('market', parsed.market || '');
      form.setValue('name', parsed.name || '');
      
      // Auto-detect gateway type
      if (parsed.gateway?.gateway_name) {
        const gatewayType = parsed.gateway.gateway_name.toLowerCase();
        if (gatewayType === 'ctp' || gatewayType === 'sopt') {
          form.setValue('gateway_type', gatewayType);
        }
      }

      // Auto-generate Account ID if in create mode and ID is empty
      if (mode === 'create' && !form.getValues().id.trim()) {
        const accountName = parsed.name || '未命名账户';
        const broker = parsed.broker || '未知期货公司';
        const gatewayName = parsed.gateway?.gateway_name?.toUpperCase() || 'UNKNOWN';
        
        // Generate ID format: 账户名-期货公司-网关类型
        const generatedId = `${accountName}-${broker}-${gatewayName}`;
        form.setValue('id', generatedId);
      }

      setParsedSettings(parsed);
      setJsonError(null);
    } catch (error) {
      setJsonError('Invalid JSON format. Please check your JSON syntax.');
      setParsedSettings(null);
    }
  }, [watchedJsonSettings, form, mode]);

  const handleValidate = async () => {
    if (!onValidate || !parsedSettings) return;
    
    const formData = form.getValues();
    setIsValidating(true);
    setValidationResult(null);

    // Debug: Log validation options
    console.log('🔧 Validation Options Debug:', {
      validate_connection: formData.validate_connection,
      allow_non_trading_validation: formData.allow_non_trading_validation,
      use_real_api_validation: formData.use_real_api_validation
    });

    try {
      // Use parsed JSON settings directly with validation options
      const success = await onValidate(
        formData.id, 
        formData.gateway_type, 
        parsedSettings,
        {
          allowNonTradingValidation: formData.allow_non_trading_validation,
          useRealApiValidation: formData.use_real_api_validation
        }
      );
      setValidationResult({
        success,
        message: success ? 'Account validation successful' : 'Account validation failed'
      });
    } catch (error: any) {
      setValidationResult({
        success: false,
        message: error?.message || 'Validation failed'
      });
    } finally {
      setIsValidating(false);
    }
  };

  const handleSubmit = async (data: AccountFormData) => {
    if (!parsedSettings) {
      toast({
        title: "Invalid JSON",
        description: "Please provide valid account settings JSON",
        variant: "destructive",
      });
      return;
    }

    if (duplicateIdError) {
      toast({
        title: "Duplicate Account ID",
        description: duplicateIdError,
        variant: "destructive",
      });
      return;
    }

    setIsSubmitting(true);

    try {
      // Use parsed JSON settings directly
      const accountData = {
        id: data.id,
        gateway_type: data.gateway_type,
        priority: data.priority,
        is_enabled: data.is_enabled,
        description: data.description,
        settings: parsedSettings as AccountSettings,
        // Add validation options for create mode
        ...(mode === 'create' && {
          validate_connection: data.validate_connection,
          allow_non_trading_validation: data.allow_non_trading_validation,
          use_real_api_validation: data.use_real_api_validation,
        })
      };

      let result: MarketDataAccount;
      
      if (mode === 'create') {
        result = await accountService.createAccount(accountData);
        toast({
          title: "Account created",
          description: `Account ${data.id} has been created successfully`,
        });
      } else {
        result = await accountService.updateAccount(data.id, {
          gateway_type: data.gateway_type,
          settings: accountData.settings,
          priority: data.priority,
          is_enabled: data.is_enabled,
          description: data.description,
        });
        toast({
          title: "Account updated",
          description: `Account ${data.id} has been updated successfully`,
        });
      }

      onSubmit(result);
    } catch (error: any) {
      toast({
        title: mode === 'create' ? "Error creating account" : "Error updating account",
        description: error?.message || 'An unexpected error occurred',
        variant: "destructive",
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Card className="w-full max-w-4xl mx-auto">
      <CardHeader>
        <CardTitle>
          {mode === 'create' ? 'Create New Account' : 'Edit Account'}
        </CardTitle>
        <CardDescription>
          {mode === 'create' 
            ? 'Add a new trading account with gateway configuration'
            : 'Update trading account configuration'
          }
        </CardDescription>
      </CardHeader>
      <CardContent>
        <Form {...form}>
          <form onSubmit={form.handleSubmit(handleSubmit)} className="space-y-6">
            
            {/* Basic Information */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="id"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Account ID</FormLabel>
                    <FormControl>
                      <Input 
                        {...field} 
                        disabled={mode === 'edit'} 
                        placeholder="账户ID将根据JSON自动生成" 
                        className={duplicateIdError ? "border-red-500" : ""}
                      />
                    </FormControl>
                    <FormDescription>
                      {mode === 'create' ? '账户ID将根据JSON内容自动生成，或手动输入唯一标识符' : '账户ID不可修改'}
                    </FormDescription>
                    {duplicateIdError && (
                      <p className="text-sm text-red-600 mt-1">{duplicateIdError}</p>
                    )}
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="gateway_type"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Gateway Type</FormLabel>
                    <Select onValueChange={field.onChange} defaultValue={field.value}>
                      <FormControl>
                        <SelectTrigger>
                          <SelectValue placeholder="Select gateway type" />
                        </SelectTrigger>
                      </FormControl>
                      <SelectContent>
                        <SelectItem value="ctp">CTP (期货期权)</SelectItem>
                        <SelectItem value="sopt">SOPT (个股期权)</SelectItem>
                      </SelectContent>
                    </Select>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="priority"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Priority</FormLabel>
                    <FormControl>
                      <Input 
                        type="number" 
                        {...field} 
                        onChange={(e) => field.onChange(parseInt(e.target.value) || 1)}
                        min={1}
                        max={100}
                      />
                    </FormControl>
                    <FormDescription>
                      Lower number = higher priority (1 = primary account)
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="is_enabled"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                    <div className="space-y-0.5">
                      <FormLabel className="text-base">Enabled</FormLabel>
                      <FormDescription>
                        Enable this account for live trading
                      </FormDescription>
                    </div>
                    <FormControl>
                      <Switch
                        checked={field.value}
                        onCheckedChange={field.onChange}
                      />
                    </FormControl>
                  </FormItem>
                )}
              />
            </div>

            {/* JSON Settings Input */}
            <div className="space-y-4">
              <h3 className="text-lg font-medium">Account Settings JSON</h3>
              
              <FormField
                control={form.control}
                name="json_settings"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Account Configuration JSON</FormLabel>
                    <FormControl>
                      <Textarea 
                        {...field} 
                        className="font-mono text-sm min-h-[300px]"
                        placeholder={`Paste your account JSON configuration here, for example:
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
}`}
                      />
                    </FormControl>
                    <FormDescription>
                      Paste the complete account configuration JSON. The system will automatically extract broker, market, and name information.
                    </FormDescription>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {/* JSON Validation Error */}
              {jsonError && (
                <Alert className="border-red-200 bg-red-50">
                  <AlertCircle className="h-4 w-4 text-red-600" />
                  <AlertDescription className="text-red-800">
                    {jsonError}
                  </AlertDescription>
                </Alert>
              )}

              {/* Auto-populated Account Details */}
              {parsedSettings && (
                <div className="space-y-4">
                  <h4 className="text-md font-medium text-green-700">✓ Parsed Account Information</h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <FormField
                      control={form.control}
                      name="broker"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Broker (Auto-populated)</FormLabel>
                          <FormControl>
                            <Input {...field} readOnly className="bg-gray-50" />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="market"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Market (Auto-populated)</FormLabel>
                          <FormControl>
                            <Input {...field} readOnly className="bg-gray-50" />
                          </FormControl>
                        </FormItem>
                      )}
                    />

                    <FormField
                      control={form.control}
                      name="name"
                      render={({ field }) => (
                        <FormItem>
                          <FormLabel>Account Name (Auto-populated)</FormLabel>
                          <FormControl>
                            <Input {...field} readOnly className="bg-gray-50" />
                          </FormControl>
                        </FormItem>
                      )}
                    />
                  </div>
                </div>
              )}
            </div>

            {/* Description */}
            <FormField
              control={form.control}
              name="description"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Description</FormLabel>
                  <FormControl>
                    <Textarea {...field} placeholder="Optional description for this account" />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Validation Options */}
            {mode === 'create' && (
              <Card className="border-blue-500/20 bg-slate-900/50 dark:border-blue-400/30 dark:bg-slate-800/50">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg text-blue-300 dark:text-blue-200">🔧 Connection Validation Options</CardTitle>
                  <CardDescription className="text-slate-300 dark:text-slate-400">
                    Configure how the account connection should be validated before creation
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <FormField
                    control={form.control}
                    name="validate_connection"
                    render={({ field }) => (
                      <FormItem className={`flex flex-row items-center justify-between rounded-lg border p-4 shadow-sm transition-colors ${
                        field.value 
                          ? 'border-green-500/50 bg-green-900/20 dark:border-green-400/40 dark:bg-green-800/20' 
                          : 'border-slate-600 bg-slate-800/30 dark:border-slate-500 dark:bg-slate-700/30'
                      }`}>
                        <div className="space-y-0.5 flex-1">
                          <FormLabel className="text-base font-medium text-white dark:text-slate-100">
                            ✅ Enable Connection Validation
                            {field.value && <span className="ml-2 text-xs text-green-400">[ENABLED]</span>}
                          </FormLabel>
                          <FormDescription className="text-sm text-slate-300 dark:text-slate-400">
                            Validate that the account can connect to the trading servers before creation
                          </FormDescription>
                        </div>
                        <FormControl>
                          <Switch
                            checked={field.value}
                            onCheckedChange={field.onChange}
                            className="ml-4"
                          />
                        </FormControl>
                      </FormItem>
                    )}
                  />

                  {form.watch('validate_connection') && (
                    <>
                      <FormField
                        control={form.control}
                        name="allow_non_trading_validation"
                        render={({ field }) => (
                          <FormItem className={`flex flex-row items-center justify-between rounded-lg border p-4 shadow-sm transition-colors ${
                            field.value 
                              ? 'border-yellow-500/50 bg-yellow-900/20 dark:border-yellow-400/40 dark:bg-yellow-800/20' 
                              : 'border-slate-600 bg-slate-800/30 dark:border-slate-500 dark:bg-slate-700/30'
                          }`}>
                            <div className="space-y-0.5 flex-1">
                              <FormLabel className="text-base font-medium text-white dark:text-slate-100">
                                ⏰ Allow Non-Trading Hours Validation
                                {field.value && <span className="ml-2 text-xs text-yellow-400">[ENABLED]</span>}
                              </FormLabel>
                              <FormDescription className="text-sm text-slate-300 dark:text-slate-400">
                                Allow validation outside trading hours using basic connectivity testing
                              </FormDescription>
                            </div>
                            <FormControl>
                              <Switch
                                checked={field.value}
                                onCheckedChange={field.onChange}
                                className="ml-4"
                              />
                            </FormControl>
                          </FormItem>
                        )}
                      />

                      <FormField
                        control={form.control}
                        name="use_real_api_validation"
                        render={({ field }) => (
                          <FormItem className={`flex flex-row items-center justify-between rounded-lg border p-4 shadow-sm transition-colors ${
                            field.value 
                              ? 'border-red-500/50 bg-red-900/20 dark:border-red-400/40 dark:bg-red-800/20' 
                              : 'border-slate-600 bg-slate-800/30 dark:border-slate-500 dark:bg-slate-700/30'
                          }`}>
                            <div className="space-y-0.5 flex-1">
                              <FormLabel className="text-base font-medium text-white dark:text-slate-100">
                                🚀 Real API Login Validation
                                {field.value && <span className="ml-2 text-xs text-red-400 font-bold">[REAL API ENABLED]</span>}
                              </FormLabel>
                              <FormDescription className="text-sm text-slate-300 dark:text-slate-400">
                                <strong className="text-orange-400 dark:text-orange-300">Advanced:</strong> Perform actual vnpy gateway login with real credentials
                                <br />
                                <span className="text-xs text-red-400 dark:text-red-300 font-medium">
                                  ⚠️ This will attempt real login to the trading exchange
                                </span>
                              </FormDescription>
                            </div>
                            <FormControl>
                              <Switch
                                checked={field.value}
                                onCheckedChange={field.onChange}
                                className="ml-4"
                              />
                            </FormControl>
                          </FormItem>
                        )}
                      />

                      {form.watch('use_real_api_validation') && (
                        <Alert className="border-red-500/30 bg-red-900/30 dark:border-red-400/40 dark:bg-red-800/30">
                          <AlertCircle className="h-4 w-4 text-red-400 dark:text-red-300" />
                          <AlertDescription className="text-red-100 dark:text-red-200">
                            <strong className="text-red-300 dark:text-red-200">🔴 Real API Validation Enabled</strong>
                            <br />
                            <span className="text-red-200 dark:text-red-300">
                              This will perform actual login to the trading exchange using your credentials.
                            </span>
                            <div className="mt-2 p-2 bg-red-800/50 rounded text-sm">
                              <strong>Validation will:</strong>
                              <ul className="mt-1 ml-4 list-disc space-y-1 text-xs text-red-200">
                                <li>Connect to real trading servers</li>
                                <li>Authenticate with your username/password</li>
                                <li>Verify authorization codes</li>
                                <li>Receive official exchange responses</li>
                                <li>Disconnect immediately after validation</li>
                              </ul>
                            </div>
                          </AlertDescription>
                        </Alert>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Validation Result */}
            {validationResult && (
              <Alert className={validationResult.success ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50"}>
                {validationResult.success ? (
                  <CheckCircle2 className="h-4 w-4 text-green-600" />
                ) : (
                  <AlertCircle className="h-4 w-4 text-red-600" />
                )}
                <AlertDescription className={validationResult.success ? "text-green-800" : "text-red-800"}>
                  {validationResult.message}
                </AlertDescription>
              </Alert>
            )}

            {/* Form Actions */}
            <div className="flex justify-between space-x-4">
              <div className="flex space-x-2">
                <Button type="button" variant="outline" onClick={onCancel}>
                  Cancel
                </Button>
                {onValidate && (
                  <Button 
                    type="button" 
                    variant="secondary" 
                    onClick={handleValidate}
                    disabled={isValidating || !parsedSettings}
                  >
                    {isValidating ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Validating...
                      </>
                    ) : (
                      'Validate Account'
                    )}
                  </Button>
                )}
              </div>
              
              <Button type="submit" disabled={isSubmitting || !parsedSettings || !!duplicateIdError}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    {mode === 'create' ? 'Creating...' : 'Updating...'}
                  </>
                ) : (
                  mode === 'create' ? 'Create Account' : 'Update Account'
                )}
              </Button>
            </div>
          </form>
        </Form>
      </CardContent>
    </Card>
  );
}