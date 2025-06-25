import { Metadata } from 'next';
import { LogViewer } from '@/components/logs/log-viewer';

export const metadata: Metadata = {
  title: 'System Logs - MDHub',
  description: 'Real-time system log monitoring and analysis',
};

export default function LogsPage() {
  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">System Logs</h1>
          <p className="text-muted-foreground">
            Real-time monitoring and analysis of system logs
          </p>
        </div>
      </div>
      <LogViewer />
    </div>
  );
}