FROM continuumio/miniconda3:latest

# Match the current workflow's conda environment exactly
RUN conda create -n pynance-v2.0 python=3.12 -y && \
    conda install -n pynance-v2.0 -c conda-forge -c anaconda \
      pandas numpy matplotlib jupyter ipython \
      requests beautifulsoup4 lxml pyyaml pip anthropic -y && \
    conda clean -afy

# Install pip packages (must use conda run to target the correct env)
RUN conda run -n pynance-v2.0 pip install --no-cache-dir \
      tradingview-datafeed yfinance

# Install git (needed for gh-pages restore steps in workflow)
RUN apt-get update && \
    apt-get install -y --no-install-recommends git && \
    rm -rf /var/lib/apt/lists/*

# Put the conda env's bin first on PATH so `python` resolves without
# needing `conda activate`
ENV PATH="/opt/conda/envs/pynance-v2.0/bin:$PATH"

# Smoke-test: confirm Python version and key imports
RUN python --version && \
    python -c "import pandas, numpy, matplotlib, yfinance, anthropic, requests, bs4, lxml, yaml; print('All imports OK')"
