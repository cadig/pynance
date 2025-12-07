import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import logging

# ============================================================================
# CONFIGURATION - Modify these values as needed
# ============================================================================

# Symbol to analyze (without .csv extension)
SYMBOL = 'KMLM'

# Z-score calculation method
# Options:
#   - None: Use full history 
#          Pros: Shows long-term positioning
#          Cons: For trending assets (like SPX), early years always show negative z-scores
#                and later years always show positive z-scores (not useful for relative valuation)
#   
#   - Integer (e.g., 252): Rolling window in days 
#          Pros: Shows if price is cheap/expensive relative to recent past (e.g., past year)
#                Much more useful for identifying relative value opportunities
#          Cons: Requires sufficient history (at least window size)
#          Recommended: 252 (1 year) or 500 (2 years) for most assets
#   
#   - 'ewm': Exponential weighted moving (gives more weight to recent prices)
#          Pros: Smooth transition, more responsive to recent changes
#          Cons: Less intuitive than rolling window
Z_SCORE_METHOD = 252  # Use 252-day (1 year) rolling window - RECOMMENDED for relative valuation
# Z_SCORE_METHOD = None  # Uncomment to use full history
# Z_SCORE_METHOD = 'ewm'  # Uncomment to use exponential weighted

# For exponential weighted method, specify the span (half-life in days)
# Larger span = more weight to older data, smaller span = more weight to recent data
EWM_SPAN = 252  # 252 days half-life

# Z-score band configuration
Z_SCORE_MIN = -2.0  # Minimum z-score to display
Z_SCORE_MAX = 2.0   # Maximum z-score to display
Z_SCORE_BAND_SIZE = 0.5  # Size of each z-score band (0.5 = bands at -2, -1.5, -1, -0.5, 0, 0.5, 1, 1.5, 2)

# Color scheme for z-score bands
# Colors will be interpolated between these bands
# Negative z-scores (cheap) = green shades, positive z-scores (expensive) = red shades
COLOR_SCHEME = {
    'very_cheap': '#00FF00',      # Bright green for z < -1.5
    'cheap': '#90EE90',            # Light green for -1.5 <= z < -1
    'somewhat_cheap': '#ADFF2F',   # Yellow-green for -1 <= z < -0.5
    'neutral': '#FFFFE0',          # Light yellow for -0.5 <= z < 0
    'somewhat_expensive': '#FFD700', # Gold for 0 <= z < 0.5
    'expensive': '#FFA500',          # Orange for 0.5 <= z < 1
    'very_expensive': '#FF6347',    # Tomato for 1 <= z < 1.5
    'extremely_expensive': '#FF0000' # Red for z >= 1.5
}

# Chart configuration
CHART_FIGSIZE = (15, 8)  # Figure size (width, height)
CHART_TITLE_FONTSIZE = 14
CHART_LABEL_FONTSIZE = 12
CHART_GRID_ALPHA = 0.3
CHART_INTERACTIVE = True  # Enable interactive zoom and pan (True) or static display (False)

# ============================================================================

class ZScoreResearch:
    def __init__(self, symbol: str):
        """
        Initialize the Z-Score research analysis.
        
        Args:
            symbol (str): Symbol to analyze (without .csv extension)
        """
        self.symbol = symbol
        self.data_dir = Path(__file__).parent.parent / 'data'
        self.data = None
        self.log_prices = None
        self.z_scores = None
        self.mean_log_price = None
        self.std_log_price = None
        self.rolling_mean = None
        self.rolling_std = None
        
    def load_data(self) -> None:
        """
        Load symbol data from CSV file.
        """
        logging.info(f"Loading data for {self.symbol}...")
        
        # Construct file path
        file_path = self.data_dir / f'{self.symbol}.csv'
        
        if not file_path.exists():
            raise FileNotFoundError(f"Data file not found: {file_path}")
        
        # Load data
        self.data = pd.read_csv(file_path, index_col=0, parse_dates=True)
        
        # Ensure we have a 'close' column
        if 'close' not in self.data.columns:
            # Try to find a close column (case insensitive)
            close_cols = [col for col in self.data.columns if 'close' in col.lower()]
            if close_cols:
                self.data['close'] = self.data[close_cols[0]]
            else:
                raise ValueError(f"No 'close' column found in {file_path}")
        
        # Forward fill any missing values
        self.data = self.data.ffill()
        
        # Drop any remaining NaN values
        self.data = self.data.dropna()
        
        logging.info(f"Loaded {len(self.data)} rows of data")
        logging.info(f"Date range: {self.data.index.min()} to {self.data.index.max()}")
        
    def calculate_z_scores(self) -> None:
        """
        Calculate z-scores based on log prices.
        Supports three methods:
        1. Full history: Uses entire dataset mean/std (trends over time)
        2. Rolling window: Uses rolling window mean/std (relative to recent past)
        3. Exponential weighted: Uses EWM mean/std (more weight to recent prices)
        
        Z-score formula: z = (P - mean) / std
        """
        logging.info("Calculating z-scores from log prices...")
        
        # Get closing prices
        close_prices = self.data['close']
        
        # Calculate log prices
        self.log_prices = np.log(close_prices)
        
        # Calculate mean and standard deviation based on method
        if Z_SCORE_METHOD is None:
            # Full history method
            logging.info("Using full history for z-score calculation")
            self.mean_log_price = self.log_prices.mean()
            self.std_log_price = self.log_prices.std()
            self.rolling_mean = pd.Series(self.mean_log_price, index=self.log_prices.index)
            self.rolling_std = pd.Series(self.std_log_price, index=self.log_prices.index)
            
        elif Z_SCORE_METHOD == 'ewm':
            # Exponential weighted moving method
            logging.info(f"Using exponential weighted moving (span={EWM_SPAN}) for z-score calculation")
            self.rolling_mean = self.log_prices.ewm(span=EWM_SPAN, adjust=False).mean()
            self.rolling_std = self.log_prices.ewm(span=EWM_SPAN, adjust=False).std()
            # Store overall stats for display (use recent values)
            self.mean_log_price = self.rolling_mean.iloc[-1]
            self.std_log_price = self.rolling_std.iloc[-1]
            
        elif isinstance(Z_SCORE_METHOD, int):
            # Rolling window method
            logging.info(f"Using {Z_SCORE_METHOD}-day rolling window for z-score calculation")
            self.rolling_mean = self.log_prices.rolling(window=Z_SCORE_METHOD, min_periods=1).mean()
            self.rolling_std = self.log_prices.rolling(window=Z_SCORE_METHOD, min_periods=1).std()
            # Store overall stats for display (use recent values)
            self.mean_log_price = self.rolling_mean.iloc[-1]
            self.std_log_price = self.rolling_std.iloc[-1]
            
        else:
            raise ValueError(f"Invalid Z_SCORE_METHOD: {Z_SCORE_METHOD}. Must be None, 'ewm', or an integer.")
        
        # Calculate z-scores: z = (P - mean) / std
        # Use rolling mean/std for each point
        self.z_scores = (self.log_prices - self.rolling_mean) / self.rolling_std
        
        # Store z-scores in data dataframe
        self.data['z_score'] = self.z_scores
        self.data['rolling_mean'] = self.rolling_mean
        self.data['rolling_std'] = self.rolling_std
        
        # For rolling windows, fill initial NaN values with 0 (or first valid value)
        # This happens when window is larger than available data
        if Z_SCORE_METHOD is not None and isinstance(Z_SCORE_METHOD, int):
            # Fill NaN with backward fill, then forward fill if still NaN, then 0
            self.z_scores = self.z_scores.bfill().ffill().fillna(0)
        
        # Get valid z-scores for statistics (exclude NaN)
        valid_z_scores = self.z_scores.dropna()
        
        logging.info(f"Mean log price (current): {self.mean_log_price:.6f}")
        logging.info(f"Std log price (current): {self.std_log_price:.6f}")
        if len(valid_z_scores) > 0:
            logging.info(f"Z-score range: {valid_z_scores.min():.2f} to {valid_z_scores.max():.2f}")
        else:
            logging.warning("No valid z-scores calculated")
        
    def get_z_score_band(self, z_score: float) -> float:
        """
        Get the z-score band for a given z-score value.
        Bands are at intervals of Z_SCORE_BAND_SIZE.
        
        Args:
            z_score (float): Z-score value
            
        Returns:
            float: Lower bound of the z-score band
        """
        # Clamp z-score to the configured range
        z_score = max(Z_SCORE_MIN, min(Z_SCORE_MAX, z_score))
        
        # Round down to the nearest band
        band = np.floor(z_score / Z_SCORE_BAND_SIZE) * Z_SCORE_BAND_SIZE
        
        return band
    
    def get_color_for_z_score(self, z_score: float) -> str:
        """
        Get the color for a given z-score value.
        
        Args:
            z_score (float): Z-score value
            
        Returns:
            str: Hex color code
        """
        # Clamp z-score to the configured range
        z_score = max(Z_SCORE_MIN, min(Z_SCORE_MAX, z_score))
        
        # Determine color based on z-score bands
        if z_score < -1.5:
            return COLOR_SCHEME['very_cheap']
        elif z_score < -1.0:
            return COLOR_SCHEME['cheap']
        elif z_score < -0.5:
            return COLOR_SCHEME['somewhat_cheap']
        elif z_score < 0.0:
            return COLOR_SCHEME['neutral']
        elif z_score < 0.5:
            return COLOR_SCHEME['somewhat_expensive']
        elif z_score < 1.0:
            return COLOR_SCHEME['expensive']
        elif z_score < 1.5:
            return COLOR_SCHEME['very_expensive']
        else:
            return COLOR_SCHEME['extremely_expensive']
    
    def plot_price_with_z_score_background(self) -> None:
        """
        Plot the closing price with background colors based on z-score bands.
        Interactive zoom and pan enabled.
        """
        logging.info("Generating visualization...")
        
        # Enable interactive mode for zoom and pan if configured
        if CHART_INTERACTIVE:
            plt.ion()
        
        fig, ax = plt.subplots(figsize=CHART_FIGSIZE)
        
        # Get dates and prices
        dates = self.data.index
        prices = self.data['close']
        
        # First, plot the price line to establish the plot
        ax.plot(dates, prices, label=f'{self.symbol} Closing Price', 
                color='black', linewidth=2, zorder=10)
        
        # Get y-axis limits after plotting
        ax.set_ylim(prices.min() * 0.95, prices.max() * 1.05)
        y_min, y_max = ax.get_ylim()
        
        # Create background color bands based on z-scores
        # We'll iterate through the data and create colored regions using axvspan
        current_band = None
        band_start_idx = 0
        label_added = {}  # Track which band labels we've added to legend
        
        for i in range(len(self.z_scores)):
            z_score = self.z_scores.iloc[i]
            band = self.get_z_score_band(z_score)
            
            # If we've moved to a new band, draw the previous band
            if current_band is not None and band != current_band:
                # Draw the previous band
                if band_start_idx < i:
                    band_start_date = dates[band_start_idx]
                    band_end_date = dates[i - 1]
                    color = self.get_color_for_z_score(current_band)
                    
                    # Create label only once per band
                    band_key = f"{current_band:.1f}"
                    label = f'Z = {current_band:.1f}' if band_key not in label_added else ''
                    if label:
                        label_added[band_key] = True
                    
                    # Use axvspan for vertical span (better for time series)
                    ax.axvspan(band_start_date, band_end_date, 
                              ymin=0, ymax=1,
                              facecolor=color, alpha=0.3, edgecolor='none', 
                              zorder=0, label=label)
                
                # Start new band
                band_start_idx = i
                current_band = band
            elif current_band is None:
                # First band
                current_band = band
                band_start_idx = i
        
        # Draw the last band
        if band_start_idx < len(self.z_scores):
            band_start_date = dates[band_start_idx]
            band_end_date = dates[-1]
            color = self.get_color_for_z_score(current_band)
            
            band_key = f"{current_band:.1f}"
            label = f'Z = {current_band:.1f}' if band_key not in label_added else ''
            if label:
                label_added[band_key] = True
            
            ax.axvspan(band_start_date, band_end_date, 
                      ymin=0, ymax=1,
                      facecolor=color, alpha=0.3, edgecolor='none', 
                      zorder=0, label=label)
        
        # Set labels and title
        method_desc = self._get_method_description()
        ax.set_title(f'{self.symbol} Price with Z-Score Background ({method_desc})', 
                    fontsize=CHART_TITLE_FONTSIZE, fontweight='bold')
        ax.set_xlabel('Date', fontsize=CHART_LABEL_FONTSIZE)
        ax.set_ylabel(f'{self.symbol} Closing Price', fontsize=CHART_LABEL_FONTSIZE)
        
        # Add legend
        ax.legend(loc='best', fontsize=9, ncol=2)
        
        # Add grid
        ax.grid(True, alpha=CHART_GRID_ALPHA, zorder=5)
        
        # Format x-axis dates
        fig.autofmt_xdate()
        
        # Add text box with statistics
        method_desc = self._get_method_description()
        current_z = self.z_scores.iloc[-1] if not pd.isna(self.z_scores.iloc[-1]) else self.z_scores.dropna().iloc[-1] if len(self.z_scores.dropna()) > 0 else 0
        stats_text = f'Method: {method_desc}\n'
        stats_text += f'Mean Log Price: {self.mean_log_price:.4f}\n'
        stats_text += f'Std Log Price: {self.std_log_price:.4f}\n'
        stats_text += f'Current Z-Score: {current_z:.2f}'
        
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes,
                fontsize=9, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5), zorder=15)
        
        plt.tight_layout()
        
        # Print instructions for zoom and pan if interactive mode is enabled
        if CHART_INTERACTIVE:
            print("\n" + "="*60)
            print("CHART INTERACTION INSTRUCTIONS:")
            print("="*60)
            print("• Zoom: Click and drag to select a region, or use the zoom tool in the toolbar")
            print("• Pan: Click and drag the chart, or use the pan tool in the toolbar")
            print("• Reset: Click the home icon in the toolbar to reset the view")
            print("• Zoom In/Out: Use the +/- buttons in the toolbar")
            print("• Keyboard: Press 'h' for help, 'o' to toggle zoom, 'p' to toggle pan")
            print("="*60 + "\n")
            plt.show(block=True)  # Use block=True to keep the window open
        else:
            plt.show()  # Non-blocking for static display
        
        logging.info("Visualization complete")
    
    def _get_method_description(self) -> str:
        """
        Get a human-readable description of the z-score calculation method.
        
        Returns:
            str: Description of the method
        """
        if Z_SCORE_METHOD is None:
            return "Full History Z-Score"
        elif Z_SCORE_METHOD == 'ewm':
            return f"EWM Z-Score (span={EWM_SPAN})"
        elif isinstance(Z_SCORE_METHOD, int):
            return f"{Z_SCORE_METHOD}-Day Rolling Z-Score"
        else:
            return "Z-Score"

def main():
    """
    Main function to run the Z-Score research analysis.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Initialize research
    research = ZScoreResearch(symbol=SYMBOL)
    
    # Load data
    research.load_data()
    
    # Calculate z-scores
    research.calculate_z_scores()
    
    # Plot visualization
    research.plot_price_with_z_score_background()

if __name__ == "__main__":
    main()

