import React from "react";
import { Button } from "../../../shared/ui/button";
import { FormField, FormLabel } from "../../../shared/ui/form-field";
import { Input } from "../../../shared/ui/input";

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
        <FormField>
          <FormLabel htmlFor="game_url" required>
            PokerNow Game URL
          </FormLabel>
          <Input
            type="text"
            id="game_url"
            value={gameUrl}
            onChange={(e) => setGameUrl(e.target.value)}
            required
            placeholder="https://www.pokernow.club/games/your-game-id"
          />
        </FormField>
      </div>
      <div className="flex items-end">
        <Button
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? "Loading..." : "Fetch Game Data"}
        </Button>
      </div>
    </form>
  </div>
);

export default GameUrlForm;
