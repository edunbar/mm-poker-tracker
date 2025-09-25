/**
 * Player Style Classifier for Poker Statistics
 *
 * Provides fun, descriptive player style names based on VPIP/PFR/AF statistics
 * optimized for high-stack friendly cash games.
 */

export interface StyleInfo {
  name: string;
  color: string;
  description: string;
  emoji: string;
}

export interface PlayerStyleClassification extends StyleInfo {
  vpipCategory: string;
  pfrCategory: string;
  afCategory: string;
}

/**
 * Get fun player style name based on VPIP and PFR statistics
 */
export function getPlayerStyleName(vpip: number, pfr: number, af?: number): string {
  const style = getPlayerStyle(vpip, pfr, af);
  return style.name;
}

/**
 * Get complete player style information including color, description, and emoji
 */
export function getPlayerStyle(vpip: number, pfr: number, _af?: number): StyleInfo {
  // Check special cases first
  if (vpip > 65 && pfr < 10) {
    return {
      name: "Calling Station",
      color: "bg-red-100 text-red-800 hover:bg-red-200",
      description: "Plays everything, never raises - the ATM of poker",
      emoji: ""
    };
  }

  if (vpip > 70 && pfr > 35) {
    return {
      name: "Maniac",
      color: "bg-purple-100 text-purple-800 hover:bg-purple-200",
      description: "Maximum chaos - plays and raises with almost everything",
      emoji: ""
    };
  }

  if (vpip > 70 && pfr < 15) {
    return {
      name: "ATM",
      color: "bg-red-100 text-red-800 hover:bg-red-200",
      description: "Gives money away by playing too many weak hands",
      emoji: ""
    };
  }

  if (vpip < 40) {
    if (pfr < 10) {
      return {
        name: "Super Nit",
        color: "bg-gray-100 text-gray-800 hover:bg-gray-200",
        description: "Barely plays at all - waiting for pocket aces",
        emoji: ""
      };
    } else {
      return {
        name: "Nit",
        color: "bg-gray-100 text-gray-800 hover:bg-gray-200",
        description: "Extremely tight even for this game",
        emoji: ""
      };
    }
  }

  // VPIP > 65% (Very Loose)
  if (vpip > 65) {
    if (pfr > 25) {
      return {
        name: "Splashy Aggressive",
        color: "bg-blue-100 text-blue-800 hover:bg-blue-200",
        description: "Sees lots of flops and plays them aggressively",
        emoji: ""
      };
    } else if (pfr >= 15 && pfr <= 25) {
      return {
        name: "Splashy Balanced",
        color: "bg-cyan-100 text-cyan-800 hover:bg-cyan-200",
        description: "Action player with decent balance",
        emoji: ""
      };
    }
    // < 15 covered by special cases above
  }

  // VPIP 55-65% (Loose)
  if (vpip >= 55) {
    if (pfr > 30) {
      return {
        name: "LAG Monster",
        color: "bg-red-100 text-red-800 hover:bg-red-200",
        description: "Loose and extremely aggressive - dangerous opponent",
        emoji: ""
      };
    } else if (pfr >= 20 && pfr <= 30) {
      return {
        name: "Action Player",
        color: "bg-blue-100 text-blue-800 hover:bg-blue-200",
        description: "Creates lots of action and plays aggressively",
        emoji: ""
      };
    } else if (pfr >= 10 && pfr < 20) {
      return {
        name: "Loose Cannon",
        color: "bg-orange-100 text-orange-800 hover:bg-orange-200",
        description: "Unpredictable loose player",
        emoji: ""
      };
    } else { // pfr < 10
      return {
        name: "Passive Fish",
        color: "bg-yellow-100 text-yellow-800 hover:bg-yellow-200",
        description: "Plays many hands but lacks aggression",
        emoji: ""
      };
    }
  }

  // Check for TAG Crusher first (high PFR regardless of VPIP in 45-55 range)
  if (pfr > 30) {
    return {
      name: "TAG Crusher",
      color: "bg-green-100 text-green-800 hover:bg-green-200",
      description: "Tight-aggressive crusher - premium hands only",
      emoji: ""
    };
  }

  // VPIP 45-55% (Standard for this game)
  if (vpip >= 45) {
    if (pfr > 25) {
      return {
        name: "Aggressive Regular",
        color: "bg-green-100 text-green-800 hover:bg-green-200",
        description: "Solid aggressive player for this game type",
        emoji: ""
      };
    } else if (pfr >= 15 && pfr <= 25) {
      return {
        name: "Active Player",
        color: "bg-green-100 text-green-800 hover:bg-green-200",
        description: "Well-balanced and active style",
        emoji: ""
      };
    } else { // pfr < 15
      return {
        name: "Passive Regular",
        color: "bg-yellow-100 text-yellow-800 hover:bg-yellow-200",
        description: "Reasonable range but lacks aggression",
        emoji: ""
      };
    }
  }

  // VPIP < 45% (Tight for this game) - remaining cases
  if (pfr >= 20 && pfr <= 30) {
    return {
      name: "Selective Aggressive",
      color: "bg-green-100 text-green-800 hover:bg-green-200",
      description: "Selective but aggressive when involved",
      emoji: ""
    };
  } else if (pfr >= 10 && pfr < 20) {
    return {
      name: "Cautious Player",
      color: "bg-slate-100 text-slate-800 hover:bg-slate-200",
      description: "Plays it safe - solid but predictable",
      emoji: ""
    };
  } else { // pfr < 10
    return {
      name: "Rock",
      color: "bg-gray-100 text-gray-800 hover:bg-gray-200",
      description: "Extremely passive - calls more than raises",
      emoji: ""
    };
  }
}

/**
 * Get extended player style classification with category breakdowns
 */
export function getPlayerStyleClassification(vpip: number, pfr: number, af = 0): PlayerStyleClassification {
  const style = getPlayerStyle(vpip, pfr, af);

  // Classify VPIP categories (adapted for high-stack cash games)
  let vpipCategory: string;
  if (vpip < 45) vpipCategory = 'tight';
  else if (vpip < 55) vpipCategory = 'normal';
  else if (vpip < 65) vpipCategory = 'loose';
  else vpipCategory = 'very-loose';

  // Classify PFR categories
  let pfrCategory: string;
  if (pfr < 10) pfrCategory = 'passive';
  else if (pfr < 20) pfrCategory = 'normal';
  else if (pfr < 30) pfrCategory = 'aggressive';
  else pfrCategory = 'very-aggressive';

  // Classify AF categories
  let afCategory: string;
  if (af < 30) afCategory = 'passive';
  else if (af < 45) afCategory = 'normal';
  else afCategory = 'aggressive';

  return {
    ...style,
    vpipCategory,
    pfrCategory,
    afCategory
  };
}

/**
 * Test the function with the provided player examples
 */
export function testPlayerStyles() {
  const testPlayers = [
    { name: "Tomo", vpip: 69.8, pfr: 23.8, af: 32.7, expected: "Splashy Balanced" },
    { name: "Casey", vpip: 66.9, pfr: 29.6, af: 27.5, expected: "Splashy Aggressive" },
    { name: "Nuck", vpip: 49.4, pfr: 5.1, af: 25.0, expected: "Passive Regular" },
    { name: "Jack", vpip: 70.7, pfr: 13.6, af: 34.3, expected: "ATM" },
    { name: "Baker", vpip: 52.1, pfr: 6.2, af: 22.2, expected: "Passive Regular" },
    { name: "Eric", vpip: 45.3, pfr: 31.4, af: 24.1, expected: "TAG Crusher" }
  ];

  // Player Style Classification Test:
  // ================================

  // Test results would be logged here in development

  return testPlayers.map(player => ({
    ...player,
    actual: getPlayerStyleName(player.vpip, player.pfr, player.af)
  }));
}