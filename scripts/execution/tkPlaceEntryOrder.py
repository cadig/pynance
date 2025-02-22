import tkinter as tk
from tkinter import ttk, messagebox
import subprocess

def run_script():
    ticker = ticker_entry.get()
    minuteToUse = minute_var.get()
    sharesToBuy = shares_entry.get()
    
    if not ticker:
        messagebox.showerror("Input Error", "Ticker is required")
        return
    
    if not sharesToBuy.isdigit() or int(sharesToBuy) < 1:
        messagebox.showerror("Input Error", "Shares to Buy must be a positive integer")
        return
    
    # Run the script with the provided inputs
    try:
        subprocess.run(["python", "ibkrPlaceEntryOrder.py", ticker, str(minuteToUse), sharesToBuy], check=True)
        messagebox.showinfo("Success", "Order placed successfully")
    except subprocess.CalledProcessError as e:
        messagebox.showerror("Execution Error", f"Error running script: {e}")

# Create the GUI window
root = tk.Tk()
root.title("IBKR Order Placement")

# Ticker input
tk.Label(root, text="Ticker:").grid(row=0, column=0, padx=5, pady=5)
ticker_entry = tk.Entry(root)
ticker_entry.grid(row=0, column=1, padx=5, pady=5)

# Minute selection dropdown
tk.Label(root, text="Minute Interval:").grid(row=1, column=0, padx=5, pady=5)
minute_var = tk.IntVar()
minute_dropdown = ttk.Combobox(root, textvariable=minute_var, values=[1, 2, 5, 15], state="readonly")
minute_dropdown.grid(row=1, column=1, padx=5, pady=5)
minute_dropdown.current(0)

# Dollars to risk input
tk.Label(root, text="Dollar to Risk:").grid(row=2, column=0, padx=5, pady=5)
shares_entry = tk.Entry(root)
shares_entry.grid(row=2, column=1, padx=5, pady=5)

# Submit button
tk.Button(root, text="Place Order", command=run_script).grid(row=3, column=0, columnspan=2, pady=10)

# Run the GUI loop
root.mainloop()
