# Serve Command Host Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the serve command to bind to 0.0.0.0 so the web UI is accessible from other devices (e.g., phone).

**Architecture:** Change the default host from 127.0.0.1 to 0.0.0.0 in the serve command's --host option.

**Tech Stack:** Python Click CLI, Uvicorn

---

## Analysis

**Current behavior:**
- `python src/main.py serve` binds to 127.0.0.1 (localhost only)
- Cannot access from phone或 other devices on the network

**Desired behavior:**
- `python src/main.py serve --host 0.0.0.0` binds to all interfaces
- Accessible from phone via local network IP

**Files:**
- Modify: `src/main.py:41` (change default value)

---

### Task 1: Change host default to 0.0.0.0

**Files:**
- Modify: `src/main.py:41`

- [ ] **Step 1: Change host default value**

Modify line 41 in `src/main.py`:
```python
# Before:
@click.option("--host", default="127.0.0.1", help="Server host")

# After:
@click.option("--host", default="0.0.0.0", help="Server host")
```

- [ ] **Step 2: Verify the change**

```bash
python src/main.py serve --help
```

Expected output should show: `--host default: 0.0.0.0`

---

## Usage

**To access from phone:**
1. Find computer's local IP: `hostname -I` or `ip addr show`
2. Run: `python src/main.py serve`
3. On phone: open `http://<YOUR_LOCAL_IP>:8701`

**To keep localhost only (security):**
- `python src/main.py serve --host 127.0.0.1`

---

## Plan complete and saved to `docs/superpowers/plans/2026-04-24-serve-host-binding.md`. 

**Two execution options:**

1. **Inline Execution (fastest for this simple change)** - I'll make the edit directly

2. **Subagent-Driven** - Not needed for this 1-file change

Which approach?