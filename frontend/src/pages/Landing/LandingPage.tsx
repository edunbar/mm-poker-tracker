import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function LandingPage() {
  const [gameId, setGameId] = useState("");
  const [adminId, setAdminId] = useState("");
  const navigate = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (gameId && adminId) {
      navigate(
        `/ingest?gameId=${encodeURIComponent(
          gameId
        )}&adminId=${encodeURIComponent(adminId)}`
      );
    }
  };

  return (
    <div className="max-w-md mx-auto py-12">
      <h1 className="text-3xl font-bold mb-6">Poker Game Ingest</h1>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block font-medium mb-1">Game ID</label>
          <input
            type="text"
            value={gameId}
            onChange={(e) => setGameId(e.target.value)}
            className="border rounded px-3 py-2 w-full"
            required
          />
        </div>
        <div>
          <label className="block font-medium mb-1">Admin ID</label>
          <input
            type="text"
            value={adminId}
            onChange={(e) => setAdminId(e.target.value)}
            className="border rounded px-3 py-2 w-full"
            required
          />
        </div>
        <button
          type="submit"
          className="bg-blue-600 text-white px-4 py-2 rounded w-full"
        >
          Go to Game Ingest
        </button>
      </form>
    </div>
  );
}
