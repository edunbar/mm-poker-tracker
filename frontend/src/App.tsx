import React from 'react';
import { QueryClient, QueryClientProvider } from 'react-query';
import GameForm from './components/GameForm';

const queryClient = new QueryClient();

const App: React.FC = () => {
    return (
        <QueryClientProvider client={queryClient}>
            <div className="App">
                <h1>Poker Analytics App</h1>
                <GameForm />
            </div>
        </QueryClientProvider>
    );
};

export default App;