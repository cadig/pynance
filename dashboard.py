import tkinter as tk
from tkinter import ttk, messagebox
import sys
import subprocess
from pathlib import Path
import configparser
import os
import shlex

class Config:
    def __init__(self):
        self.config = configparser.ConfigParser()
        config_path = Path(__file__).parent / 'config' / 'dashboard-config.ini'
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found at {config_path}")
        self.config.read(config_path)
        
    @property
    def repo_root(self):
        return os.path.expanduser(self.config.get('paths', 'repo_root'))
        
    @property
    def conda_env(self):
        return self.config.get('environment', 'conda_env')

class OrderEntrySection(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        return
        
    def setup_ui(self):
        # Create and configure style for Combobox
        style = ttk.Style()
        style.configure("Custom.TCombobox", fieldbackground="lightgrey", background="lightgrey")

        # Ticker input
        ttk.Label(self, text="Ticker:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ticker_entry = tk.Entry(self, width=15)
        self.ticker_entry.grid(row=0, column=1, padx=5, pady=5)

        # Minute selection dropdown
        ttk.Label(self, text="Minute Interval:", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.minute_var = tk.IntVar()
        self.minute_dropdown = ttk.Combobox(self, textvariable=self.minute_var, 
                                          values=[1, 2, 5, 15], state="readonly", 
                                          style="Custom.TCombobox",
                                          width=14)
        self.minute_dropdown.grid(row=1, column=1, padx=5, pady=5)
        self.minute_dropdown.current(0)

        # Dollars to risk input
        ttk.Label(self, text="Dollars to Risk:", anchor="w").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.dollars_entry = tk.Entry(self, width=15)
        self.dollars_entry.insert(0, "50")
        self.dollars_entry.grid(row=2, column=1, padx=5, pady=5)

        # Staggered Stops dropdown
        ttk.Label(self, text="Staggered Stops:", anchor="w").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.staggered_stops_var = tk.IntVar()
        self.staggered_stops_dropdown = ttk.Combobox(self, textvariable=self.staggered_stops_var, 
                                                   values=[1, 2, 3, 4], state="readonly", 
                                                   style="Custom.TCombobox",
                                                   width=14)
        self.staggered_stops_dropdown.grid(row=3, column=1, padx=5, pady=5)
        self.staggered_stops_dropdown.current(0)

        # Submit button
        ttk.Button(self, text="Place Order", command=self.run_script).grid(row=4, column=0, columnspan=2, pady=10)
        
        return

    def run_script(self):
        ticker = self.ticker_entry.get().strip()
        minuteToUse = self.minute_var.get()
        dollarsToRisk = self.dollars_entry.get().strip()
        staggeredStops = self.staggered_stops_var.get()
        
        if not ticker:
            messagebox.showerror("Input Error", "Ticker is required")
            return
        
        if not dollarsToRisk.isdigit() or int(dollarsToRisk) < 1:
            messagebox.showerror("Input Error", "Dollars to Risk must be a positive integer")
            return
        
        try:
            script_path = Path(__file__).parent / "ibkr" / "ibkrPlaceEntryOrder.py"
            args = [sys.executable, str(script_path), ticker, str(minuteToUse), 
                   dollarsToRisk, str(staggeredStops)]
            subprocess.run(args, check=True)
            messagebox.showinfo("Success", "Order placed successfully")
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Execution Error", f"Error running script: {e}")
            
        return
    
class LongVolBreakoutsSection(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Button(self, text="Start RVOL Scanner", command=self.run_script).pack(pady=2, anchor="w")

    def run_script(self):
        try:
            # Get absolute paths
            script_path = Path(__file__).parent / "ibkr" / "longVolBreakouts.py"
            repo_root = Path(self.config.repo_root).resolve()
            execution_dir = repo_root
            
            # Verify paths exist
            if not script_path.exists():
                raise FileNotFoundError(f"Script not found at: {script_path}")
            if not execution_dir.exists():
                raise FileNotFoundError(f"Execution directory not found at: {execution_dir}")
            
            # On macOS/Linux
            if sys.platform != "win32":
                # Construct the command with proper path handling
                cmd = f"conda activate {self.config.conda_env} && cd {execution_dir} && {sys.executable} {script_path}"
                
                # Debug output
                print(f"Executing command: {cmd}")
                print(f"Script path: {script_path}")
                print(f"Execution dir: {execution_dir}")
                
                # Execute with proper quoting
                subprocess.Popen(['osascript', '-e', 
                    f'tell application "Terminal" to do script "{cmd}"'])
            # On Windows
            else:
                cmd = f'conda activate {self.config.conda_env} && {sys.executable} {script_path}'
                subprocess.Popen(['start', 'cmd', '/k', cmd], shell=True)
                
        except Exception as e:
            messagebox.showerror("Execution Error", f"Error running script: {str(e)}")
            # Print the full error for debugging
            print(f"Full error: {e}")
    
class BreakoutStatsSection(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        # Ticker input
        ttk.Label(self, text="Ticker:", anchor="w").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.ticker_entry = tk.Entry(self, width=15)
        self.ticker_entry.grid(row=0, column=1, padx=5, pady=5)

        # Date input
        ttk.Label(self, text="Date (MM/DD/YYYY):", anchor="w").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.date_entry = tk.Entry(self, width=15)
        self.date_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Run button
        ttk.Button(self, text="Run Breakout Stats", command=self.run_script).grid(row=2, column=0, columnspan=2, pady=10)

    def run_script(self):
        ticker = self.ticker_entry.get()
        date = self.date_entry.get()
        
        if not ticker or not date:
            messagebox.showerror("Input Error", "Both ticker and date are required")
            return
            
        try:
            script_path = Path(__file__).parent / "research" / "getBreakoutStats.py"
            subprocess.run(["python", str(script_path), ticker, date], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Execution Error", f"Error running script: {e}")

class FinvizGainersSection(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Button(self, text="Get Recent Gainers", command=self.run_script).pack(pady=2, anchor="w")

    def run_script(self):
        try:
            script_path = Path(__file__).parent / "data" / "finvizConsolidateRecentGainers.py"
            subprocess.run(["python", str(script_path)], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Execution Error", f"Error running script: {e}")



class RiskAndOrdersSection(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Button(self, text="Check Risk and Orders", command=self.run_script).pack(pady=2, anchor="w")

    def run_script(self):
        try:
            script_path = Path(__file__).parent / "ibkr" / "checkRiskAndOrders.py"
            subprocess.run(["python", str(script_path)], check=True)
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Execution Error", f"Error running script: {e}")

class SPXSignalsSection(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        # Create button
        self.run_button = ttk.Button(
            self,
            text="Generate SPX Signals",
            command=self.run_script
        )
        self.run_button.pack(side='left', padx=5, pady=5)
        
    def run_script(self):
        try:
            # First run fetch_data.py
            fetch_data_path = Path(self.config.repo_root) / 'data' / 'fetch_data.py'
            subprocess.run([sys.executable, str(fetch_data_path)], check=True)
            
            # Then run combined-research.py that will generate the plot of latest combined research
            research_path = Path(self.config.repo_root) / 'research' / 'combined-research.py'
            subprocess.run([sys.executable, str(research_path)], check=True)
            
        except subprocess.CalledProcessError as e:
            messagebox.showerror("Error", f"Failed to generate SPX signals: {str(e)}")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {str(e)}")

class ExecutionTab(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        # Add RVOL Scanner section first
        self.rvol_section = LongVolBreakoutsSection(self, self.config)
        self.rvol_section.pack(fill='x', padx=5, pady=5)
        
        # Add Risk and Orders section
        self.risk_section = RiskAndOrdersSection(self)
        self.risk_section.pack(fill='x', padx=5, pady=5)
        
        # Add Order Entry section
        self.order_entry = OrderEntrySection(self, self.config)
        self.order_entry.pack(fill='x', padx=5, pady=5)

class ScriptsTab(ttk.Frame):
    def __init__(self, parent, config):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        
    def setup_ui(self):
        # Add Finviz Gainers section first
        self.finviz_section = FinvizGainersSection(self)
        self.finviz_section.pack(fill='x', padx=5, pady=5)
        
        # Add SPX Signals section
        self.spx_signals_section = SPXSignalsSection(self, self.config)
        self.spx_signals_section.pack(fill='x', padx=5, pady=5)

class Dashboard:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Trading Dashboard")
        self.root.geometry("600x400")
        
        try:
            self.config = Config()
        except Exception as e:
            messagebox.showerror("Configuration Error", str(e))
            self.root.destroy()
            return
        
        # Configure the ttk style
        self.style = ttk.Style()
        
        # Configure notebook tab colors
        self.style.configure("TNotebook.Tab", padding=[10, 2], background="#dcdcdc")
        self.style.configure("TNotebook", background='#f0f0f0')
        
        # Configure button colors
        self.style.configure("TButton", 
                           padding=5,
                           background="#dcdcdc",
                           foreground="black")
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.scripts_tab = ScriptsTab(self.notebook, self.config)
        self.execution_tab = ExecutionTab(self.notebook, self.config)
        
        # Add tabs to notebook
        self.notebook.add(self.scripts_tab, text="Scripts")
        self.notebook.add(self.execution_tab, text="Execution")
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    dashboard = Dashboard()
    dashboard.run()
