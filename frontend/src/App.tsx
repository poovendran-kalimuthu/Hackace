import React, { useEffect } from 'react';
import { useAppStore } from './store/useAppStore';
import { SinglePageFormatter } from './pages/SinglePageFormatter';

export const App: React.FC = () => {
  const { connectWebSocket } = useAppStore();

  useEffect(() => {
    connectWebSocket();
  }, []);

  return <SinglePageFormatter />;
};

export default App;
