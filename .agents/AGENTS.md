# SSMS — Enterprise UI/UX Design System

## 0. Design North Star

The Student & Staff Management System (SSMS) is an institutional enterprise application for academic and administrative operations.

The interface must feel:

* Professional
* Institutional
* Fast
* Trustworthy
* Information-dense
* Consistent
* Modern without being trendy
* Polished without being decorative
* Responsive
* Accessible

SSMS should look like software that a university could operate every day—not a portfolio project, startup landing page, AI-generated dashboard, or Dribbble concept.

### Guiding principle

> **Functional sophistication, not visual decoration.**

Every visual decision must support at least one of:

* Usability
* Hierarchy
* Navigation
* Feedback
* Accessibility
* Brand identity
* Information comprehension

If a visual treatment does not serve a purpose, do not add it.

---

# 1. Product Priorities

The implementation priority is:

1. **Mobile usability**
2. **Performance**
3. **Accessibility**
4. **Information clarity**
5. **Desktop productivity**
6. **Visual polish**
7. **Decorative enhancement**

SSMS is primarily an operational system. Users should be able to complete tasks quickly and reliably, especially on mobile devices.

### Critical rule

> **Do not design desktop first and merely shrink it for mobile.**

Mobile is a first-class experience.

Every major feature must have an intentional mobile layout.

---

# 2. Anti-Slop Design Rules

SSMS must actively avoid generic AI-generated UI patterns.

### Never introduce by default

* Neon effects
* Glowing cards
* Glassmorphism
* Frosted glass
* Decorative blobs
* Abstract background shapes
* Rainbow gradients
* Gradient text
* Excessive blur
* Giant hero sections
* Huge typography
* Excessive rounded containers
* 20–32px "blob" cards
* Excessive pill-shaped components
* Floating UI without purpose
* Decorative emoji
* Random illustrations
* Fake statistics
* Fake charts
* Excessive shadows
* Continuous animations
* Bouncing UI
* Shimmer effects everywhere
* Excessive hover transformations
* Excessive icon circles
* Decorative separators
* Unnecessary glass panels
* Excessive empty space
* "AI dashboard" metric-card grids

### Do not make every section a card

Create hierarchy using:

* Typography
* Spacing
* Borders
* Background surfaces
* Tables
* Tabs
* Lists
* Dividers
* Section headers

Cards exist to group related information—not because cards are visually attractive.

---

# 3. Modernization Rule

Modern does not mean:

```text
gradient + blur + huge radius + floating card + glow
```

Modern SSMS means:

```text
excellent spacing
+ crisp typography
+ strong hierarchy
+ responsive layouts
+ subtle motion
+ excellent states
+ precise vector icons
+ clean data visualization
+ thoughtful interactions
+ fast performance
```

The interface should feel:

> **Quietly premium.**

Premium comes from precision, not decoration.

---

# 4. Brand Identity

## Primary Brand

```css
--primary: #5a7d7c;
--primary-hover: #4a6b69;
--primary-active: #405e5c;
```

Sage Teal is the primary interactive brand color.

Use it for:

* Primary actions
* Active navigation
* Active tabs
* Selected states
* Links
* Focus indicators
* Important UI accents
* Progress indicators where appropriate

Do not use teal on every element.

## Institutional Gold

```css
--gold: #c5a059;
```

Gold is an accent, not a second primary color.

Use sparingly for:

* Institutional identity
* Special highlights
* Important ceremonial elements
* Selected institutional metadata
* Subtle premium accents

Never create gold gradients.

---

# 5. Color Architecture

## Light Mode

```css
--bg-body: #f8fafc;
--surface: #ffffff;
--surface-subtle: #f8fafc;
--surface-hover: #f1f5f9;

--border: #e2e8f0;
--border-strong: #cbd5e1;

--text-main: #0f172a;
--text-primary: #1e293b;
--text-secondary: #475569;
--text-muted: #64748b;
```

---

# 6. Obsidian Dark Mode

Dark mode is not a light theme with inverted colors.

It is a purpose-built theme optimized for:

* Long administrative sessions
* Low-light environments
* High information density
* Tables
* Forms
* CRUD operations
* Dashboards
* Documents
* Charts
* Reduced visual fatigue
* Accessibility

The dark interface should feel:

> **Deep, calm, precise, structured, professional.**

It must not feel:

* Cyberpunk
* Gaming-oriented
* Neon
* Glowing
* Glassy
* Futuristic for the sake of appearance

## Core dark palette

Never use pure black as the application background.

```css
--bg-body: #0b0f19;

--surface-0: #0b0f19;
--surface-1: #111827;
--surface-2: #172033;
--surface-3: #1f2937;

--surface-hover: #202b3d;
--surface-active: #263447;
```

### Surface meaning

```text
surface-0
Application background

surface-1
Cards / panels / sidebar

surface-2
Elevated controls / inputs / nested sections

surface-3
Dropdowns / popovers / high-elevation UI

surface-hover
Hover state

surface-active
Selected / pressed state
```

Do not use one dark color for everything.

Hierarchy must come from:

```text
surface value
+ border
+ spacing
```

not from:

```text
glow
+ blur
+ huge shadow
+ glass
```

---

# 7. Canonical Dark Theme Tokens

Components must use semantic tokens rather than hard-coded colors.

```css
.dark-theme {

  /* Backgrounds */
  --bg-body: #0b0f19;
  --bg-sidebar: #0f1520;
  --bg-topbar: #0f1520;

  --surface: #111827;
  --surface-subtle: #151d2b;
  --surface-elevated: #172033;
  --surface-hover: #1f2937;
  --surface-active: #263447;

  /* Borders */
  --border: #263244;
  --border-subtle: #1f2937;
  --border-strong: #334155;
  --border-focus: #5a7d7c;

  /* Text */
  --text-main: #f8fafc;
  --text-primary: #e2e8f0;
  --text-secondary: #cbd5e1;
  --text-tertiary: #94a3b8;
  --text-muted: #7f8ea3;
  --text-disabled: #64748b;
  --text-placeholder: #718096;

  /* Brand */
  --primary: #6f9290;
  --primary-hover: #7da19f;
  --primary-active: #587b79;
  --primary-dark: #4a6b69;

  --primary-surface: rgba(90, 125, 124, 0.14);
  --primary-surface-hover: rgba(90, 125, 124, 0.20);
  --primary-border: rgba(111, 146, 144, 0.45);

  /* Gold */
  --gold: #d0ad68;
  --gold-muted: #a98b52;
  --gold-surface: rgba(197, 160, 89, 0.12);

  /* Semantic */
  --success: #34d399;
  --success-text: #6ee7b7;
  --success-surface: rgba(52, 211, 153, 0.12);
  --success-border: rgba(52, 211, 153, 0.28);

  --warning: #fbbf24;
  --warning-text: #fcd34d;
  --warning-surface: rgba(251, 191, 36, 0.12);
  --warning-border: rgba(251, 191, 36, 0.28);

  --danger: #f87171;
  --danger-text: #fca5a5;
  --danger-surface: rgba(248, 113, 113, 0.12);
  --danger-border: rgba(248, 113, 113, 0.28);

  --info: #60a5fa;
  --info-text: #93c5fd;
  --info-surface: rgba(96, 165, 250, 0.12);
  --info-border: rgba(96, 165, 250, 0.28);
}
```

---

# 8. Typography

## Font priority

Primary:

```text
Plus Jakarta Sans
```

Fallback:

```text
Inter
system-ui
-apple-system
Segoe UI
Roboto
sans-serif
```

Do not introduce unrelated fonts.

## Type scale

### Desktop

```text
Page title       20–24px / 700
Section heading  16–18px / 600
Body             14px / 400–500
Supporting       12–13px / 400–500
Table header     11–13px / 600
```

### Mobile

Avoid simply scaling everything down.

Recommended:

```text
Page title       20–22px
Section heading  16–18px
Body             14–16px
Supporting       12–14px
Table text       13–14px
```

Body text must remain comfortably readable on small screens.

Never sacrifice readability merely to fit more content.

---

# 9. Spacing System

```css
--space-1: 4px;
--space-2: 8px;
--space-3: 12px;
--space-4: 16px;
--space-5: 20px;
--space-6: 24px;
--space-8: 32px;
--space-10: 40px;
```

Default application spacing:

```text
8 / 12 / 16 / 20 / 24px
```

Large spacing should represent meaningful section separation.

Do not add unnecessary 48–80px gaps to operational screens.

### Mobile spacing

Prefer:

```text
4 / 8 / 12 / 16 / 20px
```

Mobile screens should feel compact without feeling cramped.

---

# 10. Border Radius

Use restrained radii.

```css
--radius-sm: 6px;
--radius-md: 8px;
--radius-lg: 12px;
```

Default:

```text
Buttons       6px
Inputs        6px
Selects       6px
Badges        6px
Cards         8px
Tables        8px
Dropdowns     8px
Modals        8–12px
```

Avoid:

```text
rounded-2xl
rounded-3xl
```

as the default visual language.

---

# 11. Elevation & Shadows

Borders are the primary structural mechanism.

Use shadows only for meaningful elevation:

* Dropdowns
* Popovers
* Modals
* Floating menus
* Temporary elevated UI

Avoid shadows on every:

* Card
* Input
* Button
* Table
* Section

Dark mode should rely even more heavily on tonal surface hierarchy.

---

# 12. Motion & Animation

Animation is allowed when it improves usability or communicates state.

> **Subtle motion, not animated everything.**

```css
--motion-fast: 120ms;
--motion-normal: 180ms;
--motion-slow: 240ms;
```

### Appropriate

* Sidebar expand/collapse
* Mobile navigation
* Active indicator movement
* Dropdown opening
* Modal entrance
* Accordion expansion
* Loading states
* Progress indicators
* Toast entrance/exit
* Validation feedback
* Save confirmation
* Upload progress

### Avoid

* Constant floating
* Bouncing cards
* Parallax
* Animated gradients
* Glow animations
* Infinite decorative loops
* Large page-load animations
* Unnecessary icon rotations

### Mobile motion

Mobile animations must be especially lightweight.

Do not animate large areas of the page unnecessarily.

Prefer:

```text
opacity
transform
small height transitions
```

Avoid expensive layout animations.

### Reduced motion

Respect:

```css
@media (prefers-reduced-motion: reduce)
```

When enabled:

* Remove decorative animation
* Reduce transitions
* Disable non-essential motion
* Keep only motion necessary to communicate state

---

# 13. Interaction States

Every interactive component must define:

```text
Default
Hover
Focus
Active
Disabled
Loading
Success
Error
```

Do not design only the default state.

Focus must always remain visible.

---

# 14. Vector Icon System

## No emoji as UI icons

Do not use emoji for:

* Navigation
* Buttons
* Status
* Actions
* Empty states
* Alerts
* Dashboard controls

Use a consistent SVG/vector icon system such as Lucide or an equivalent library.

Icons should be:

* SVG-based
* Crisp
* Theme-aware
* Consistent in stroke weight
* Consistent in visual weight
* Accessible
* Lightweight

Recommended sizes:

```text
16px → compact controls
18px → standard actions
20px → navigation
24px → major contextual actions
```

Do not mix:

```text
filled icon
+ outlined icon
+ emoji
+ random SVG
```

within the same interface.

Icon-only buttons require:

* Accessible label
* Tooltip where appropriate
* Hover state
* Focus state
* Disabled state

---

# 15. Image System

Images are allowed only when they provide genuine context.

Use:

* Institutional imagery
* Department imagery
* Profile photos
* Document previews
* Academic/event imagery
* Useful empty-state illustrations

Avoid:

* Generic startup stock photos
* AI-generated people
* Decorative images
* Images used only to fill empty space

Prefer:

* Natural crops
* Controlled aspect ratios
* 6–8px radius
* Correct `object-fit`
* Explicit dimensions
* Meaningful alt text

## Image performance

Images must be optimized for mobile.

Prefer:

* WebP or AVIF where supported
* Responsive image sizes
* Lazy loading for below-the-fold images
* Proper width/height attributes
* Compressed assets
* Avoid unnecessarily high-resolution images

Do not load a 3000px image when a 600px image is sufficient.

---

# 16. Cards

Cards represent meaningful information groups.

```css
background: var(--surface);
border: 1px solid var(--border);
border-radius: 8px;
```

Avoid excessive nesting:

```text
Page
 └── Card
      └── Card
           └── Card
```

If nesting is necessary, use surface hierarchy instead of additional decorative containers.

### Mobile cards

Cards should:

* Use full available width
* Reduce unnecessary padding
* Keep important information near the top
* Avoid excessive vertical whitespace
* Avoid nested cards where possible

Do not turn every desktop section into a separate mobile card.

---

# 17. Tables

Tables are a core SSMS interaction.

Prioritize:

* Information density
* Clear alignment
* Sorting
* Filtering
* Pagination
* Search
* Row actions
* Status indicators
* Responsive behavior

Desktop:

```text
Header: 11–13px / 600
Body:   13–14px
```

Rows should not be excessively tall.

Use subtle hover states.

Do not turn every row into a floating card.

---

# 18. Mobile Tables

Mobile tables require intentional design.

### Preferred strategy

Use horizontal scrolling when the table contains genuinely tabular information.

```text
┌───────────────────────────────┐
│ ← horizontally scrollable →   │
│ Name | Reg No | Dept | Year   │
│ ...                            │
└───────────────────────────────┘
```

Requirements:

* Preserve table semantics
* Keep the first important column visible where practical
* Allow horizontal scrolling
* Do not force unreadable tiny text
* Keep row actions accessible
* Provide sufficient touch targets
* Avoid wrapping critical identifiers excessively

### Alternative

For very complex datasets, provide a mobile-specific condensed record view.

Example:

```text
Student Name
Register Number
Department
Year
Status

[View] [More]
```

Do not automatically convert every table into cards.

Use the representation that best preserves the user's task.

### Mobile table performance

For large datasets:

* Use pagination
* Prefer server-side pagination where appropriate
* Avoid rendering hundreds/thousands of DOM rows unnecessarily
* Use virtualization when the dataset and framework justify it
* Keep filtering responsive
* Avoid expensive re-renders

---

# 19. Forms

Forms must optimize for data entry.

Use:

* Explicit labels
* Required indicators
* Logical grouping
* Consistent field heights
* Inline validation
* Helpful errors
* Clear submit actions

Desktop:

```text
Label        Label
Input        Input

Label        Label
Input        Input
```

Mobile:

```text
Label
Input

Label
Input
```

Mobile forms should normally become one column.

Do not force two-column forms into narrow mobile layouts.

### Mobile form requirements

* Input width: 100%
* Comfortable touch targets
* Labels always visible
* Avoid placeholder-only labels
* Keep errors close to their fields
* Preserve entered data after validation errors
* Use appropriate mobile input types
* Use numeric keyboards for numeric fields
* Use email keyboards for email fields
* Use date controls where appropriate

Do not make users zoom into form fields.

---

# 20. Buttons

Buttons must use clear verbs.

Good:

```text
Add Student
Save Changes
Upload Document
Generate Report
Delete Record
Download
Edit
```

Avoid decorative wording such as:

```text
Get Started
Launch
Let's Go
Explore Now
```

Buttons require:

* Clear label
* Appropriate size
* Hover
* Focus
* Active
* Loading
* Disabled states

### Mobile buttons

Touch targets must be comfortable.

Do not make important mobile buttons tiny icon-only controls.

Primary actions should be easy to reach.

For forms with important actions:

```text
[ Save Changes ]
[ Cancel ]
```

Maintain sufficient separation between actions to prevent accidental taps.

---

# 21. Search, Filters & Data Controls

Desktop:

```text
Page title                         Primary action

Search   Filter   Status   Date   More

────────────────────────────────────────

Data
```

Mobile should simplify the control area:

```text
Page title

[ Search ]

[ Filter ]

Results
```

or:

```text
[ Search ] [ Filter ]
```

Secondary filters may be placed in a bottom sheet or modal filter panel.

### Important

Do not hide essential functionality merely because the screen is smaller.

Filters must be:

* Discoverable
* Removable
* Resettable
* Easy to understand
* Touch-friendly

Show active filter count when useful.

---

# 22. Status Badges

Use badges only for compact semantic state.

Examples:

```text
Active
Inactive
New
Existing
Pending
Approved
Rejected
Present
Absent
```

Use restrained backgrounds.

Never create rainbow-colored badge systems.

A badge should communicate state immediately without dominating the interface.

---

# 23. Toasts & Notifications

Use toast notifications for short-lived feedback.

Examples:

```text
Student added successfully.
Document uploaded successfully.
Changes saved.
Unable to delete student.
```

Keep them:

* Compact
* Clear
* Dismissible
* Non-blocking

Do not show notifications for every minor interaction.

### Mobile toast behavior

Mobile toasts should:

* Respect safe-area insets
* Avoid covering primary controls
* Stay within the viewport
* Be easy to dismiss
* Remain readable at narrow widths

Avoid extremely wide desktop-style toast containers on mobile.

---

# 24. Modals & Dialogs

Structure:

```text
Title
Short explanation
Content

Cancel      Confirm
```

Animation:

```text
150–220ms
```

### Mobile dialogs

Dialogs should adapt to the viewport.

For larger interactions, prefer a bottom sheet where appropriate.

Bottom sheets should:

* Have clear titles
* Have obvious dismissal
* Respect safe areas
* Support keyboard interaction
* Avoid excessive height when unnecessary

Do not create desktop-sized dialogs that barely fit on mobile.

For destructive actions, make the consequence explicit.

---

# 25. Empty States

Empty states should explain:

1. What happened
2. Why the area is empty when useful
3. What the user can do next

Example:

```text
No students found.

Try changing your filters or add a new student.

[ Add Student ]
```

Optional vector illustration/icon is acceptable when useful.

Do not use:

* Emojis
* Huge illustrations
* Inspirational quotes
* Excessive empty space

---

# 26. Loading States

Use:

* Skeletons
* Compact spinners
* Progress indicators
* Loading labels
* Disabled submit buttons

Loading should reflect real activity.

For long operations:

```text
Uploading documents...

47 of 120 files processed
```

### Mobile loading

Keep loading indicators close to the affected content.

Avoid blocking the entire mobile screen unless the operation genuinely requires it.

Skeletons should match the final layout to reduce layout shift.

---

# 27. Error Handling

Errors must be actionable.

Bad:

```text
Something went wrong.
```

Better:

```text
Unable to upload the document.

The file exceeds the 10 MB limit.

Choose another file.
```

Errors should identify:

1. What happened
2. Why, when known
3. What the user can do next

Never communicate errors through color alone.

---

# 28. Dashboard UX

The dashboard should answer:

> **What matters right now?**

Prioritize:

1. Operational metrics
2. Pending tasks
3. Recent activity
4. Alerts
5. Relevant trends
6. Frequently used actions

Do not fill the dashboard with unnecessary charts.

A useful dashboard is better than a visually impressive dashboard.

### Mobile dashboard

Mobile should prioritize:

```text
Most important metrics
↓
Pending actions
↓
Alerts
↓
Recent activity
↓
Secondary analytics
```

Do not simply preserve a multi-column desktop dashboard and stack twenty cards vertically.

Mobile dashboards should reduce cognitive load.

---

# 29. Metric Cards

Metric cards are allowed when operationally useful.

Good:

```text
Total Students

1,284

+32 this semester
```

Do not give every metric:

* A different color
* A different card style
* A different illustration
* A gradient
* A decorative icon

Use a consistent structure.

On mobile, prioritize the most important metrics and allow secondary metrics to follow.

---

# 30. Data Visualization

Charts must represent meaningful data.

Prefer:

* Line charts for trends
* Bar charts for comparisons
* Donuts only for simple proportions
* Tables when exact values matter more

Avoid:

* 3D charts
* Decorative charts
* Fake data
* Excessive colors
* Gradient fills
* Charts without actionable meaning

Charts require mobile-specific treatment.

On small screens:

* Reduce unnecessary labels
* Allow horizontal scrolling for complex charts
* Simplify legends
* Avoid tiny axis labels
* Preserve readable tooltips
* Prefer simpler chart types where appropriate

Do not force a desktop chart into a tiny mobile rectangle.

---

# 31. Navigation Architecture

Navigation must be predictable.

Example:

```text
Dashboard
Students
Staff
Attendance
Marks
Documents
Reports
Settings
```

Hierarchy:

```text
Primary section
 └── Subsection
      └── Current page
```

Active navigation uses:

* Sage Teal
* Subtle background
* Clear indicator
* Strong text contrast

---

# 32. Desktop Sidebar

Expanded:

```text
280–320px
```

Collapsed:

```text
64–72px
```

Support:

* Collapse/expand
* Clear active state
* Tooltips in collapsed mode
* Grouped navigation
* Keyboard accessibility

Transitions should be subtle.

---

# 33. Mobile Navigation

Mobile navigation is a **primary UX component**, not an afterthought.

The desktop sidebar must not simply become a permanently visible narrow sidebar.

Preferred patterns:

* Hamburger + drawer
* Bottom navigation for high-frequency sections
* Full-height navigation drawer
* Contextual navigation where appropriate

### Mobile navigation priorities

Show the most frequently used sections first.

Secondary sections may be grouped under:

```text
More
```

or an equivalent menu.

### Navigation drawer

The drawer should:

* Open quickly
* Have clear hierarchy
* Show current page
* Close predictably
* Support swipe dismissal where appropriate
* Respect safe-area insets
* Prevent accidental background interaction

Do not animate every menu item individually.

---

# 34. Top Navigation

Desktop:

```text
Logo / Institution
Page context
Search
Notifications
Profile
```

Typical height:

```text
56–68px
```

Keep it compact.

### Mobile topbar

Prioritize:

```text
Menu
Page title / context
Essential action
```

Do not attempt to fit:

```text
logo + breadcrumbs + search + notifications + profile + multiple actions
```

into one tiny row.

Secondary actions should move into:

* Overflow menus
* Bottom sheets
* Contextual action menus

---

# 35. Responsive Breakpoints

Use responsive behavior based on available space rather than device-brand assumptions.

Suggested baseline:

```text
Mobile       < 640px
Tablet       640–1023px
Desktop      1024px+
Large        1280px+
```

These values may be adjusted to the application's actual component behavior.

### Mobile-first principle

Components should be designed from their smallest useful layout upward.

Do not rely on desktop CSS as the foundation and then patch mobile with dozens of overrides.

---

# 36. Mobile Layout Rules

### Mobile must:

* Use one-column layouts where appropriate
* Stack forms
* Simplify navigation
* Preserve primary actions
* Allow table scrolling
* Collapse secondary actions
* Use bottom sheets where appropriate
* Reduce unnecessary padding
* Maintain readable typography
* Maintain touch-friendly targets
* Respect safe areas
* Prevent horizontal page overflow

### Mobile must not:

* Shrink desktop UI until text becomes unreadable
* Hide critical functionality
* Require horizontal scrolling for the entire application
* Use tiny buttons
* Use tiny form controls
* Create oversized cards
* Preserve unnecessary desktop columns
* Force complex desktop dashboards into long vertical stacks

---

# 37. Touch Interaction

Touch is a core interaction model.

Interactive controls should have comfortable touch targets.

Pay particular attention to:

* Buttons
* Icon buttons
* Checkboxes
* Switches
* Table actions
* Pagination
* Tabs
* Dropdown options
* Navigation items

Do not place destructive and non-destructive actions immediately adjacent without sufficient separation.

Avoid hover-only functionality.

> **Anything essential on desktop must remain usable without hover on mobile.**

---

# 38. Mobile Forms & Keyboard Behavior

Mobile keyboards can significantly reduce the available viewport.

The UI must:

* Scroll focused fields into view
* Avoid hiding the active input behind fixed UI
* Keep submit actions accessible
* Handle virtual keyboard resizing correctly
* Avoid unnecessary fixed-height containers
* Preserve entered data

Use appropriate input types:

```text
email
tel
number
date
search
url
```

Do not force users to type everything using a generic text keyboard.

---

# 39. Safe Areas

Mobile UI must account for devices with:

* Notches
* Rounded corners
* Home indicators
* Browser UI overlays

Fixed elements should respect safe-area insets where applicable.

Examples:

```css
padding-bottom: env(safe-area-inset-bottom);
padding-top: env(safe-area-inset-top);
```

Do not place important controls directly against screen edges.

---

# 40. Mobile Performance — Key Priority

Performance is part of the design system.

SSMS must feel fast even on:

* Mid-range Android phones
* Older devices
* Mobile networks
* High-latency connections
* Low-memory environments

### Prioritize

* Fast initial rendering
* Small JavaScript bundles
* Optimized CSS
* Optimized images
* Lazy loading
* Efficient API requests
* Pagination
* Caching where appropriate
* Minimal unnecessary re-renders
* Efficient tables
* Lightweight animations

### Avoid

* Huge image assets
* Unnecessary libraries
* Large icon bundles when tree-shaking is possible
* Heavy animation libraries for simple transitions
* Rendering entire datasets unnecessarily
* Repeated API calls
* Blocking JavaScript
* Unnecessary page-wide effects

---

# 41. Mobile Network Optimization

Design for unreliable networks.

The UI should provide:

```text
Loading
Success
Error
Retry
Offline/connection state where relevant
```

Avoid making the user wonder whether an action worked.

For large operations:

```text
Uploading...
Processing...
Completed
```

Where appropriate, preserve the user's input while requests are processing.

Do not automatically repeat destructive requests.

---

# 42. API & Data Loading UX

For data-heavy pages:

* Load critical content first
* Defer secondary content
* Paginate large datasets
* Avoid requesting unnecessary fields
* Debounce search requests
* Avoid firing a request on every keystroke
* Cache stable data where appropriate
* Cancel obsolete requests where supported

Search/filter interactions should remain responsive.

---

# 43. Layout Stability

Avoid layout shifts.

Reserve space for:

* Images
* Tables
* Charts
* Loading states
* Notifications
* Dynamic controls

Do not allow content to jump unexpectedly after loading.

Mobile users are especially sensitive to layout shifts because small screens amplify movement.

---

# 44. Tables & Large Data Performance

For large SSMS datasets:

* Prefer pagination
* Use server-side filtering where appropriate
* Avoid rendering unnecessary rows
* Use virtualization when justified
* Keep row components lightweight
* Avoid expensive calculations during rendering
* Memoize expensive derived data where appropriate
* Debounce search
* Avoid unnecessary full-table re-renders

Performance must not be sacrificed for decorative animation.

---

# 45. Dark Mode Component Rules

## Inputs

```css
background: #0f1724;
border: 1px solid #334155;
color: #e2e8f0;
```

Placeholder:

```css
color: #718096;
```

Focus:

```css
border-color: #6f9290;
box-shadow: 0 0 0 3px rgba(90,125,124,0.18);
```

Disabled controls must remain visible enough to understand their state.

## Tables

Container:

```css
background: #111827;
border: 1px solid #263244;
```

Header:

```css
background: #151d2b;
color: #cbd5e1;
border-bottom: 1px solid #334155;
```

Row:

```css
background: transparent;
border-bottom: 1px solid #1f2937;
```

Hover:

```css
background: #172033;
```

Selected:

```css
background: rgba(90,125,124,0.10);
```

Avoid unnecessary zebra striping.

## Badges

Semantic foreground colors must be adapted for dark backgrounds.

Do not blindly reuse light-mode semantic colors.

## Buttons

Primary:

```css
background: #6f9290;
color: #071011;
```

Hover:

```css
background: #7da19f;
```

Pressed:

```css
background: #587b79;
```

Secondary:

```css
background: #172033;
border: 1px solid #334155;
color: #e2e8f0;
```

Do not make every button teal.

---

# 46. Dark Mode Surface Hierarchy

Canonical hierarchy:

```text
Level 0
#0b0f19
Application background

Level 1
#111827
Primary surface

Level 2
#172033
Elevated surface

Level 3
#1f2937
Hover / nested controls

Level 4
#263447
Strong interactive state
```

Not every component requires a unique level.

The hierarchy exists to prevent everything from looking identical.

---

# 47. Dark Mode Anti-Patterns

Never implement:

```text
#000000 background
+
#ffffff everything
```

Never implement:

```text
dark background
+
bright teal glow everywhere
```

Never implement:

```text
light theme
+
CSS invert()
```

Never implement:

```text
all cards = #111827
all borders = #111827
```

Never implement:

```text
all text = #ffffff
```

Never use universal:

```css
opacity: 0.5;
```

for disabled controls.

---

# 48. Contrast & Accessibility

Every important combination must be checked against its actual surface.

Test:

* Text vs body
* Text vs cards
* Text vs inputs
* Text vs tables
* Text vs modals
* Text vs dropdowns
* Text vs tooltips
* Text vs selected rows
* Text vs badges

Target WCAG AA:

```text
Normal text       4.5:1
Large text        3:1
UI components     3:1
```

Also verify:

* Focus indicators
* Borders
* Switches
* Checkboxes
* Icons
* Non-text controls

Do not communicate meaning through color alone.

---

# 49. Accessibility

Required:

* Semantic HTML
* Keyboard navigation
* Visible focus states
* Adequate contrast
* Accessible labels
* Accessible tooltips
* Meaningful alt text
* Screen-reader-friendly status messages
* Errors that do not rely only on color
* Logical focus order
* Correct heading hierarchy
* Proper form labels

Mobile accessibility must include:

* Comfortable touch targets
* Readable text
* Predictable gestures
* No hover dependency
* Screen-reader support
* Proper focus management in drawers/modals
* Accessible bottom sheets

---

# 50. Component Reuse

Before creating a component, inspect the existing SSMS UI.

Reuse:

* Buttons
* Inputs
* Tables
* Badges
* Modals
* Cards
* Navigation
* Toolbars
* Dropdowns
* Toasts
* Form layouts
* Responsive patterns

Do not create visually different versions of the same component on different pages.

A new component must visually belong to the existing system.

---

# 51. Visual Hierarchy

Every screen should have an obvious hierarchy:

```text
Page
│
├── Page title
│
├── Context / description
│
├── Primary actions
│
├── Search / filters
│
├── Primary content
│
└── Secondary information
```

A user should understand the page within seconds.

Mobile should preserve the same hierarchy while reducing simultaneous visual complexity.

---

# 52. Enterprise Density

SSMS is not a marketing website.

Default density should favor:

```text
More useful information
+
Less decorative space
```

Use compact:

* Tables
* Forms
* Filters
* Navigation
* Toolbars
* Status indicators

Whitespace should separate concepts, not inflate components.

---

# 53. Premium Feel Without Vibe Coding

A premium SSMS interface comes from:

* Excellent typography
* Consistent spacing
* Precise alignment
* Strong grid systems
* Crisp borders
* Responsive behavior
* Meaningful motion
* High-quality vector icons
* Clear states
* Good empty states
* Good loading states
* Good error handling
* Consistent component behavior
* Fast performance

Not from:

```text
gradients
+
glows
+
blur
+
giant cards
+
huge typography
+
animations everywhere
```

---

# 54. Mobile-First Quality Standard

Every major SSMS page must be explicitly reviewed at:

```text
320px
360px
390px
414px
768px
1024px
1280px+
```

At minimum verify:

### Layout

* No unintended horizontal page scrolling
* No clipped content
* No overlapping elements
* Correct stacking
* Correct spacing
* Correct navigation

### Forms

* Inputs fit viewport
* Keyboard does not hide fields
* Errors are visible
* Buttons are reachable
* Labels remain readable

### Tables

* Horizontal scrolling works
* Important columns remain discoverable
* Actions remain accessible
* Text remains readable

### Navigation

* Drawer opens correctly
* Current page is obvious
* Close behavior works
* No content remains inaccessible

### Modals

* Fit small screens
* Do not overflow
* Buttons remain reachable
* Keyboard/focus behavior works

### Performance

* Fast initial render
* No unnecessary animations
* Images optimized
* Large data does not freeze the UI
* Network delays are communicated

---

# 55. Mobile Visual Rules

Mobile is not an opportunity to add more cards.

Prefer:

```text
clear section
↓
important content
↓
primary action
↓
secondary content
```

Avoid:

```text
card
 card
  card
   card
    card
```

Use typography, dividers, spacing and surface changes to establish hierarchy.

---

# 56. Theme Switching

Supported modes:

```text
Light
Dark
System
```

If System mode exists, respect:

```css
prefers-color-scheme
```

Theme switching should be fast.

Recommended:

```css
transition:
  background-color 150ms ease,
  border-color 150ms ease,
  color 150ms ease;
```

Do not animate:

* Layout
* Width
* Height
* Position
* Entire page content

during theme switching.

Content should remain stationary.

---

# 57. Theme Persistence

The selected theme must persist.

An explicit user selection must not unexpectedly change during normal usage.

Components must use semantic tokens.

Bad:

```css
background: #172033;
```

repeated throughout components.

Better:

```css
background: var(--surface-elevated);
```

This allows the design system to evolve without rewriting components.

---

# 58. Performance Guardrails

When implementing any UI:

### Prefer

* CSS transitions
* CSS transforms
* Native browser APIs
* SVG icons
* Optimized assets
* Lazy loading
* Pagination
* Debounced search
* Code splitting where useful
* Reusable components
* Semantic tokens

### Avoid

* Heavy animation libraries for simple effects
* Large background videos
* Unnecessary dependencies
* Huge SVG illustrations
* Excessive DOM nesting
* Repeated network requests
* Rendering unused content
* Continuous animations
* Expensive visual filters

Do not sacrifice application speed for visual polish.

---

# 59. AI Implementation Guardrails

When an AI coding agent modifies SSMS:

## MUST

1. Inspect existing components before creating new ones.
2. Reuse existing design tokens.
3. Reuse existing icon libraries.
4. Follow established spacing.
5. Follow established typography.
6. Preserve existing functionality.
7. Maintain responsive behavior.
8. Treat mobile as a first-class layout.
9. Optimize mobile performance.
10. Implement loading, error, disabled and success states where applicable.
11. Use subtle animation only when it improves UX.
12. Prefer SVG/vector icons over emojis.
13. Use real images only when meaningful.
14. Keep information density high.
15. Maintain light and dark theme compatibility.
16. Keep interactions predictable.
17. Test small viewport layouts.
18. Prevent horizontal overflow.
19. Avoid unnecessary API requests.
20. Preserve accessibility.

## MUST NOT

1. Introduce random gradients.
2. Introduce decorative blobs.
3. Introduce glassmorphism.
4. Introduce excessive shadows.
5. Introduce oversized rounded cards.
6. Introduce emojis as UI elements.
7. Introduce unrelated icon styles.
8. Create unnecessary cards.
9. Create fake statistics or charts.
10. Add animation simply to make the interface "feel alive."
11. Redesign unrelated components while implementing a feature.
12. Replace functional tables with decorative cards.
13. Introduce a completely new color palette.
14. Introduce a new font without approval.
15. Turn application screens into marketing pages.
16. Treat mobile as a secondary afterthought.
17. Hide important functionality merely because the viewport is small.
18. Introduce unnecessary dependencies.
19. Render huge datasets without considering performance.
20. Create desktop-only interactions.

---

# 60. Decision Rule for AI Agents

Before adding any visual treatment, ask:

```text
Does this improve usability?

Does this communicate state?

Does this improve hierarchy?

Does this improve navigation?

Does this reinforce SSMS identity?

Is it consistent with existing components?

Does it work well on mobile?

Does it preserve performance?

Does it remain accessible?
```

If none apply:

> **Do not add it.**

When choosing between:

### A

Flashy, highly stylized, animated UI

### B

Restrained, polished, information-dense enterprise UI

**Choose B.**

When choosing between:

### A

Static but functional UI

### B

Subtle interaction that communicates state

**Choose B.**

When choosing between:

### A

Emoji

### B

Consistent vector/SVG icon

**Choose B.**

When choosing between:

### A

Desktop UI squeezed onto mobile

### B

Purpose-built responsive mobile experience

**Choose B.**

When choosing between:

### A

Decorative optimization

### B

Faster loading and smoother interaction

**Choose B.**

---

# 61. Final Dark Mode Character

SSMS dark mode should look like:

> **Obsidian institutional software with a restrained Sage Teal identity.**

Think:

```text
Deep neutral background
        ↓
Layered slate surfaces
        ↓
Crisp borders
        ↓
Controlled teal accents
        ↓
Soft semantic colors
        ↓
Clear typography
        ↓
Precise vector icons
        ↓
Subtle motion
```

Not:

```text
Black
+
Neon teal
+
Glow
+
Glass
+
Gradient
+
Animation
```

The dark theme should feel premium because it is precise, not because it is visually loud.

---

# 62. Final SSMS Visual Character

SSMS should feel like:

> **A modern university enterprise platform with the precision of professional administrative software.**

The experience should be:

**Clean → Dense → Calm → Precise → Responsive → Accessible → Fast → Polished**

It should never feel:

**Glossy → Noisy → Over-animated → Generic → AI-generated → Decorative → Slow**

The goal is not to make SSMS look fancy.

The goal is to make users think:

> **"This feels like a serious, well-engineered system."**
# SSMS — Emoji, Vector Icon & Image Rule

## No Emoji as UI Elements

**Do not use emojis anywhere as part of the application UI.**

This includes:

* Navigation icons
* Button icons
* Action icons
* Status indicators
* Alerts
* Toasts
* Empty states
* Dashboard cards
* Form controls
* Table actions
* Menu items
* Authentication screens
* Decorative UI elements

Do not use emojis such as:

```text
😀 🎉 🚀 ✨ 📊 📁 ⚙️ 🔥 ❤️ 👍 ❌ ✅ ⚠️
```

as substitutes for interface icons or visual elements.

### Why

Emoji rendering varies between:

* Android
* iOS
* Windows
* macOS
* Different browsers
* Different system fonts

This creates inconsistent visual weight, alignment, appearance, and meaning.

SSMS must maintain a consistent professional institutional identity across devices.

---

# Vector Icons Instead

Use a consistent **SVG/vector icon system**.

Preferred:

* Lucide
* Another consistent SVG icon library
* Existing SSMS icon components
* Custom SVG icons when necessary

Icons must be:

* Vector/SVG based
* Crisp at all resolutions
* Theme-aware
* Consistent in stroke weight
* Consistent in visual style
* Accessible
* Lightweight
* Responsive

Recommended sizes:

```text
16px → compact controls
18px → standard actions
20px → navigation
24px → major contextual actions
```

Use vector icons for:

```text
Search
Filter
Edit
Delete
Download
Upload
Add
Settings
Notifications
Calendar
Documents
Attendance
Students
Staff
Reports
Navigation
More
Back
Forward
Refresh
```

### Do not mix icon styles

Avoid combinations such as:

```text
Outlined SVG
+
Filled SVG
+
Emoji
+
Random icon package
+
Custom inconsistent SVG
```

within the same interface.

Choose one coherent icon language and maintain it across SSMS.

---

# Images Instead of Decorative Emoji

When a visual requires more than an icon, use an appropriate **real image, illustration, or SVG graphic**.

Use images when they provide genuine context:

* Institutional photographs
* Department photographs
* Academic/event imagery
* Student/staff profile photographs
* Document previews
* Institutional graphics
* Purposeful empty-state illustrations

Do not replace meaningful imagery with emoji.

Do not add images merely to make a screen look more visually impressive.

### Image requirements

Images should:

* Have a genuine purpose
* Be properly cropped
* Use appropriate aspect ratios
* Have meaningful alt text
* Be optimized for mobile
* Use WebP/AVIF where appropriate
* Be lazy-loaded when appropriate
* Avoid unnecessary large resolutions

Avoid:

* Generic stock people
* AI-generated people
* Decorative filler images
* Random illustrations
* Abstract blobs
* Unrelated photography

---

# Icon vs Image Decision Rule

Use an **icon** when representing an action, state, or navigation concept.

Use an **image** when the visual provides real contextual information.

Use an **illustration/SVG graphic** when it genuinely helps explain an empty, unavailable, or informational state.

Do **not** use an emoji as a replacement for any of these.

### Example

Bad:

```text
📚 Students
📄 Documents
⚙️ Settings
🗑️ Delete
```

Good:

```text
[Users icon] Students
[File icon] Documents
[Settings icon] Settings
[Trash icon] Delete
```

The icons above must be actual SVG/vector assets, not emoji characters.

---

# Absolute Rule

> **No emoji-based UI. Use consistent vector icons for interface elements and meaningful images/SVG graphics when visual content is required.**

This rule applies to **desktop, tablet, and mobile**, in both **light and dark mode**.

AI coding agents must not introduce emoji UI even if an emoji appears to be the quickest or most convenient implementation.
