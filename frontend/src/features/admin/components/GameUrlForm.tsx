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
  <form onSubmit={handleSubmit} className="flex gap-2 mb-6">
    <input
      type="text"
      id="game_url"
      value={gameUrl}
      onChange={(e) => setGameUrl(e.target.value)}
      required
      placeholder="https://www.pokernow.club/games/your-game-id"
      className="flex-1 border rounded px-3 py-2"
    />
    <button
      type="submit"
      disabled={isLoading}
      className="bg-blue-600 text-white px-4 py-2 rounded"
    >
      {isLoading ? "Loading..." : "Fetch"}
    </button>
  </form>
);

export default GameUrlForm;
