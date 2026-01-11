import { useParams } from 'react-router-dom';
import { ConsoleView } from '../components';
import { Server } from '../types';

interface ConsolePageProps {
  server: Server | null;
}

export function ConsolePage({ server }: ConsolePageProps) {
  const { id } = useParams<{ id: string }>();
  const serverId = parseInt(id || '0');

  if (!server || server.id !== serverId) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center text-foreground-muted">
          <p>Server not found</p>
        </div>
      </div>
    );
  }

  if (!server.is_running) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-16 h-16 bg-secondary rounded-full flex items-center justify-center mx-auto mb-4">
            <div className="w-4 h-4 bg-offline rounded-full" />
          </div>
          <h3 className="text-lg font-semibold mb-2">Server Offline</h3>
          <p className="text-foreground-muted">
            Start the server to view the console
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <ConsoleView serverId={server.id} serverName={server.name} />
    </div>
  );
}
