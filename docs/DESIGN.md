# MoneyPrinterV2 TUI Design System

## Inspired by: Flexoki (stephango.com/flexoki)

An inky color scheme for terminal - minimal, high-contrast, warm. Dark theme with proper Flexoki semantics.

---

## 1. Visual Theme & Atmosphere

**Mood**: Minimal, high-contrast, inky
**Density**: Clean but information-rich
**Philosophy**: "Content is king" - colors calibrated for legibility

---

## 2. Color Palette (Flexoki Dark Mode)

### Core Backgrounds
| Role | Color | Hex | Usage |
|------|-------|-----|------|
| Background | Black | `#100F0F` | Main app background |
| Background 2 | Base 950 | `#1C1B1A` | Cards, modals |
| UI | Base 900 | `#282726` | Borders, dividers |
| UI Hover | Base 850 | `#343331` | Hover states |
| UI Active | Base 800 | `#403E3C` | Active/focus |

### Text (Dark Theme)
| Role | Color | Hex | Usage |
|------|-------|-----|------|
| Text Primary | White | `#FFFFFF` | Main text |
| Text Muted | Base 600 | `#6F6E69` | Labels, secondary |
| Text Faint | Base 700 | `#575653` | Hints, placeholders |

### Accents (Dark Theme - Use 400 values)
| Role | Color | Hex | Usage |
|------|-------|-----|------|
| Primary | Cyan 400 | `#3AA99F` | Buttons, links, focus |
| Success | Green 400 | `#879A39` | Complete, success |
| Warning | Orange 400 | `#DA702C` | In progress, pending |
| Error | Red 400 | `#D14D41` | Errors, failed |
| Accent | Blue 400 | `#4385BE` | Variables, secondary |

---

## 3. Typography

### Font Family
- **Primary**: System monospace (`"SF Mono", "Menlo", "Monaco", monospace`)
- **Fallback**: System UI font for labels

### Type Scale
| Element | Size | Weight | Color |
|---------|------|--------|-------|
| Screen Title | 16px | 600 | `#3AA99F` |
| Section Header | 13px | 500 | `#6F6E69` |
| Body Text | 13px | 400 | `#FFFFFF` |
| Label | 12px | 500 | `#6F6E69` |
| Hint | 12px | 400 | `#575653` |

---

## 4. Component Styling

### Buttons (Primary)
```css
background: #3AA99F;      /* cyan-400 */
color: #100F0F;
border: none;
padding: 6px 12px;
border-radius: 2px;
```

### Secondary Buttons (Sidebar)
```css
background: transparent;
color: #6F6E69;
border: none;
```

### Input Fields
```css
background: #343331;       /* ui-2 */
border: 1px solid #403E3C; /* ui-3 */
color: #FFFFFF;
padding: 8px 12px;
```

### Focus State
```css
border-color: #3AA99F;     /* cyan */
```

### Cards (Stat Cards)
```css
background: #282726;       /* ui */
border: 1px solid #343331;  /* ui-2 */
border-radius: 4px;
```

### Sidebar
```css
background: #100F0F;
width: 180px;
border-right: 1px solid #282726;
```

### Progress Steps
```css
.step-pending   { color: #6F6E69; }  /* tx-2 */
.step-active    { color: #DA702C; }  /* orange-400 */
.step-complete  { color: #879A39; }  /* green-400 */
.step-error    { color: #D14D41; }  /* red-400 */
```

---

## 5. Layout Principles

### Spacing Scale
- `xs`: 4px
- `sm`: 8px  
- `md`: 16px
- `lg`: 24px

### Screen Layout
```
┌─────────────────────────────────┐
│ Header                          │
├──────────┬──────────────────────┤
│ Sidebar  │ Content              │
│ 180px   │ padding: 16px        │
│          │                      │
├──────────┴──────────────────────┤
│ Footer                          │
└─────────────────────────────────┘
```

---

## 6. Do's and Don'ts

### Do
- Use cyan (#3AA99F) for primary actions
- Use green (#879A39) for success states
- Use orange (#DA702C) for in-progress
- Use red (#D14D41) for errors
- Keep design minimal, no gradients

### Don't
- Use purple (Flexoki is cyan-based)
- Use bright saturated colors
- Add unnecessary shadows
- Use rounded corners > 4px

---

## 7. UI Components

### Screens
1. Dashboard - Stat cards, activity list
2. Video Gen - Form, progress, log viewer
3. Accounts - Table, filter, actions
4. Twitter - Composer, tables
5. AFM - Products, pitch generator
6. Outreach - Search, campaigns
7. Settings - Read-only config

### Widgets
- StatCard, PipelineProgress, LogViewer
- AccountTable, ConfirmDialog

---

## 8. Quick Reference

```
Background: #100F0F
Surface:    #1C1B1A
Border:    #282726
Primary:   #3AA99F (cyan)
Success:   #879A39 (green)
Warning:   #DA702C (orange)
Error:     #D14D41 (red)
Text:      #FFFFFF / #6F6E69 / #575653
```

---

*Document Version: 1.1*
*Updated: 2026-04-11*
*Inspired by: Flexoki (stephango.com/flexoki)*