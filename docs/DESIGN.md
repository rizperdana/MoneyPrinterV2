# MoneyPrinterV2 TUI Design System

## Inspired by: Linear + TOAD + VoltAgent

Ultra-minimal terminal interface with purple accent, terminal-native feel. Clean, precise, keyboard-first.

---

## 1. Visual Theme & Atmosphere

**Mood**: Professional, minimal, terminal-native
**Density**: High information density but with generous whitespace
**Philosophy**: "Content is king" - UI fades to let data shine

---

## 2. Color Palette

### Core Colors
| Role | Color | Hex | Usage |
|------|-------|-----|------|
| Background | Deep Black | `#0D0D0D` | Main app background |
| Surface | Charcoal | `#1A1A1A` | Cards, sidebar |
| Surface Elevated | Dark Gray | `#262626` | Hover states, inputs |
| Border | Subtle Gray | `#333333` | Dividers, outlines |

### Accent Colors
| Role | Color | Hex | Usage |
|------|-------|-----|------|
| Primary | Electric Purple | `#5E6AD2` | Buttons, links, focus |
| Primary Hover | Light Purple | `#7B83EB` | Hover states |
| Success | Emerald | `#10B981` | Completed steps, success |
| Warning | Amber | `#F59E0B` | In progress, warnings |
| Error | Rose | `#EF4444` | Errors, failures |

### Text Colors
| Role | Color | Hex | Usage |
|------|-------|-----|------|
| Text Primary | White | `#FFFFFF` | Headings, important |
| Text Secondary | Gray | `#A1A1AA` | Labels, descriptions |
| Text Muted | Dark Gray | `#71717A` | Placeholders, hints |

---

## 3. Typography

### Font Family
- **Primary**: System monospace (`"SF Mono", "Menlo", "Monaco", monospace`)
- **Fallback**: System UI font for labels

### Type Scale
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Screen Title | 18px | 600 | `#FFFFFF` |
| Section Header | 14px | 600 | `#A1A1AA` |
| Body Text | 13px | 400 | `#FFFFFF` |
| Label | 12px | 500 | `#A1A1AA` |
| Hint/Placeholder | 12px | 400 | `#71717A` |
| Keyboard Shortcut | 11px | 500 | `#5E6AD2` |

---

## 4. Component Styling

### Buttons
```css
/* Primary Button */
background: #5E6AD2;
color: white;
border-radius: 4px;
padding: 6px 12px;
font-size: 12px;
font-weight: 500;

/* Primary Hover */
background: #7B83EB;

/* Secondary/Ghost Button */
background: transparent;
color: #A1A1AA;
border: 1px solid #333333;

/* Error Button */
background: #EF4444;
color: white;
```

### Input Fields
```css
background: #1A1A1A;
border: 1px solid #333333;
border-radius: 4px;
padding: 8px 12px;
color: #FFFFFF;
font-size: 13px;

/* Focus State */
border-color: #5E6AD2;
box-shadow: 0 0 0 2px rgba(94, 106, 210, 0.2);
```

### Cards (Stat Cards, Account Details)
```css
background: #1A1A1A;
border: 1px solid #262626;
border-radius: 6px;
padding: 16px;
```

### Sidebar Navigation
```css
background: #0D0D0D;
width: 180px;
border-right: 1px solid #1A1A1A;

.nav-item {
    padding: 8px 12px;
    color: #71717A;
    font-size: 12px;
}

.nav-item:hover {
    background: #1A1A1A;
    color: #A1A1AA;
}

.nav-item.active {
    color: #FFFFFF;
    background: #1A1A1A;
    border-left: 2px solid #5E6AD2;
}
```

### Data Tables
```css
background: transparent;
border-collapse: collapse;

th {
    color: #71717A;
    font-size: 11px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    padding: 8px 12px;
    border-bottom: 1px solid #262626;
}

td {
    color: #FFFFFF;
    font-size: 13px;
    padding: 10px 12px;
    border-bottom: 1px solid #1A1A1A;
}

tr:hover {
    background: #1A1A1A;
}
```

### Progress Steps
```css
.step-pending { color: #71717A; }
.step-active { color: #F59E0B; }
.step-complete { color: #10B981; }
.step-error { color: #EF4444; }
```

---

## 5. Layout Principles

### Spacing Scale (4px baseline)
- `xs`: 4px
- `sm`: 8px
- `md`: 16px
- `lg`: 24px
- `xl`: 32px

### Screen Layout
```
┌────────────────────────────────────────────┐
│ Header (auto height)                       │
├──────────┬───────────────────────────────┤
│ Sidebar  │ Content Area                │
│ 180px   │ padding: 16px              │
│          │                            │
│          │ Section                   │
│          │ height: auto               │
│          │                            │
│          │ Section                   │
│          │ height: auto               │
├──────────┴───────────────────────────────┤
│ Footer (auto height)                       │
└────────────────────────────────────────────┘
```

### Grid Specifications
- Max content width: 800px (centered in content area)
- Sidebar: fixed 180px
- Responsive: Stack sidebar on width < 768px

---

## 6. Depth & Elevation

### Shadows (minimal use - terminal aesthetic)
```css
/* Subtle lift on hover */
box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);

/* Modal/Dialog */
box-shadow: 0 4px 24px rgba(0, 0, 0, 0.5);
```

### Surface Hierarchy
1. **Base**: `#0D0D0D` - Main background
2. **Raised**: `#1A1A1A` - Cards, sidebar
3. **Hover**: `#262626` - Interactive elements
4. **Focus**: `#5E6AD2` - Focus ring

---

## 7. Do's and Don'ts

### Do
- Use monospace fonts for data/values
- Keep keyboard shortcuts visible in footer
- Use purple (#5E6AD2) for primary actions
- Show clear progress states (pending/active/complete/error)
- Support keyboard navigation (g+d, g+v, etc.)

### Don't
- Use gradients (keep it flat/clean)
- Use rounded corners > 6px
- Use bright/dense colors
- Show unnecessary animations
- Use shadows unless necessary

---

## 8. Responsive Behavior

### Breakpoints
- **Desktop**: > 1024px (full sidebar)
- **Tablet**: 768px - 1024px (collapsible sidebar)
- **Mobile**: < 768px (bottom nav)

### Touch Targets
- Minimum: 44px height
- Spacing between: 8px

---

## 9. UI Components Reference

### Screens
1. **Dashboard**: Stat cards (3), Recent activity list, Quick actions
2. **Video Gen**: Form inputs (4), Progress widget, Log viewer, Output section
3. **Accounts**: Table, Filter, Add/Edit modal, Actions
4. **Twitter**: Composer, Scheduled, Recent tables
5. **AFM**: Products table, Pitch generator, Campaigns
6. **Outreach**: Search form, Campaigns, Template editor
7. **Settings**: Read-only config display, Reload button

### Widgets
- `StatCard`: Title, value, optional icon
- `PipelineProgress`: Step list with states
- `LogViewer`: Filterable log output
- `AccountTable`: Sortable, filterable table
- `ConfirmDialog`: Yes/No modal

### Icons (emoji-based for simplicity)
- 📊 Dashboard
- 🎬 Video
- 👤 Accounts
- 🐦 Twitter
- 💰 AFM
- 📧 Outreach
- ⚙️ Settings
- ✓ Complete (green)
- ○ Pending (gray)
- ◐ Active (amber)
- ✗ Error (red)

---

## 10. Agent Prompt Guide

### Quick Reference
```
Background: #0D0D0D
Surface: #1A1A1A
Primary: #5E6AD2
Success: #10B981
Warning: #F59E0B
Error: #EF4444
Text: #FFFFFF / #A1A1AA / #71717A
```

### Build Command
"Create a screen that matches MoneyPrinterV2 DESIGN.md - use monospace fonts, purple (#5E6AD2) for primary actions, dark (#0D0D0D) background."

---

*Document Version: 1.0*
*Created: 2026-04-11*
*Inspired by: Linear, TOAD, VoltAgent*