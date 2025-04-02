import React from 'react';
import classNames from 'classnames';

interface LogEntry {
  type: 'thinking' | 'action' | 'error';
  message: string;
  timestamp: string;
}

interface AILogProps {
  logs: LogEntry[];
}

const AILog: React.FC<AILogProps> = ({ logs }) => {
  const logRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logs]);

  return (
    <div className="w-full h-full bg-gray-900 rounded-lg overflow-hidden border-4 border-gray-700">
      <div className="flex items-center px-4 py-2 bg-gray-800 border-b-2 border-gray-700">
        <div className="flex space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded-full" />
          <div className="w-3 h-3 bg-yellow-500 rounded-full" />
          <div className="w-3 h-3 bg-green-500 rounded-full" />
        </div>
        <span className="ml-4 text-gray-400 font-pixel text-sm">AI Log</span>
      </div>
      <div
        ref={logRef}
        className="h-[calc(100%-2.5rem)] overflow-y-auto p-4 font-mono text-sm"
      >
        {logs.map((log, index) => (
          <div
            key={index}
            className={classNames('mb-2', {
              'text-blue-400': log.type === 'thinking',
              'text-green-400': log.type === 'action',
              'text-red-400': log.type === 'error',
            })}
          >
            <span className="text-gray-500">[{log.timestamp}]</span>{' '}
            <span className="font-pixel">{log.message}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AILog; 