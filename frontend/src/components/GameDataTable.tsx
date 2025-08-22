import React from "react";

interface PlayerInfo {
  id: string;
  names: string;
  buyInSum: number;
  buyOutSum: number;
  inGame: number;
  net: number;
  validated_name?: string;
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
  // Sort players by net, biggest to smallest
  const sortedPlayers = playersInfos
    .map((player, originalIdx) => ({ ...player, originalIdx }))
    .sort((a, b) => b.net - a.net);

  const handleChange = (
    index: number,
    field: keyof PlayerInfo,
    value: string | number | boolean
  ) => {
    const updated = [...playersInfos];
    if (field === "buyInSum" || field === "buyOutSum") {
      updated[index][field] = Number(value);
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
    } else if (field === "validated_name") {
      updated[index][field] = value as string;
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
          <th>Name</th>
          <th>IGN</th>
          <th>Buy In</th>
          <th>Cash Out</th>
          <th>Net</th>
        </tr>
      </thead>
      <tbody>
        {sortedPlayers.map((player, idx) => (
          <tr key={player.id || idx}>
            <td>
              <input
                type="text"
                value={player.id}
                onChange={(e) =>
                  handleChange(player.originalIdx, "id", e.target.value)
                }
              />
            </td>
            <td>
              <input
                type="text"
                value={player.validated_name || ""}
                onChange={(e) =>
                  handleChange(
                    player.originalIdx,
                    "validated_name",
                    e.target.value
                  )
                }
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
                onChange={(e) =>
                  handleChange(player.originalIdx, "names", e.target.value)
                }
              />
            </td>
            <td>
              <input
                type="number"
                value={player.buyInSum}
                onChange={(e) =>
                  handleChange(player.originalIdx, "buyInSum", e.target.value)
                }
              />
            </td>
            <td>
              <input
                type="number"
                value={
                  player.buyOutSum === 0 ? player.inGame : player.buyOutSum
                }
                onChange={(e) =>
                  handleChange(player.originalIdx, "buyOutSum", e.target.value)
                }
              />
            </td>
            <td>
              <input
                type="number"
                value={player.net}
                onChange={(e) =>
                  handleChange(player.originalIdx, "net", e.target.value)
                }
              />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default GameDataTable;
