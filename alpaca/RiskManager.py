"""
Risk Management Module for Dynamic Position Sizing

This module provides risk management functionality based on market regime
background colors, adjusting position risk percentages accordingly.
"""

from typing import Dict, Optional
from enum import Enum

class RiskLevel(Enum):
    """Risk level enumeration based on background colors"""
    RED = "red"
    ORANGE = "orange" 
    YELLOW = "yellow"
    GREEN = "green"

class RiskManager:
    """Manages position risk based on market regime background color"""
    
    # Risk percentage mapping based on background color
    RISK_PERCENTAGES = {
        RiskLevel.RED: 0.0,      # No new positions
        RiskLevel.ORANGE: 0.1,   # 0.1% risk per position
        RiskLevel.YELLOW: 0.3,   # 0.3% risk per position
        RiskLevel.GREEN: 0.5     # 0.5% risk per position
    }
    
    def __init__(self):
        self.current_risk_level: Optional[RiskLevel] = None
        self.current_risk_percentage: Optional[float] = None
    
    def set_risk_level(self, background_color: str) -> None:
        """
        Set the current risk level based on background color
        
        Args:
            background_color: Background color string ('red', 'orange', 'yellow', 'green')
            
        Raises:
            ValueError: If background_color is invalid
        """
        try:
            self.current_risk_level = RiskLevel(background_color.lower())
            self.current_risk_percentage = self.RISK_PERCENTAGES[self.current_risk_level]
        except ValueError:
            valid_colors = [level.value for level in RiskLevel]
            raise ValueError(f"Invalid background color: {background_color}. Must be one of {valid_colors}")
    
    def get_risk_percentage(self, background_color: str) -> float:
        """
        Get risk percentage for a given background color
        
        Args:
            background_color: Background color string
            
        Returns:
            Risk percentage as decimal (e.g., 0.2 for 0.2%)
            
        Raises:
            ValueError: If background_color is invalid
        """
        try:
            risk_level = RiskLevel(background_color.lower())
            return self.RISK_PERCENTAGES[risk_level]
        except ValueError:
            valid_colors = [level.value for level in RiskLevel]
            raise ValueError(f"Invalid background color: {background_color}. Must be one of {valid_colors}")
    
    def can_enter_positions(self, background_color: str) -> bool:
        """
        Check if new positions can be entered based on background color
        
        Args:
            background_color: Background color string
            
        Returns:
            True if positions can be entered, False otherwise
        """
        risk_percentage = self.get_risk_percentage(background_color)
        return risk_percentage > 0.0
    
    def get_current_risk_percentage(self) -> float:
        """
        Get the current risk percentage
        
        Returns:
            Current risk percentage as decimal
            
        Raises:
            ValueError: If no risk level has been set
        """
        if self.current_risk_percentage is None:
            raise ValueError("No risk level has been set. Call set_risk_level() first.")
        
        return self.current_risk_percentage
    
    def get_current_risk_level(self) -> RiskLevel:
        """
        Get the current risk level
        
        Returns:
            Current RiskLevel enum value
            
        Raises:
            ValueError: If no risk level has been set
        """
        if self.current_risk_level is None:
            raise ValueError("No risk level has been set. Call set_risk_level() first.")
        
        return self.current_risk_level
    
    def get_risk_info(self, background_color: str) -> Dict[str, any]:
        """
        Get comprehensive risk information for a background color
        
        Args:
            background_color: Background color string
            
        Returns:
            Dictionary containing risk information
        """
        risk_percentage = self.get_risk_percentage(background_color)
        can_enter = self.can_enter_positions(background_color)
        
        return {
            'background_color': background_color,
            'risk_percentage': risk_percentage,
            'risk_percentage_formatted': f"{risk_percentage:.1f}%",
            'can_enter_positions': can_enter,
            'risk_level': RiskLevel(background_color.lower()).name
        }

def get_risk_percentage_for_color(background_color: str) -> float:
    """
    Convenience function to get risk percentage for a background color
    
    Args:
        background_color: Background color string
        
    Returns:
        Risk percentage as decimal
    """
    risk_manager = RiskManager()
    return risk_manager.get_risk_percentage(background_color)

def can_enter_positions_for_color(background_color: str) -> bool:
    """
    Convenience function to check if positions can be entered for a background color
    
    Args:
        background_color: Background color string
        
    Returns:
        True if positions can be entered, False otherwise
    """
    risk_manager = RiskManager()
    return risk_manager.can_enter_positions(background_color)

if __name__ == "__main__":
    # Example usage
    risk_manager = RiskManager()
    
    colors = ['red', 'orange', 'yellow', 'green']
    
    print("=== Risk Management by Background Color ===")
    for color in colors:
        try:
            risk_info = risk_manager.get_risk_info(color)
            print(f"\n{color.upper()}:")
            print(f"  Risk Percentage: {risk_info['risk_percentage_formatted']}")
            print(f"  Can Enter Positions: {risk_info['can_enter_positions']}")
            print(f"  Risk Level: {risk_info['risk_level']}")
        except ValueError as e:
            print(f"Error for {color}: {e}")
    
    # Test setting and getting current risk level
    print(f"\n=== Testing Current Risk Level ===")
    risk_manager.set_risk_level('yellow')
    print(f"Current Risk Level: {risk_manager.get_current_risk_level().name}")
    print(f"Current Risk Percentage: {risk_manager.get_current_risk_percentage():.1f}%")
