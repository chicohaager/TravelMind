# Frontend Dockerfile for TravelMind (React + Vite)

FROM node:20-alpine

# Set working directory
WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy application code
COPY . .

# Expose port
EXPOSE 5173

# Shell-Form ist hier noetig: der HEALTHCHECK verkettet mit "||" bzw. nutzt
# eine Shell-Auswertung. In JSON-Notation gaebe es keine Verkettung.
# Health check
# hadolint ignore=DL3025
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:5173 || exit 1

# Run the development server
CMD ["npm", "run", "dev", "--", "--host"]
