import React, { useState } from 'react';
import { Button } from '../../../shared/ui/button';
import { Plus, Trash2, Calculator } from 'lucide-react';
import { HelpTooltip } from '../../../shared/ui/help-tooltip';

interface Player {
  id: string;
  name: string;
  buyIn: string;
  cashOut: string;
}

interface LiveGameFormProps {
  onSubmit: (data: {
    sessionName: string;
    players: Array<{
      name: string;
      buy_in: number;
      cash_out: number;
    }>;
    date?: string;
    gameNumber?: number;
  }) => void;
  isLoading?: boolean;
}

export default function LiveGameForm({ onSubmit, isLoading }: LiveGameFormProps) {
  const [sessionName, setSessionName] = useState('');
  const [gameNumber, setGameNumber] = useState('');
  const [date, setDate] = useState('');
  const [players, setPlayers] = useState<Player[]>([
    { id: '1', name: '', buyIn: '', cashOut: '' },
    { id: '2', name: '', buyIn: '', cashOut: '' }
  ]);
  const [errors, setErrors] = useState<string[]>([]);

  const addPlayer = () => {
    const newId = (Math.max(...players.map(p => parseInt(p.id))) + 1).toString();
    setPlayers([...players, { id: newId, name: '', buyIn: '', cashOut: '' }]);
  };

  const removePlayer = (id: string) => {
    if (players.length > 2) {
      setPlayers(players.filter(p => p.id !== id));
    }
  };

  const updatePlayer = (id: string, field: keyof Player, value: string) => {
    setPlayers(players.map(p => 
      p.id === id ? { ...p, [field]: value } : p
    ));
  };

  const validateForm = (): string[] => {
    const errors: string[] = [];

    if (!sessionName.trim()) {
      errors.push('Session name is required');
    }

    const validPlayers = players.filter(p => p.name.trim());
    if (validPlayers.length < 2) {
      errors.push('At least 2 players with names are required');
    }

    validPlayers.forEach((player, index) => {
      const buyIn = parseFloat(player.buyIn) || 0;
      const cashOut = parseFloat(player.cashOut) || 0;

      if (buyIn < 0 || cashOut < 0) {
        errors.push(`Player ${index + 1} (${player.name}): All amounts must be non-negative`);
      }

      if (buyIn === 0 && cashOut === 0) {
        errors.push(`Player ${index + 1} (${player.name}): At least one amount must be greater than 0`);
      }
    });

    if (gameNumber && (parseInt(gameNumber) < 1)) {
      errors.push('Game number must be a positive integer');
    }

    return errors;
  };

  const calculateTotals = () => {
    const validPlayers = players.filter(p => p.name.trim());
    const totalBuyIn = validPlayers.reduce((sum, p) => sum + (parseFloat(p.buyIn) || 0), 0);
    const totalCashOut = validPlayers.reduce((sum, p) => sum + (parseFloat(p.cashOut) || 0), 0);
    const balance = totalCashOut - totalBuyIn;

    return { totalBuyIn, totalCashOut, balance };
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    const validationErrors = validateForm();
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    const validPlayers = players
      .filter(p => p.name.trim())
      .map(p => ({
        name: p.name.trim(),
        buy_in: parseFloat(p.buyIn) || 0,
        cash_out: parseFloat(p.cashOut) || 0
      }));

    const submitData = {
      sessionName: sessionName.trim(),
      players: validPlayers,
      ...(date && { date }),
      ...(gameNumber && { gameNumber: parseInt(gameNumber) })
    };

    setErrors([]);
    onSubmit(submitData);
  };

  const totals = calculateTotals();
  const isBalanced = Math.abs(totals.balance) < 0.01;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-lg border shadow-sm">
        <div className="border-b p-4">
          <h3 className="text-lg font-semibold">Live Game Details</h3>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label htmlFor="sessionName" className="block text-sm font-medium text-gray-700 mb-1">
                Session Name *
              </label>
              <input
                id="sessionName"
                type="text"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="e.g., Thursday Night Game #15"
              />
            </div>
            <div>
              <label htmlFor="gameNumber" className="block text-sm font-medium text-gray-700 mb-1 flex items-center gap-2">
                Game Number (optional)
                <HelpTooltip content="Game number will be auto-assigned if left empty" />
              </label>
              <input
                id="gameNumber"
                type="number"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={gameNumber}
                onChange={(e) => setGameNumber(e.target.value)}
                placeholder="Auto-assigned if empty"
              />
            </div>
            <div>
              <label htmlFor="date" className="block text-sm font-medium text-gray-700 mb-1">
                Date (optional)
              </label>
              <input
                id="date"
                type="datetime-local"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border shadow-sm">
        <div className="border-b p-4 flex flex-row items-center justify-between">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            Players
            <HelpTooltip content="Player names should match previous sessions for consistent tracking" />
          </h3>
          <Button type="button" onClick={addPlayer} variant="outline" size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Player
          </Button>
        </div>
        <div className="p-4">
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-2 font-medium text-sm text-gray-600">
              <div>Player Name</div>
              <div className="flex items-center gap-2">
                Buy In ($)
                <HelpTooltip content="Enter buy-ins in dollars (e.g., 100.00)" />
              </div>
              <div className="flex items-center gap-2">
                Cash Out ($)
                <HelpTooltip content="Enter cash-outs in dollars (e.g., 100.00)" />
              </div>
              <div>Net</div>
            </div>
            
            {players.map((player) => {
              const buyIn = parseFloat(player.buyIn) || 0;
              const cashOut = parseFloat(player.cashOut) || 0;
              const net = cashOut - buyIn;
              
              return (
                <div key={player.id} className="grid grid-cols-4 gap-2 items-center">
                  <input
                    type="text"
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    value={player.name}
                    onChange={(e) => updatePlayer(player.id, 'name', e.target.value)}
                    placeholder="Player name"
                  />
                  <input
                    type="number"
                    step="0.01"
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    value={player.buyIn}
                    onChange={(e) => updatePlayer(player.id, 'buyIn', e.target.value)}
                    placeholder="0.00"
                  />
                  <input
                    type="number"
                    step="0.01"
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    value={player.cashOut}
                    onChange={(e) => updatePlayer(player.id, 'cashOut', e.target.value)}
                    placeholder="0.00"
                  />
                  <div className="flex items-center gap-2">
                    <span className={`font-mono ${net >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                      {net >= 0 ? '+' : ''}${net.toFixed(2)}
                    </span>
                    {players.length > 2 && (
                      <button
                        type="button"
                        className="p-1 text-gray-400 hover:text-red-600 transition-colors"
                        onClick={() => removePlayer(player.id)}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      <div className="bg-white rounded-lg border shadow-sm">
        <div className="border-b p-4">
          <h3 className="text-lg font-semibold flex items-center gap-2">
            <Calculator className="h-5 w-5" />
            Session Summary
          </h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div>
              <div className="text-gray-600">Total Buy-ins</div>
              <div className="font-mono text-lg">${totals.totalBuyIn.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-gray-600">Total Cash-outs</div>
              <div className="font-mono text-lg">${totals.totalCashOut.toFixed(2)}</div>
            </div>
            <div>
              <div className="text-gray-600 flex items-center gap-2">
                Balance
                <HelpTooltip content="The balance should equal 0 if all money is accounted for" />
              </div>
              <div className={`font-mono text-lg ${isBalanced ? 'text-green-600' : 'text-red-600'}`}>
                {totals.balance >= 0 ? '+' : ''}${totals.balance.toFixed(2)}
              </div>
            </div>
          </div>
          
          {!isBalanced && (
            <div className="mt-4 p-4 bg-yellow-50 border-l-4 border-yellow-400 rounded">
              <p className="text-yellow-800">
                ⚠️ Session doesn't balance. Total cash-outs should equal total buy-ins.
                {Math.abs(totals.balance) > 0.01 && ` Difference: $${Math.abs(totals.balance).toFixed(2)}`}
              </p>
            </div>
          )}
        </div>
      </div>

      {errors.length > 0 && (
        <div className="p-4 bg-red-50 border-l-4 border-red-400 rounded">
          <ul className="list-disc list-inside space-y-1 text-red-800">
            {errors.map((error, index) => (
              <li key={index}>{error}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex gap-4">
        <Button 
          type="submit" 
          onClick={handleSubmit} 
          disabled={isLoading}
          className="flex-1"
        >
          {isLoading ? 'Submitting...' : 'Submit Live Game'}
        </Button>
      </div>
    </div>
  );
}