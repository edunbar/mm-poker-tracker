import { Calculator, Plus, Trash2 } from 'lucide-react';
import React, { useState } from 'react';
import { Button } from '../../../shared/ui/button';
import { FormField, FormLabel } from '../../../shared/ui/form-field';
import { HelpTooltip } from '../../../shared/ui/help-tooltip';
import { Input } from '../../../shared/ui/input';
import { Heading, Text } from '../../../shared/ui/typography';

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
      <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
        <div className="border-b p-4">
          <Heading variant="h3">Live Game Details</Heading>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <FormField>
              <FormLabel htmlFor="sessionName" required>
                Session Name
              </FormLabel>
              <Input
                id="sessionName"
                type="text"
                value={sessionName}
                onChange={(e) => setSessionName(e.target.value)}
                placeholder="e.g., Thursday Night Game #15"
              />
            </FormField>
            <FormField>
              <FormLabel htmlFor="gameNumber" className="flex items-center gap-2">
                Game Number (optional)
                <HelpTooltip content="Game number will be auto-assigned if left empty" />
              </FormLabel>
              <Input
                id="gameNumber"
                type="number"
                value={gameNumber}
                onChange={(e) => setGameNumber(e.target.value)}
                placeholder="Auto-assigned if empty"
              />
            </FormField>
            <FormField>
              <FormLabel htmlFor="date">
                Date (optional)
              </FormLabel>
              <Input
                id="date"
                type="datetime-local"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </FormField>
          </div>
        </div>
      </div>

      <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
        <div className="border-b p-4 flex flex-row items-center justify-between">
          <div className="flex items-center gap-2">
            <Heading variant="h3">Players</Heading>
            <HelpTooltip content="Player names should match previous sessions for consistent tracking" />
          </div>
          <Button type="button" onClick={addPlayer} variant="outline" size="sm">
            <Plus className="h-4 w-4 mr-2" />
            Add Player
          </Button>
        </div>
        <div className="p-4">
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-2">
              <Text variant="bodySmall" weight="medium" color="muted">Player Name</Text>
              <div className="flex items-center gap-2">
                <Text variant="bodySmall" weight="medium" color="muted">Buy In ($)</Text>
                <HelpTooltip content="Enter buy-ins in dollars (e.g., 100.00)" />
              </div>
              <div className="flex items-center gap-2">
                <Text variant="bodySmall" weight="medium" color="muted">Cash Out ($)</Text>
                <HelpTooltip content="Enter cash-outs in dollars (e.g., 100.00)" />
              </div>
              <Text variant="bodySmall" weight="medium" color="muted">Net</Text>
            </div>
            
            {players.map((player) => {
              const buyIn = parseFloat(player.buyIn) || 0;
              const cashOut = parseFloat(player.cashOut) || 0;
              const net = cashOut - buyIn;
              
              return (
                <div key={player.id} className="grid grid-cols-4 gap-2 items-center">
                  <Input
                    type="text"
                    value={player.name}
                    onChange={(e) => updatePlayer(player.id, 'name', e.target.value)}
                    placeholder="Player name"
                    size="sm"
                  />
                  <Input
                    type="number"
                    step="0.01"
                    value={player.buyIn}
                    onChange={(e) => updatePlayer(player.id, 'buyIn', e.target.value)}
                    placeholder="0.00"
                    size="sm"
                  />
                  <Input
                    type="number"
                    step="0.01"
                    value={player.cashOut}
                    onChange={(e) => updatePlayer(player.id, 'cashOut', e.target.value)}
                    placeholder="0.00"
                    size="sm"
                  />
                  <div className="flex items-center gap-2">
                    <Text className={`font-medium ${net >= 0 ? 'text-success' : 'text-destructive'}`}>
                      {net >= 0 ? '+' : ''}${net.toFixed(2)}
                    </Text>
                    {players.length > 2 && (
                      <button
                        type="button"
                        className="p-1 text-muted-foreground hover:text-destructive transition-colors"
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

      <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
        <div className="border-b p-4">
          <div className="flex items-center gap-2">
            <Calculator className="h-5 w-5" />
            <Heading variant="h3">Session Summary</Heading>
          </div>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <Text variant="bodySmall" color="muted">Total Buy-ins</Text>
              <Text className="font-medium">${totals.totalBuyIn.toFixed(2)}</Text>
            </div>
            <div>
              <Text variant="bodySmall" color="muted">Total Cash-outs</Text>
              <Text className="font-medium">${totals.totalCashOut.toFixed(2)}</Text>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <Text variant="bodySmall" color="muted">Balance</Text>
                <HelpTooltip content="The balance should equal 0 if all money is accounted for" />
              </div>
              <Text className={`font-medium ${isBalanced ? 'text-success' : 'text-destructive'}`}>
                {totals.balance >= 0 ? '+' : ''}${totals.balance.toFixed(2)}
              </Text>
            </div>
          </div>
          
          {!isBalanced && (
            <div className="mt-4 p-4 bg-warning/20 border-l-4 border-warning rounded">
              <Text variant="body" color="warning">
                ⚠️ Session doesn't balance. Total cash-outs should equal total buy-ins.
                {Math.abs(totals.balance) > 0.01 && ` Difference: $${Math.abs(totals.balance).toFixed(2)}`}
              </Text>
            </div>
          )}
        </div>
      </div>

      {errors.length > 0 && (
        <div className="p-4 bg-destructive/10 border-l-4 border-destructive rounded">
          <ul className="list-disc list-inside space-y-1">
            {errors.map((error, index) => (
              <li key={index}>
                <Text variant="body" color="destructive">{error}</Text>
              </li>
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