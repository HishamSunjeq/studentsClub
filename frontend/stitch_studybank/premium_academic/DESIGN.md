---
name: Premium Academic
colors:
  surface: '#131313'
  surface-dim: '#131313'
  surface-bright: '#3a3939'
  surface-container-lowest: '#0e0e0e'
  surface-container-low: '#1c1b1b'
  surface-container: '#201f1f'
  surface-container-high: '#2a2a2a'
  surface-container-highest: '#353534'
  on-surface: '#e5e2e1'
  on-surface-variant: '#c7c4d8'
  inverse-surface: '#e5e2e1'
  inverse-on-surface: '#313030'
  outline: '#918fa1'
  outline-variant: '#464555'
  surface-tint: '#c3c0ff'
  primary: '#c3c0ff'
  on-primary: '#1d00a5'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#4d44e3'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb695'
  on-tertiary: '#571f00'
  tertiary-container: '#a44100'
  on-tertiary-container: '#ffd2be'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb695'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7b2f00'
  background: '#131313'
  on-background: '#e5e2e1'
  surface-variant: '#353534'
typography:
  display-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '600'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  h1:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  ui-medium:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '500'
    lineHeight: 20px
  ui-small:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  study-body:
    fontFamily: Newsreader
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  study-quote:
    fontFamily: Newsreader
    fontSize: 20px
    fontWeight: '400'
    lineHeight: '1.5'
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 8px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 64px
  container-max: 1200px
  sidebar-width: 260px
---

## Brand & Style

The brand personality is authoritative yet accessible, positioned as a high-end tool for serious learners. It merges the systematic efficiency of modern productivity software with the timeless credibility of academic publishing. The emotional response should be one of "quiet focus"—removing the anxiety of study through structural clarity.

The visual style is a hybrid of **Minimalism** and **Tonal Layering**. It avoids the playful, rounded aesthetics often found in EdTech, instead opting for a "Tool-First" philosophy. The interface stays out of the way of the content, using high-quality typography and generous whitespace to create a sense of intellectual breathing room. AI features are integrated as seamless functional enhancements rather than flashy visual gimmicks.

## Colors

The palette is anchored by a "True Neutral" foundation. Dark mode is the primary experience, utilizing a near-black (#0A0A0A) that avoids blue or purple undertones to keep the focus on content. The primary accent is a Deep Indigo (#4F46E5), used sparingly to indicate primary actions and progress.

In light mode, the primary surface is a crisp near-white (#F9FAFB). Success states and secondary highlights use a refined Emerald (#10B981). Neutral scales are tightly controlled to maintain high legibility and a sophisticated, monochromatic feel, with color only appearing to signify intent or focus.

## Typography

This design system employs a dual-typeface strategy to distinguish between "operating" and "learning."

**Inter** is the functional workhorse, used for all navigational elements, buttons, sidebars, and metadata. It is set with tighter letter-spacing in headlines for a confident, modern look.

**Newsreader** is reserved exclusively for study content—questions, textbook excerpts, and AI-generated explanations. It features a generous line height (1.6) to optimize for long-form reading and to evoke the feeling of a premium printed journal. This contrast helps the user psychologically switch from "navigating" to "absorbing."

## Layout & Spacing

The layout follows a **Fixed-Fluid Hybrid** model. The main navigation sidebar is fixed, while the primary study workspace centers itself within a maximum width of 1200px to ensure line lengths for serif text remain readable.

A strictly enforced 4px baseline grid ensures vertical rhythm. Spacing is intentionally generous (24px to 40px between sections) to prevent the "clutter" common in educational platforms. Content-heavy pages should use a single-column "focus mode" where the sidebar collapses, centering the study material to eliminate distractions.

## Elevation & Depth

Depth is conveyed through **Tonal Layers** and **Low-Contrast Outlines** rather than heavy shadows. 

1. **Surface Base:** The bottom-most layer (#0A0A0A).
2. **Surface Container:** Elements like cards or sidebars use a subtle lift (#171717) with a 1px solid border (#262626).
3. **Floating States:** Modals or menus use a slightly more pronounced background (#262626) and a very soft, diffused ambient shadow (Black, 20% opacity, 20px blur).

Interactive elements should not feel "3D" or "squishy." Instead, they use subtle shifts in background color or border intensity to indicate state changes.

## Shapes

The shape language is "Medium Rounded," striking a balance between the clinical sharp corners of professional software and the overly round friendless of casual apps. 

Standard components (inputs, small buttons) use a **10px radius**. Larger containers (cards, modal panels) use a **14px radius**. This consistency creates a cohesive "object" feel across the platform. Icons must follow this logic, using 1.5px strokes and slightly rounded caps and joins to match the UI's geometry.

## Components

**Buttons:**
- Primary: Deep Indigo fill, white text, 10px radius. No gradient.
- Secondary: Transparent fill, 1px neutral border, subtle hover highlight.
- Ghost: No border or fill, primary text color, used for low-priority actions.

**Study Cards:**
- Background: #171717 (Dark Mode).
- Border: 1px solid #262626.
- Padding: 32px (Generous) to allow the serif typography room to breathe.

**Inputs:**
- 1px neutral border. On focus, the border transitions to Deep Indigo with a subtle 2px Indigo glow (low opacity). No "AI sparkles" or animated gradients.

**Icons:**
- Use Lucide-style line icons.
- Stroke weight: 1.5px.
- Size: 20px for UI actions, 16px for inline metadata.

**Specialty Components:**
- **The "Focus Timer":** A minimal, hairline-stroke circular progress indicator using the Primary Accent color.
- **AI Citation:** Small labels in Inter-medium with a subtle Indigo tint to denote AI-assisted content without being distracting.
- **Note-taking Sidebar:** Uses a slightly different background tone to differentiate from the primary study area.