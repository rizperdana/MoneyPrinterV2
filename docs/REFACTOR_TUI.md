# MoneyPrinterV2 TUI Refactor Plan

## Executive Summary

Refactor the MoneyPrinterV2 CLI application to use [Textual](https://textual.textualize.io/) framework for a modern Terminal User Interface (TUI). This replaces the current menu-driven CLI with an interactive dashboard featuring real-time progress tracking, live logs, and improved navigation.

**Target:** Python 3.12+  
**Framework:** Textual  
**Scope:** Full UI overhaul, replace existing CLI  
**Priority:** Video generation screen first

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Target Architecture](#2-target-architecture)
3. [Screen Designs](#3-screen-designs)
4. [Implementation Steps](#4-implementation-steps)
5. [File Organization](#5-file-organization)
6. [Migration Strategy](#6-migration-strategy)
7. [Risk Mitigation](#7-risk-mitigation)
8. [Testing Plan](#8-testing-plan)

---

## 1. Current State Analysis

### 1.1 Existing Entry Points

| File | Purpose | Lines | Issues |
|------|---------|-------|--------|
| `src/main.py` | Interactive CLI menu | ~700 | Deep nesting, blocking I/O |
| `src/run_pipeline.py` | Non-interactive pipeline | ~200 | Step-by-step print, no real-time UI |
| `src/run_24_7.py` | 24/7 content runner | ~150 | Log-based only |
| `src/batch_run.py` | Batch video creation | ~150 | CLI args, no UI |

### 1.2 UI Components

- **Menu System:** Nested `input()` calls in `main.py`
- **Output:** `status.py` module with `termcolor` + emoji prefixes
- **Tables:** PrettyTable for accounts/videos
- **Banner:** ASCII art from `assets/banner.txt`
- **No real-time updates** — all blocking terminal I/O

### 1.3 Pipeline Code

```
classes/YouTube.py     - 251 status.* calls scattered throughout
                        - Browser initialized in __init__ (blocking)
                        - generate_topic() → generate_video() → upload_video()
                        - No progress callbacks, only print statements
```

### 1.4 Identified Issues

| Issue | Impact | Fix Required |
|-------|--------|--------------|
| Blocking I/O | UI freezes during LLM calls, image gen | Async wrapper |
| Browser in __init__ | TUI event loop blocked | Lazy initialization |
| 251 status calls | Hard to track progress | Callback protocol |
| No session state | Can't see mid-process status | TUI state management |
| Deep menu nesting | Hard to navigate | Flat sidebar navigation |

---

## 2. Target Architecture

### 2.1 Layout Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│  MoneyPrinterV2 TUI                                              │
├────────────┬────────────────────────────────────────────────────┤
│            │  HEADER: Screen Title + Status Indicators         │
│  SIDEBAR   ├────────────────────────────────────────────────────┤
│            │                                                     │
│  - Dashboard |           MAIN CONTENT AREA                       │
│  - Video     |     (Dynamic based on selected screen)            │
│  - Accounts  |                                                    │
│  - Twitter   |                                                    │
│  - AFM       |                                                    │
│  - Outreach  |                                                    │
│  - Settings  |                                                    │
│            ├────────────────────────────────────────────────────┤
│            │  FOOTER: Pipeline Status / Progress               │
└────────────┴────────────────────────────────────────────────────┘
```

### 2.2 Component Hierarchy

```
App (Textual)
├── Sidebar (Navigation)
├── Screen Stack
│   ├── DashboardScreen
│   ├── VideoGenScreen
│   ├── AccountsScreen
│   ├── TwitterScreen
│   ├── AFMScreen
│   ├── OutreachScreen
│   └── SettingsScreen
└── Global Widgets
    ├── Toast (notifications)
    ├── ConfirmDialog (modals)
    └── LogViewer (footer)
```

### 2.3 Event System

```python
# Pipeline Events (publish-subscribe)
PipelineEvent
├── TopicStarted
├── TopicComplete
├── ScriptStarted
├── ScriptComplete
├── ImagesStarted
├── ImageComplete (x8)
├── TTSStarted
├── TTSComplete
├── CombineStarted
├── VideoComplete
├── UploadStarted
└── UploadComplete
```

### 2.4 Async Pipeline Wrapper

```python
class PipelineWrapper:
    """Wraps existing YouTube class with async + events."""
    
    def __init__(self, app: App, account: str):
        self.app = app
        self.account = account
        self.youtube = None  # Lazy init
    
    async def generate(self, niche: str, language: str) -> dict:
        # Run sync pipeline in thread pool
        return await asyncio.to_thread(self._run_sync, niche, language)
    
    def _run_sync(self, niche: str, language: str) -> dict:
        # Initialize YouTube lazy
        self.youtube = YouTube(self.account)
        
        # Add progress callback to YouTube
        self.youtube.set_progress_callback(self._on_progress)
        
        # Run pipeline
        return self.youtube.generate_video(niche, language)
    
    def _on_progress(self, step: str, message: str, progress: float):
        # Emit to TUI
        self.app.post_message(PipelineUpdate(step, message, progress))
```

---

## 3. Screen Designs

### 3.1 Dashboard Screen

```
┌─────────────────────────────────────────────────────┐
│  DASHBOARD                              [Refresh]  │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  ┌──────────────┐ ┌──────────────┐ ┌────────────┐  │
│  │ Videos Today │ │  This Week   │ │  Accounts  │  │
│  │      12      │ │      47      │ │      3     │  │
│  └──────────────┘ └──────────────┘ └────────────┘  │
│                                                     │
│  Recent Activity                                    │
│  ┌──────────────────────────────────────────────┐  │
│  │ ✅ Video uploaded - "The Bloop Mystery"     │  │
│  │ ✅ Video generated - output/video_007.mp4  │  │
│  │ ⏳ Generating - "Ocean Sounds"               │  │
│  │ ❌ Upload failed - "Secret Metro-2"         │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Quick Actions                                     │
│  [🎬 Generate Video]  [📤 Upload Latest]  [⚙️Settings]│
└─────────────────────────────────────────────────────┘
```

### 3.2 Video Generation Screen (PRIORITY)

```
┌─────────────────────────────────────────────────────┐
│  VIDEO GENERATION                     [⏹ Stop]    │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  Account:  [YouTube v]                              │
│  Niche:    [________________________________]       │
│  Language: [English v]                              │
│  For Kids: [ ] Yes                                 │
│                       [▶ GENERATE]                  │
│                                                     │
│  ─────────────────────────────────────────────────  │
│  Progress: ████████████░░░░░░░ 60%                  │
│  Status:   Generating images (3/8)                  │
│                                                     │
│  ┌──────────────────────────────────────────────┐  │
│  │ Step              │ Status      │ Time       │  │
│  │ ─────────────────────────────────────────── │  │
│  │ 1. Topic          │ ✓ Complete  │ 2.3s      │  │
│  │ 2. Script         │ ✓ Complete  │ 4.1s      │  │
│  │ 3. Image Prompts │ ✓ Complete  │ 1.2s      │  │
│  │ 4. Images        │ ████░░░░ 3/8 │ 12.4s     │  │
│  │ 5. TTS           │ ○ Pending    │ -         │  │
│  │ 6. Combine       │ ○ Pending    │ -         │  │
│  │ 7. Upload        │ ○ Pending    │ -         │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Output                                             │
│  Path: /home/.../output/video_047.mp4              │
│  Size: 24.3 MB                                     │
│                              [▶ Play] [📤 Upload]   │
│                                                     │
│  Live Log                                          │
│  ┌──────────────────────────────────────────────┐  │
│  │ 🔍 Searching Tavily...                       │  │
│  │ ✅ Found 8 topics                            │  │
│  │ 🤖 Generating script...                     │  │
│  │ 🖼️ Generating image 3/8: "underwater scene"  │  │
│  │ ✅ Image saved: .mp/img_003.png             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 3.3 Accounts Screen

```
┌─────────────────────────────────────────────────────┐
│  ACCOUNTS                        [+ Add] [⟳ Sync]   │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  Platform Filter: [All v]  Search: [__________]     │
│                                                     │
│  ┌────────────────────────────────────────────────┐  │
│  │ Platform │ Username    │ Status  │ Last Used  │  │
│  │ ─────────────────────────────────────────────│  │
│  │ YouTube  │ @channel123 │ ✅ Active│ 2 min ago  │  │
│  │ TikTok   │ @username   │ ⚠️ Exp. │ 1 hour ago │  │
│  │ Twitter  │ @bot_account│ ❌ Error│ 3 days ago  │  │
│  │ Facebook │ @page_name  │ ✅ Active│ 5 min ago  │  │
│  └────────────────────────────────────────────────┘  │
│                                                     │
│  Account Details (selected: YouTube)               │
│  ┌──────────────────────────────────────────────┐  │
│  │ Profile: /path/to/firefox/profile             │  │
│  │ Uploaded: 47 videos                           │  │
│  │ Daily Limit: 3/3 used                         │  │
│  │ [Edit] [Test Connection] [Delete]             │  │
│  └──────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

### 3.4 Settings Screen

```
┌─────────────────────────────────────────────────────┐
│  SETTINGS                                           │
│  ─────────────────────────────────────────────────  │
│                                                     │
│  API Keys                                           │
│  ┌──────────────────────────────────────────────┐  │
│  │ CLIPROXY_API_KEY    │ •••••••••••••••• [👁] │  │
│  │ TAVILY_API_KEY      │ •••••••••••••••• [👁] │  │
│  │ EXA_API_KEY         │ •••••••••••••••• [👁] │  │
│  │ POLLINATIONS_KEY    │ •••••••••••••••• [👁] │  │
│  │ PIXABAY_API_KEY     │ •••••••••••••••• [👁] │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Defaults                                           │
│  ┌──────────────────────────────────────────────┐  │
│  │ TTS Voice:    [en-US-JennyNeural v]          │  │
│  │ Language:     [English v]                    │  │
│  │ Sentence Len: [4 v]                          │  │
│  │ Headless:     [✓] Yes                        │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│  Browser                                            │
│  ┌──────────────────────────────────────────────┐  │
│  │ Firefox Profile: [/path/to/profile    ][…]  │  │
│  │ ImageMagick:    [/usr/bin/convert     ][…]  │  │
│  └──────────────────────────────────────────────┘  │
│                                                     │
│                       [💾 Save]  [↩️ Reset]         │
└─────────────────────────────────────────────────────┘
```

---

## 4. Implementation Steps

### Phase 1: Foundation (Days 1-2)

#### Step 1.1: Setup Textual Project
```
1. Add to requirements.txt: textual>=0.90.0
2. Create src/tui/ directory structure
3. Create basic app.py with sidebar navigation
4. Create dark.tcss theme file
5. Verify: python -m src.tui runs without errors
```

#### Step 1.2: Create Base Screens
```
1. Create Screen base class with common layout
2. Implement Sidebar widget with navigation
3. Create DashboardScreen (placeholder)
4. Create SettingsScreen (placeholder)
5. Verify: Can navigate between screens
```

#### Step 1.3: Dark Theme Implementation
```css
/* dark.tcss */
Screen {
    background: #0f172a;
    color: #f8fafc;
}

Sidebar {
    background: #1e293b;
    width: 25;
}

Button {
    background: #6366f1;
    color: white;
}

Button:hover {
    background: #818cf8;
}

Input {
    background: #334155;
    color: #f8fafc;
}

DataTable {
    background: #1e293b;
}

DataTable > .datatable--cursor {
    background: #6366f1;
}
```

### Phase 2: Video Generation Screen (Days 3-5)

#### Step 2.1: Progress Widget
```
1. Create ProgressStep widget (pending/current/complete states)
2. Create PipelineProgress composite widget
3. Add step icons (✓, ○, █)
4. Add elapsed time tracking per step
```

#### Step 2.2: Log Viewer Widget
```
1. Create LogViewer widget extending RichLog
2. Add log level filtering (INFO/WARN/ERROR)
3. Add search/filter functionality
4. Add auto-scroll toggle
5. Add clear/export buttons
```

#### Step 2.3: Pipeline Wrapper
```
1. Create src/tui/wrappers/pipeline.py
2. Implement lazy browser initialization
3. Add progress callback to YouTube class
4. Wrap sync operations with asyncio.to_thread()
5. Add proper cleanup on cancel/interrupt
```

#### Step 2.4: Connect Video Gen Screen
```
1. Create form inputs (account, niche, language, for_kids)
2. Connect Generate button to PipelineWrapper
3. Wire progress updates to UI widgets
4. Add Stop/Cancel functionality
5. Add output preview (file path display)
```

### Phase 3: Accounts Screen (Days 6-7)

#### Step 3.1: Account Table Widget
```
1. Create AccountTable widget using DataTable
2. Add columns: Platform, Username, Status, Last Used
3. Add row selection for detail view
4. Add sorting by column
5. Add platform filter dropdown
```

#### Step 3.2: Account Form
```
1. Create AddAccountScreen (modal)
2. Form fields: Platform, Username, Profile Path
3. Add validation (profile exists, etc.)
4. Add Test Connection button
5. Connect to db.py for persistence
```

#### Step 3.3: Account Actions
```
1. Add Edit button → pre-fill form
2. Add Delete with confirmation dialog
3. Add Sync button → refresh status
4. Add Test Connection → verify browser works
```

### Phase 4: Remaining Screens (Days 8-10)

#### Step 4.1: Twitter Screen
```
1. Post composer (text area + character count)
2. Schedule viewer (list of scheduled tweets)
3. Recent tweets table
4. Analytics (followers, engagement)
```

#### Step 4.2: AFM Screen
```
1. Product list with affiliate links
2. Pitch generator form
3. Campaign manager
4. Performance stats
```

#### Step 4.3: Outreach Screen
```
1. Business search form (niche, location)
2. Campaign list
3. Email template editor
4. Send tracking
```

### Phase 5: Integration & Polish (Days 11-12)

#### Step 5.1: Keyboard Shortcuts
```
- Tab/Shift+Tab: Navigate inputs
- Enter: Submit forms, activate buttons
- Escape: Close modals, go back
- g+d: Go to Dashboard
- g+v: Go to Video Generation
- g+s: Go to Settings
- Ctrl+C: Stop current pipeline
```

#### Step 5.2: Error Handling
```
1. Catch all exceptions in pipeline wrapper
2. Display errors in LogViewer (red text)
3. Show toast notification on error
4. Add retry button for recoverable errors
5. Add "View Error Details" for stack traces
```

#### Step 5.3: Final Integration
```
1. Replace main.py entry point to launch TUI
2. Remove old CLI (or keep as --legacy flag)
3. Add --help showing new commands
4. Verify all screens work end-to-end
```

---

## 5. File Organization

### 5.1 New TUI Structure

```
src/
├── tui/                          # NEW: TUI application
│   ├── __init__.py               # Package init
│   ├── app.py                    # Main Textual App
│   ├── screens/
│   │   ├── __init__.py
│   │   ├── dashboard.py          # Dashboard home
│   │   ├── video_gen.py          # Video generation (PRIORITY)
│   │   ├── accounts.py           # Account management
│   │   ├── twitter.py            # Twitter bot
│   │   ├── afm.py                # Affiliate marketing
│   │   ├── outreach.py           # Business outreach
│   │   └── settings.py           # Configuration
│   ├── widgets/
│   │   ├── __init__.py
│   │   ├── sidebar.py            # Navigation sidebar
│   │   ├── progress.py          # Pipeline progress widgets
│   │   ├── log_viewer.py         # Real-time log display
│   │   ├── stat_card.py         # Dashboard stat cards
│   │   ├── account_form.py      # Account add/edit form
│   │   └── confirm_dialog.py    # Reusable confirm modal
│   ├── styles/
│   │   ├── __init__.py
│   │   └── dark.tcss            # Dark theme
│   ├── wrappers/
│   │   ├── __init__.py
│   │   ├── pipeline.py          # Async pipeline wrapper
│   │   └── youtube.py           # TUI-friendly YouTube wrapper
│   └── events.py                # Custom Textual events
│
├── main.py                       # MODIFIED: Launch TUI
├── run_pipeline.py              # REFACTOR: Importable module
├── run_24_7.py                  # REFACTOR: Importable module
├── batch_run.py                 # REFACTOR: Importable module
│
├── classes/                     # EXISTING: Keep as-is
│   ├── YouTube.py               # MODIFIED: Add progress callback
│   └── ...
│
├── config.py                    # EXISTING
├── db.py                        # EXISTING
├── llm_generate.py              # EXISTING
├── llm_provider.py              # EXISTING
├── research.py                  # EXISTING
├── status.py                    # MODIFIED: TUI-aware logging
└── utils.py                     # EXISTING
```

### 5.2 Entry Point Changes

```python
# src/main.py (new)
import sys
from tui.app import MoneyPrinterApp

def main():
    if "--legacy" in sys.argv:
        # Old CLI behavior
        import main_legacy
        main_legacy.run()
    else:
        # New TUI
        app = MoneyPrinterApp()
        app.run()

if __name__ == "__main__":
    main()
```

---

## 6. Migration Strategy

### 6.1 Phased Rollout

| Phase | Description | Timeline |
|-------|-------------|----------|
| Alpha | TUI runs parallel to CLI, internal testing | Day 1-7 |
| Beta | TUI default, CLI available via `--legacy` | Day 8-10 |
| Release | CLI removed, TUI only | Day 11+ |

### 6.2 Code Sharing Pattern

```python
# TUI imports existing code unchanged
from classes.YouTube import YouTube
from run_pipeline import run_pipeline
from config import get_firefox_profile_path

# Wrapper adds TUI awareness
from tui.wrappers.pipeline import PipelineWrapper
```

### 6.3 Status Call Migration

**Before (YouTube.py):**
```python
status.print_step("Generating topic...")
topic = self.generate_topic()
status.success(f"Generated: {topic}")
```

**After (YouTube.py with callback):**
```python
def generate_topic(self, progress_callback=None):
    if progress_callback:
        progress_callback("topic", "started", 0)
    
    topic = self._do_generate_topic()
    
    if progress_callback:
        progress_callback("topic", "complete", 100, {"topic": topic})
    
    return topic
```

---

## 7. Risk Mitigation

### 7.1 Identified Risks

| Risk | Impact | Mitigation |
|------|--------|-------------|
| Selenium blocks event loop | TUI freezes | `asyncio.to_thread()`, lazy init |
| Browser not closing on exit | Zombie Firefox | `atexit.register(browser.quit)` |
| 251 status calls in YouTube | Hard to track | Callback protocol, map to widgets |
| Image generation slow | User sees frozen UI | Per-image progress, cancel button |
| Headless in terminal | Display issues | Force `--headless` in TUI mode |
| Memory leaks | OOM over time | Proper cleanup between runs |
| No graceful error recovery | Stuck on crash | Retry/reset buttons |

### 7.2 Browser Lifecycle

```python
# src/tui/wrappers/youtube.py
import atexit
from selenium import webdriver

class YouTubeWrapper:
    _browser = None
    
    @property
    def browser(self):
        if self._browser is None:
            options = webdriver.FirefoxOptions()
            options.add_argument("--headless")
            self._browser = webdriver.Firefox(options=options)
            atexit.register(self._cleanup)
        return self._browser
    
    def _cleanup(self):
        if self._browser:
            self._browser.quit()
            self._browser = None
```

### 7.3 Async Pipeline Pattern

```python
# src/tui/wrappers/pipeline.py
import asyncio

class PipelineWrapper:
    async def generate(self, niche: str, language: str):
        def _run():
            youtube = YouTube(account)
            youtube.set_progress_callback(self._on_progress)
            return youtube.generate_video(niche, language)
        
        return await asyncio.to_thread(_run)
```

---

## 8. Testing Plan

### 8.1 Unit Tests

| Component | Test Coverage |
|-----------|---------------|
| PipelineWrapper | Async execution, callback firing, cancel |
| Progress widgets | State transitions (pending→active→complete) |
| LogViewer | Filtering, search, export |
| AccountForm | Validation, save/load |

### 8.2 Integration Tests

```
1. Launch TUI → Dashboard loads
2. Navigate: Dashboard → Video → Accounts → Settings
3. Generate video: Complete pipeline with progress
4. Add account: Form submit → database → table refresh
5. Stop pipeline: Cancel mid-run, cleanup browser
6. Exit TUI: Browser quits, no zombie processes
```

### 8.3 Manual Checkpoints

- [ ] Dark theme renders correctly in various terminal sizes
- [ ] Progress updates in real-time during video generation
- [ ] Log viewer shows all status messages with correct colors
- [ ] Sidebar navigation works with keyboard (Tab, Enter)
- [ ] Account form validates profile path exists
- [ ] Settings save to config.json correctly
- [ ] Ctrl+C stops pipeline and cleans up browser

---

## 9. Dependencies

### 9.1 New Dependencies

```text
# requirements.txt additions
textual>=0.90.0
```

### 9.2 Existing Dependencies (required)

```text
selenium>=4.0
webdriver-manager
MoviePy
faster-whisper
edge-tts
pillow
requests
```

---

## 10. Success Criteria

### 10.1 Functional Requirements

- [ ] TUI launches with sidebar navigation
- [ ] Video generation screen shows real-time progress
- [ ] All 7 steps tracked with status + timing
- [ ] Log viewer displays all pipeline output
- [ ] Account management (CRUD) works
- [ ] Settings save/load correctly
- [ ] Browser cleanup on exit

### 10.2 Performance Requirements

- [ ] TUI responds < 100ms to navigation
- [ ] Progress updates display within 500ms of event
- [ ] No UI freeze during LLM calls (async)
- [ ] Memory stable across multiple video generations

### 10.3 User Experience

- [ ] Dark theme consistent across all screens
- [ ] Keyboard navigation works throughout
- [ ] Error states show clear messages + recovery options
- [ ] Exit cleanup prevents zombie processes

---

## Appendix A: CSS Color Reference

| Element | Dark Mode Hex |
|---------|---------------|
| Background | #0f172a |
| Sidebar | #1e293b |
| Card | #1e293b |
| Input | #334155 |
| Primary Action | #6366f1 |
| Primary Hover | #818cf8 |
| Text Primary | #f8fafc |
| Text Secondary | #94a3b8 |
| Success | #22c55e |
| Warning | #f59e0b |
| Error | #ef4444 |
| Border | #475569 |

---

## Appendix B: Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `g d` | Go to Dashboard |
| `g v` | Go to Video Generation |
| `g a` | Go to Accounts |
| `g t` | Go to Twitter |
| `g f` | Go to AFM |
| `g o` | Go to Outreach |
| `g s` | Go to Settings |
| `Ctrl+C` | Stop pipeline |
| `Escape` | Close modal / Go back |
| `Tab` | Next input |
| `Shift+Tab` | Previous input |
| `Enter` | Submit / Activate |

---

## Appendix C: Progress Step Icons

| State | Icon | Description |
|-------|------|-------------|
| Pending | `○` | Not started, gray |
| Started | `◐` | In progress, pulsing |
| Complete | `✓` | Done, green |
| Error | `✗` | Failed, red |

---

*Document Version: 1.0*  
*Created: 2026-04-11*  
*Framework: Textual*  
*Target: Python 3.12+*