import { useState, useRef, useEffect } from 'react';
import { Send, ArrowDown } from 'lucide-react';
import { useConsoleWebSocket } from '../hooks';

interface ConsoleViewProps {
  serverId: number;
  serverName?: string;
}

export function ConsoleView({ serverId }: ConsoleViewProps) {
  const { messages, connected, sendCommand } = useConsoleWebSocket(serverId);
  const [command, setCommand] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const consoleRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [messages, autoScroll]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (command.trim()) {
      sendCommand(command.trim());
      setCommand('');
    }
  };

  const handleScroll = () => {
    if (consoleRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = consoleRef.current;
      setAutoScroll(scrollHeight - scrollTop - clientHeight < 50);
    }
  };

  const scrollToBottom = () => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
      setAutoScroll(true);
    }
  };

  const colorizeLog = (line: string) => {
    if (line.includes('[ERROR]') || line.includes('ERROR')) {
      return 'text-destructive';
    }
    if (line.includes('[WARN]') || line.includes('WARN')) {
      return 'text-accent';
    }
    if (line.includes('[INFO]') || line.includes('INFO')) {
      return 'text-console-text';
    }
    if (line.startsWith('>')) {
      return 'text-primary';
    }
    return 'text-console-text';
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-card-border">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold">Console</h2>
          <span className={`status-badge ${connected ? 'status-online' : 'status-offline'}`}>
            {connected ? 'Connected' : 'Disconnected'}
          </span>
        </div>

        <div className="flex items-center gap-2">
          {!autoScroll && (
            <button
              onClick={scrollToBottom}
              className="btn btn-ghost btn-sm"
            >
              <ArrowDown className="w-4 h-4" />
              Scroll to bottom
            </button>
          )}
        </div>
      </div>

      {/* Console Output */}
      <div
        ref={consoleRef}
        onScroll={handleScroll}
        className="console flex-1 m-4 p-2 overflow-y-auto"
        style={{ maxHeight: 'calc(100vh - 280px)' }}
      >
        {messages.length === 0 ? (
          <div className="text-center text-foreground-muted py-8">
            {connected ? 'Waiting for console output...' : 'Connect to see console output'}
          </div>
        ) : (
          messages.map((line, index) => (
            <div key={index} className={`console-line ${colorizeLog(line)}`}>
              {line}
            </div>
          ))
        )}
      </div>

      {/* Command Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-card-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={command}
            onChange={(e) => setCommand(e.target.value)}
            placeholder="Enter command..."
            disabled={!connected}
            className="input flex-1 font-mono"
          />
          <button
            type="submit"
            disabled={!connected || !command.trim()}
            className="btn btn-primary"
          >
            <Send className="w-4 h-4" />
            Send
          </button>
        </div>
      </form>
    </div>
  );
}
