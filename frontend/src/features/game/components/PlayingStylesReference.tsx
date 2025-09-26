import { ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import { Badge } from "../../../shared/ui/badge";
import { Heading, Text } from "../../../shared/ui/typography";

interface StyleInfo {
  name: string;
  description: string;
  category: string;
  color: string;
  vpipRange: string;
  pfrRange: string;
}

const playingStyles: StyleInfo[] = [
  // Special cases
  { name: 'Calling Station', description: 'Plays everything, never raises - the ATM of poker', category: 'Special Cases', color: 'bg-red-100 text-red-800 hover:bg-red-200', vpipRange: '>65%', pfrRange: '<10%' },
  { name: 'Maniac', description: 'Maximum chaos - plays and raises with almost everything', category: 'Special Cases', color: 'bg-purple-100 text-purple-800 hover:bg-purple-200', vpipRange: '>70%', pfrRange: '>35%' },
  { name: 'ATM', description: 'Gives money away by playing too many weak hands', category: 'Special Cases', color: 'bg-red-100 text-red-800 hover:bg-red-200', vpipRange: '>70%', pfrRange: '<15%' },
  { name: 'Super Nit', description: 'Barely plays at all - waiting for pocket aces', category: 'Special Cases', color: 'bg-gray-100 text-gray-800 hover:bg-gray-200', vpipRange: '<40%', pfrRange: '<10%' },
  { name: 'Nit', description: 'Extremely tight even for this game', category: 'Special Cases', color: 'bg-gray-100 text-gray-800 hover:bg-gray-200', vpipRange: '<40%', pfrRange: '≥10%' },

  // Very loose styles (65%+ VPIP)
  { name: 'Splashy Aggressive', description: 'Sees lots of flops and plays them aggressively', category: 'Very Loose (65%+ VPIP)', color: 'bg-blue-100 text-blue-800 hover:bg-blue-200', vpipRange: '>65%', pfrRange: '>25%' },
  { name: 'Splashy Balanced', description: 'Action player with decent balance', category: 'Very Loose (65%+ VPIP)', color: 'bg-cyan-100 text-cyan-800 hover:bg-cyan-200', vpipRange: '>65%', pfrRange: '15-25%' },

  // Loose styles (55-65% VPIP)
  { name: 'LAG Monster', description: 'Loose and extremely aggressive - dangerous opponent', category: 'Loose (55-65% VPIP)', color: 'bg-red-100 text-red-800 hover:bg-red-200', vpipRange: '55-65%', pfrRange: '>30%' },
  { name: 'Action Player', description: 'Creates lots of action and plays aggressively', category: 'Loose (55-65% VPIP)', color: 'bg-blue-100 text-blue-800 hover:bg-blue-200', vpipRange: '55-65%', pfrRange: '20-30%' },
  { name: 'Loose Cannon', description: 'Unpredictable loose player', category: 'Loose (55-65% VPIP)', color: 'bg-orange-100 text-orange-800 hover:bg-orange-200', vpipRange: '55-65%', pfrRange: '10-20%' },
  { name: 'Passive Fish', description: 'Plays many hands but lacks aggression', category: 'Loose (55-65% VPIP)', color: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200', vpipRange: '55-65%', pfrRange: '<10%' },

  // Standard styles (45-55% VPIP)
  { name: 'TAG Crusher', description: 'Tight-aggressive crusher - premium hands only', category: 'Standard (45-55% VPIP)', color: 'bg-green-100 text-green-800 hover:bg-green-200', vpipRange: 'Any', pfrRange: '>30%' },
  { name: 'Aggressive Regular', description: 'Solid aggressive player for this game type', category: 'Standard (45-55% VPIP)', color: 'bg-green-100 text-green-800 hover:bg-green-200', vpipRange: '45-55%', pfrRange: '>25%' },
  { name: 'Active Player', description: 'Well-balanced and active style', category: 'Standard (45-55% VPIP)', color: 'bg-green-100 text-green-800 hover:bg-green-200', vpipRange: '45-55%', pfrRange: '15-25%' },
  { name: 'Passive Regular', description: 'Reasonable range but lacks aggression', category: 'Standard (45-55% VPIP)', color: 'bg-yellow-100 text-yellow-800 hover:bg-yellow-200', vpipRange: '45-55%', pfrRange: '<15%' },

  // Tight styles (<45% VPIP)
  { name: 'Selective Aggressive', description: 'Selective but aggressive when involved', category: 'Tight (<45% VPIP)', color: 'bg-green-100 text-green-800 hover:bg-green-200', vpipRange: '<45%', pfrRange: '20-30%' },
  { name: 'Cautious Player', description: 'Plays it safe - solid but predictable', category: 'Tight (<45% VPIP)', color: 'bg-slate-100 text-slate-800 hover:bg-slate-200', vpipRange: '<45%', pfrRange: '10-20%' },
  { name: 'Rock', description: 'Extremely passive - calls more than raises', category: 'Tight (<45% VPIP)', color: 'bg-gray-100 text-gray-800 hover:bg-gray-200', vpipRange: '<45%', pfrRange: '<10%' },

  // Legacy support
  { name: 'TAG', description: 'Tight-Aggressive: Plays few hands but plays them aggressively', category: 'Legacy', color: 'bg-green-100 text-green-800 hover:bg-green-200', vpipRange: '<50%', pfrRange: '>15%' },
  { name: 'LAG', description: 'Loose-Aggressive: Plays many hands aggressively', category: 'Legacy', color: 'bg-blue-100 text-blue-800 hover:bg-blue-200', vpipRange: '>50%', pfrRange: '>15%' },
  { name: 'TP', description: 'Tight-Passive (Nit): Plays few hands and rarely bets/raises', category: 'Legacy', color: 'bg-gray-100 text-gray-800 hover:bg-gray-200', vpipRange: '<50%', pfrRange: '<15%' },
  { name: 'LP', description: 'Loose-Passive (Fish): Plays many hands but calls more than bets/raises', category: 'Legacy', color: 'bg-red-100 text-red-800 hover:bg-red-200', vpipRange: '>50%', pfrRange: '<15%' },
];

const groupedStyles = playingStyles.reduce((acc: Record<string, StyleInfo[]>, style) => {
  if (!acc[style.category]) {
    acc[style.category] = [];
  }
  const category = acc[style.category];
  if (category) {
    category.push(style);
  }
  return acc;
}, {} as Record<string, StyleInfo[]>);

export default function PlayingStylesReference() {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="bg-card text-card-foreground rounded-lg border border-border shadow-sm">
      <div
        className="p-6 cursor-pointer flex items-center justify-between hover:bg-muted/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div>
          <Heading variant="h3">Playing Styles Reference</Heading>
          <Text variant="body" color="muted" className="mt-1">
            Definitions of all playing style classifications
          </Text>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-5 h-5 text-muted-foreground" />
        ) : (
          <ChevronDown className="w-5 h-5 text-muted-foreground" />
        )}
      </div>

      {isExpanded && (
        <div className="px-6 pb-6 space-y-6">
          {Object.entries(groupedStyles).map(([category, styles]) => (
            <div key={category}>
              <Heading variant="h4" className="mb-3 text-muted-foreground uppercase tracking-wide text-sm">
                {category}
              </Heading>
              <div className="grid gap-3 md:grid-cols-1 lg:grid-cols-2">
                {styles.map((style) => (
                  <div key={style.name} className="p-4 bg-muted/30 rounded-md">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge
                        variant="secondary"
                        className={`${style.color} font-medium shrink-0`}
                      >
                        {style.name}
                      </Badge>
                      <div className="flex gap-2 text-xs">
                        <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded font-mono">
                          VPIP: {style.vpipRange}
                        </span>
                        <span className="bg-green-100 text-green-800 px-2 py-1 rounded font-mono">
                          PFR: {style.pfrRange}
                        </span>
                      </div>
                    </div>
                    <Text variant="bodySmall" className="leading-relaxed text-muted-foreground">
                      {style.description}
                    </Text>
                  </div>
                ))}
              </div>
            </div>
          ))}

          <div className="mt-6 pt-4 border-t border-border">
            <Text variant="bodySmall" color="muted">
              <strong>Note:</strong> Playing styles are determined by VPIP (Voluntarily Put money In Pot) and PFR (Pre-Flop Raise) statistics.
              Higher VPIP means playing more hands, higher PFR means more aggressive pre-flop play.
            </Text>
          </div>
        </div>
      )}
    </div>
  );
}