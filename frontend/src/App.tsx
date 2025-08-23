import React from "react";
import { QueryClient, QueryClientProvider } from "react-query";
import GameForm from "./components/GameForm";

const queryClient = new QueryClient();

const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <div className="App">
        <GameForm />
      </div>
    </QueryClientProvider>
  );
};

export default App;
