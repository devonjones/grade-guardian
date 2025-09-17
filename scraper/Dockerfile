FROM node:22-slim

# Install system dependencies for Playwright
RUN apt-get update && apt-get install -y \
    libnss3 \
    libnspr4 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libatspi2.0-0 \
    libxss1 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/scraper

# Copy package files
COPY package*.json ./

# Install all dependencies (including dev for debugging)
RUN npm ci

# Install Playwright browsers
RUN npx playwright install chromium --with-deps

# Copy scraper code and debugging scripts
COPY *.js ./
COPY *.py ./

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Create output directory
RUN mkdir -p /app/data/scraped

# Set environment
ENV OUTPUT_DIR=/app/data/scraped
ENV NODE_ENV=production

# Expose Chrome remote debugging port
EXPOSE 9222

# Default command
CMD ["node", "dps_scraper.js"]
