import axios from "axios";

export const fetchGameData = async (gameUrl: string) => {
  // gameUrl is the full PokerNow game URL provided by the user
  const response = await axios.get(
    "http://localhost:8000/api/games/get_transactions",
    {
      params: { url: gameUrl },
    }
  );
  return response.data;
};

