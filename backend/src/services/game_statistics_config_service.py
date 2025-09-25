"""
Game Statistics Configuration Service

Manages configurable poker statistics classification thresholds based on game type.
Provides adaptive classifications that make sense for different game contexts
(tournament, cash game, friendly high-stack, etc.)
"""

from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from db.models import GameStatisticsConfig, Game
from dataclasses import dataclass
from enum import Enum


class GameType(Enum):
    TOURNAMENT = "tournament"
    CASH_GAME = "cashGame"
    FRIENDLY_HIGH_STACK = "friendlyHighStack"
    CUSTOM = "custom"


@dataclass
class StatisticsThresholds:
    """Holds all classification thresholds for a game type"""
    # VPIP thresholds
    vpip_tight: int
    vpip_normal: int
    vpip_loose: int

    # PFR thresholds
    pfr_passive: int
    pfr_normal: int
    pfr_aggressive: int

    # AF thresholds
    af_passive: int
    af_aggressive: int


@dataclass
class PlayerClassification:
    """Complete player classification based on game-specific thresholds"""
    # Raw statistics
    vpip: float
    pfr: float
    af: float

    # Categories relative to game type
    vpip_category: str  # 'tight', 'normal', 'loose', 'very-loose'
    pfr_category: str   # 'passive', 'normal', 'aggressive', 'very-aggressive'
    af_category: str    # 'passive', 'normal', 'aggressive'

    # Combined style classification
    style: str
    style_color: str
    description: str


class GameStatisticsConfigService:
    """Service for managing game statistics configuration and classification"""

    # Predefined game type configurations
    PREDEFINED_CONFIGS = {
        GameType.TOURNAMENT: StatisticsThresholds(
            vpip_tight=22, vpip_normal=28, vpip_loose=35,
            pfr_passive=10, pfr_normal=18, pfr_aggressive=25,
            af_passive=40, af_aggressive=60
        ),
        GameType.CASH_GAME: StatisticsThresholds(
            vpip_tight=25, vpip_normal=35, vpip_loose=45,
            pfr_passive=12, pfr_normal=20, pfr_aggressive=30,
            af_passive=35, af_aggressive=55
        ),
        GameType.FRIENDLY_HIGH_STACK: StatisticsThresholds(
            vpip_tight=45, vpip_normal=55, vpip_loose=65,
            pfr_passive=10, pfr_normal=20, pfr_aggressive=30,
            af_passive=30, af_aggressive=45
        )
    }

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_or_create_game_config(self, game_id: str) -> GameStatisticsConfig:
        """Get or create configuration for a game (defaults to friendlyHighStack)"""
        config = (self.db.query(GameStatisticsConfig)
                 .filter(GameStatisticsConfig.game_id == game_id)
                 .first())

        if not config:
            # Create default config for the game
            default_thresholds = self.PREDEFINED_CONFIGS[GameType.FRIENDLY_HIGH_STACK]
            config = GameStatisticsConfig(
                game_id=game_id,
                config_name=GameType.FRIENDLY_HIGH_STACK.value,
                vpip_tight_threshold=default_thresholds.vpip_tight,
                vpip_normal_threshold=default_thresholds.vpip_normal,
                vpip_loose_threshold=default_thresholds.vpip_loose,
                pfr_passive_threshold=default_thresholds.pfr_passive,
                pfr_normal_threshold=default_thresholds.pfr_normal,
                pfr_aggressive_threshold=default_thresholds.pfr_aggressive,
                af_passive_threshold=default_thresholds.af_passive,
                af_aggressive_threshold=default_thresholds.af_aggressive,
            )
            self.db.add(config)
            self.db.commit()

        return config

    def update_game_config(self, game_id: str, config_type: str, custom_thresholds: Optional[Dict] = None) -> GameStatisticsConfig:
        """Update game configuration with new type or custom thresholds"""
        config = self.get_or_create_game_config(game_id)

        if config_type == GameType.CUSTOM.value and custom_thresholds:
            # Apply custom thresholds
            config.config_name = config_type
            for key, value in custom_thresholds.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        else:
            # Apply predefined configuration
            game_type = GameType(config_type)
            thresholds = self.PREDEFINED_CONFIGS[game_type]

            config.config_name = config_type
            config.vpip_tight_threshold = thresholds.vpip_tight
            config.vpip_normal_threshold = thresholds.vpip_normal
            config.vpip_loose_threshold = thresholds.vpip_loose
            config.pfr_passive_threshold = thresholds.pfr_passive
            config.pfr_normal_threshold = thresholds.pfr_normal
            config.pfr_aggressive_threshold = thresholds.pfr_aggressive
            config.af_passive_threshold = thresholds.af_passive
            config.af_aggressive_threshold = thresholds.af_aggressive

        self.db.commit()
        return config

    def classify_player(self, vpip: float, pfr: float, af: float, game_config: GameStatisticsConfig) -> PlayerClassification:
        """Classify a player based on game-specific thresholds"""

        # Classify VPIP
        if vpip < game_config.vpip_tight_threshold:
            vpip_category = 'tight'
        elif vpip < game_config.vpip_normal_threshold:
            vpip_category = 'normal'
        elif vpip < game_config.vpip_loose_threshold:
            vpip_category = 'loose'
        else:
            vpip_category = 'very-loose'

        # Classify PFR
        if pfr < game_config.pfr_passive_threshold:
            pfr_category = 'passive'
        elif pfr < game_config.pfr_normal_threshold:
            pfr_category = 'normal'
        elif pfr < game_config.pfr_aggressive_threshold:
            pfr_category = 'aggressive'
        else:
            pfr_category = 'very-aggressive'

        # Classify AF
        if af < game_config.af_passive_threshold:
            af_category = 'passive'
        elif af < game_config.af_aggressive_threshold:
            af_category = 'normal'
        else:
            af_category = 'aggressive'

        # Determine combined style and description
        style, style_color, description = self._determine_play_style(
            vpip, pfr, af, vpip_category, pfr_category, af_category, game_config
        )

        return PlayerClassification(
            vpip=vpip,
            pfr=pfr,
            af=af,
            vpip_category=vpip_category,
            pfr_category=pfr_category,
            af_category=af_category,
            style=style,
            style_color=style_color,
            description=description
        )

    def _determine_play_style(self, vpip: float, pfr: float, af: float,
                            vpip_cat: str, pfr_cat: str, af_cat: str,
                            config: GameStatisticsConfig) -> Tuple[str, str, str]:
        """Determine play style based on categories and specific thresholds using fun, descriptive names"""

        # Special cases (check these first)
        if vpip > 65 and pfr < 10:
            return ("Calling Station", "bg-red-100 text-red-800",
                   "Plays everything, never raises - the ATM of poker")

        if vpip > 70 and pfr > 35:
            return ("Maniac", "bg-purple-100 text-purple-800",
                   "Maximum chaos - plays and raises with almost everything")

        if vpip > 70 and pfr < 15:
            return ("ATM", "bg-red-100 text-red-800",
                   "Gives money away by playing too many weak hands")

        if vpip < 40:  # Very tight for this game type
            if pfr < 10:
                return ("Super Nit", "bg-gray-100 text-gray-800",
                       "Barely plays at all - waiting for pocket aces")
            else:
                return ("Nit", "bg-gray-100 text-gray-800",
                       "Extremely tight even for this game")

        # VPIP > 65% (Very Loose)
        if vpip > 65:
            if pfr > 25:
                return ("Splashy Aggressive", "bg-blue-100 text-blue-800",
                       "Sees lots of flops and plays them aggressively")
            elif 15 <= pfr <= 25:
                return ("Splashy Balanced", "bg-cyan-100 text-cyan-800",
                       "Action player with decent balance")
            # < 15 covered by special cases above

        # VPIP 55-65% (Loose)
        elif vpip >= 55:
            if pfr > 30:
                return ("LAG Monster", "bg-red-100 text-red-800",
                       "Loose and extremely aggressive - dangerous opponent")
            elif 20 <= pfr <= 30:
                return ("Action Player", "bg-blue-100 text-blue-800",
                       "Creates lots of action and plays aggressively")
            elif 10 <= pfr < 20:
                return ("Loose Cannon", "bg-orange-100 text-orange-800",
                       "Unpredictable loose player")
            else:  # pfr < 10
                return ("Passive Fish", "bg-yellow-100 text-yellow-800",
                       "Plays many hands but lacks aggression")

        # Check for TAG Crusher first (high PFR regardless of VPIP in moderate range)
        elif pfr > 30:
            return ("TAG Crusher", "bg-green-100 text-green-800",
                   "Tight-aggressive crusher - premium hands only")

        # VPIP 45-55% (Standard for this game)
        elif vpip >= 45:
            if pfr > 25:
                return ("Aggressive Regular", "bg-green-100 text-green-800",
                       "Solid aggressive player for this game type")
            elif 15 <= pfr <= 25:
                return ("Active Player", "bg-green-100 text-green-800",
                       "Well-balanced and active style")
            else:  # pfr < 15
                return ("Passive Regular", "bg-yellow-100 text-yellow-800",
                       "Reasonable range but lacks aggression")

        # VPIP < 45% (Tight for this game) - remaining cases
        else:
            if 20 <= pfr <= 30:
                return ("Selective Aggressive", "bg-green-100 text-green-800",
                       "Selective but aggressive when involved")
            elif 10 <= pfr < 20:
                return ("Cautious Player", "bg-slate-100 text-slate-800",
                       "Plays it safe - solid but predictable")
            else:  # pfr < 10
                return ("Rock", "bg-gray-100 text-gray-800",
                       "Extremely passive - calls more than raises")

        # Fallback (shouldn't reach here)
        return ("Mystery Player", "bg-slate-100 text-slate-800",
               "Playing style unclear from available data")

    def get_config_description(self, config: GameStatisticsConfig) -> Dict:
        """Get human-readable description of current configuration"""
        return {
            "configType": config.config_name,
            "description": self._get_game_type_description(config.config_name),
            "thresholds": {
                "vpip": {
                    "tight": f"< {config.vpip_tight_threshold}%",
                    "normal": f"{config.vpip_tight_threshold}-{config.vpip_normal_threshold}%",
                    "loose": f"{config.vpip_normal_threshold}-{config.vpip_loose_threshold}%",
                    "veryLoose": f"> {config.vpip_loose_threshold}%"
                },
                "pfr": {
                    "passive": f"< {config.pfr_passive_threshold}%",
                    "normal": f"{config.pfr_passive_threshold}-{config.pfr_normal_threshold}%",
                    "aggressive": f"{config.pfr_normal_threshold}-{config.pfr_aggressive_threshold}%",
                    "veryAggressive": f"> {config.pfr_aggressive_threshold}%"
                },
                "af": {
                    "passive": f"< {config.af_passive_threshold}%",
                    "normal": f"{config.af_passive_threshold}-{config.af_aggressive_threshold}%",
                    "aggressive": f"> {config.af_aggressive_threshold}%"
                }
            }
        }

    def _get_game_type_description(self, config_name: str) -> str:
        """Get description of what each game type represents"""
        descriptions = {
            "tournament": "Traditional tournament poker with tight ranges",
            "cashGame": "Regular cash game with moderate ranges",
            "friendlyHighStack": "Casual deep-stack game with loose ranges - players see more flops",
            "custom": "Custom thresholds defined for this specific game"
        }
        return descriptions.get(config_name, "Custom configuration")

    def get_available_game_types(self) -> List[Dict]:
        """Get list of available predefined game types"""
        return [
            {
                "value": GameType.TOURNAMENT.value,
                "label": "Tournament",
                "description": "Traditional tight tournament ranges",
                "thresholds": "VPIP: Tight<22%, Normal<28%, Loose<35%"
            },
            {
                "value": GameType.CASH_GAME.value,
                "label": "Cash Game",
                "description": "Standard cash game ranges",
                "thresholds": "VPIP: Tight<25%, Normal<35%, Loose<45%"
            },
            {
                "value": GameType.FRIENDLY_HIGH_STACK.value,
                "label": "Friendly High-Stack",
                "description": "Casual deep-stack with loose ranges",
                "thresholds": "VPIP: Tight<45%, Normal<55%, Loose<65%"
            },
            {
                "value": GameType.CUSTOM.value,
                "label": "Custom",
                "description": "Define your own thresholds",
                "thresholds": "User-defined ranges"
            }
        ]