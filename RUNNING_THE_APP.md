# How to Run Iva 2.0

## ❌ Common Error

```bash
npm run dev
# Error: Could not read package.json
```

**This is a Python project, not Node.js!** Use Python commands instead.

---

## ✅ Correct Way to Run

### Prerequisites Check

This project requires **Python 3.11+**. Check your version:

```bash
python3 --version
# If it shows 3.9.x or 3.10.x, you need to upgrade
```

### Step 1: Install Python 3.11+ (if needed)

**On macOS with Homebrew:**
```bash
brew install python@3.11
```

**Then use it explicitly:**
```bash
python3.11 --version  # Should show 3.11.x or higher
```

### Step 2: Install Dependencies

```bash
# Using Makefile (will use python3.11 if available)
make dev

# OR manually:
python3.11 -m pip install -r requirements.txt
python3.11 -m playwright install chromium
```

### Step 3: Run the Server

```bash
# Using Makefile
make run

# OR manually:
python3.11 -m uvicorn src.iva.server:app --host 0.0.0.0 --port 8080 --reload
```

### Step 4: Access the Application

Open your browser to: **http://localhost:8080**

---

## Using the Makefile

The Makefile uses `python` by default. To use Python 3.11+:

```bash
# Override the Python command
make run PY=python3.11

# Or update Makefile to use python3.11 by default
```

---

## Alternative: Use Docker

If you have Docker installed:

```bash
docker-compose up
```

This will use Python 3.11+ automatically.

---

## CLI Usage

```bash
# Verify a company claim
python3.11 -m src.iva.cli verify --url "https://example.com" --company "Example Inc"

# Or using Makefile
make cli URL="https://example.com" COMPANY="Example Inc" PY=python3.11
```

---

## Troubleshooting

### "cannot import name 'UTC' from 'datetime'"
- **Cause**: Python version < 3.11
- **Fix**: Install Python 3.11+ (see Step 1 above)

### "ModuleNotFoundError: No module named 'src'"
- **Cause**: Wrong working directory
- **Fix**: Run from project root: `cd /Users/benjaminwilliams/IVA_3.0/iva_2`

### "Command not found: python3.11"
- **Cause**: Python 3.11 not installed
- **Fix**: Install via Homebrew: `brew install python@3.11`

