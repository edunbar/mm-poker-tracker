import React from "react";

interface GameUrlFormProps {
  gameUrl: string;
  setGameUrl: (url: string) => void;
  handleSubmit: (event: React.FormEvent) => void;
  isLoading: boolean;
}

const GameUrlForm: React.FC<GameUrlFormProps> = ({
  gameUrl,
  setGameUrl,
  handleSubmit,
  isLoading,
}) => (
  <div className="bg-card rounded-lg border border-border shadow-sm p-4 mb-6">
    <form onSubmit={handleSubmit} className="flex gap-4">
      <div className="flex-1">
        <label htmlFor="game_url" className="block text-sm font-medium text-foreground mb-2">
          PokerNow Game URL
        </label>
        <input
          type="text"
          id="game_url"
          value={gameUrl}
          onChange={(e) => setGameUrl(e.target.value)}
          required
          placeholder="https://www.pokernow.club/games/your-game-id"
          className="w-full px-3 py-2 border border-input rounded-md focus:outline-none focus:ring-2 focus:ring-ring focus:border-ring bg-background text-foreground"
        />
      </div>
      <div className="flex items-end">
        <button
          type="submit"
          disabled={isLoading}
          className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-2xl hover:bg-primary/90 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:opacity-50 transition-colors duration-150"
        >
          {isLoading ? "Loading..." : "Fetch Game Data"}
        </button>
      </div>
    </form>
  </div>
);

export default GameUrlForm;
