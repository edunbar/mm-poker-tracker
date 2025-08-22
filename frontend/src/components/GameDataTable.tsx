import React from "react";

interface PlayerInfo {
  id: string;
  names: string;
  buyInSum: number;
  buyOutSum: number;
  inGame: number;
  net: number;
}

interface GameDataTableProps {
  playersInfos: PlayerInfo[];
  setEditableData: React.Dispatch<React.SetStateAction<PlayerInfo[]>>;
}

// TODO: Add ability for math expressions in cells

const GameDataTable: React.FC<GameDataTableProps> = ({
  playersInfos,
  setEditableData,
}) => {
  const handleChange = (
    index: number,
    field: keyof PlayerInfo,
    value: string | number | boolean
  ) => {
    const updated = [...playersInfos];
    if (field === "buyInSum" || field === "buyOutSum") {
      updated[index][field] = Number(value);
      // Recalculate net when buyInSum or buyOutSum changes
      updated[index].net = updated[index].buyOutSum - updated[index].buyInSum;
    } else if (field === "net") {
      updated[index][field] = Number(value);
    } else if (field === "id") {
      updated[index][field] = value as string;
    } else if (field === "names") {
      updated[index][field] = (value as string)
        .split(",")
        .map((n) => n.trim())
        .join(",");
    }
    setEditableData(updated);
  };

  if (!Array.isArray(playersInfos) || playersInfos.length === 0) {
    return <div>No player data available.</div>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>ID</th>
          <th>Name(s)</th>
          <th>Buy In</th>
          <th>Cash Out</th>
          <th>Net</th>
        </tr>
      </thead>
      <tbody>
        {playersInfos.map((player, idx) => (
          <tr key={player.id || idx}>
            <td>
              <input
                type="text"
                value={player.id}
                onChange={(e) => handleChange(idx, "id", e.target.value)}
              />
            </td>
            <td>
              <input
                type="text"
                value={
                  Array.isArray(player.names)
                    ? player.names.join(", ")
                    : player.names
                }
                onChange={(e) => handleChange(idx, "names", e.target.value)}
              />
            </td>
            <td>
              <input
                type="number"
                value={player.buyInSum}
                onChange={(e) => handleChange(idx, "buyInSum", e.target.value)}
              />
            </td>
            <td>
              <input
                type="number"
                value={
                  player.buyOutSum === 0 ? player.inGame : player.buyOutSum
                }
                onChange={(e) => handleChange(idx, "buyOutSum", e.target.value)}
              />
            </td>
            <td>
              <input
                type="number"
                value={player.net}
                onChange={(e) => handleChange(idx, "net", e.target.value)}
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default GameDataTable;
