# Pinned to Debian 12 (bookworm) — Microsoft's ODBC Driver 18 repo below targets
# debian/12. Plain python:3.11-slim now tracks Debian 13 (trixie), which the MS
# repo doesn't publish for, so the msodbcsql18 install would fail.
FROM python:3.11-slim-bookworm

WORKDIR /app

# ---------------------------------------------------------------------------
# Microsoft ODBC Driver 18 for SQL Server — required by pyodbc to reach Azure SQL.
# (Local SQLite dev doesn't need this, but the production image does.)
# ---------------------------------------------------------------------------
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl gnupg unixodbc-dev gcc g++ \
    && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg \
    && echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
         > /etc/apt/sources.list.d/mssql-release.list \
    && apt-get update \
    && ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application backend code
COPY . .

# EXPOSE the target port for documentation clarity
EXPOSE 8000

# Container health = the app is up AND its database is reachable. curl is already
# present (installed above for the ODBC setup). start-period gives the app time to
# boot and make its first DB connection before failures count against it.
# NOTE: Azure Container Apps / App Service use their OWN probe config, not this
# HEALTHCHECK — point their readiness probe at the same /api/health/db path.
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD curl -fsS http://localhost:8000/api/health/db || exit 1

# The bulletproof startup command
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
