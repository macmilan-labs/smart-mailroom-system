---
name: Aura Logic
colors:
  surface: '#131314'
  surface-dim: '#131314'
  surface-bright: '#3a393a'
  surface-container-lowest: '#0e0e0f'
  surface-container-low: '#1c1b1c'
  surface-container: '#201f20'
  surface-container-high: '#2a2a2b'
  surface-container-highest: '#353436'
  on-surface: '#e5e2e3'
  on-surface-variant: '#c1c6d7'
  inverse-surface: '#e5e2e3'
  inverse-on-surface: '#313031'
  outline: '#8b90a0'
  outline-variant: '#414755'
  surface-tint: '#adc6ff'
  primary: '#adc6ff'
  on-primary: '#002e69'
  primary-container: '#4b8eff'
  on-primary-container: '#00285c'
  inverse-primary: '#005bc1'
  secondary: '#4edea3'
  on-secondary: '#003824'
  secondary-container: '#00a572'
  on-secondary-container: '#00311f'
  tertiary: '#ffb3ad'
  on-tertiary: '#68000a'
  tertiary-container: '#ff5451'
  on-tertiary-container: '#5c0008'
  error: '#ffb4ab'
  on-error: '#690005'
  error-container: '#93000a'
  on-error-container: '#ffdad6'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#adc6ff'
  on-primary-fixed: '#001a41'
  on-primary-fixed-variant: '#004493'
  secondary-fixed: '#6ffbbe'
  secondary-fixed-dim: '#4edea3'
  on-secondary-fixed: '#002113'
  on-secondary-fixed-variant: '#005236'
  tertiary-fixed: '#ffdad7'
  tertiary-fixed-dim: '#ffb3ad'
  on-tertiary-fixed: '#410004'
  on-tertiary-fixed-variant: '#930013'
  background: '#131314'
  on-background: '#e5e2e3'
  surface-variant: '#353436'
typography:
  display-xl:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: '1.1'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: '1.3'
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: '1.6'
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.05em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 24px
  margin: 40px
  container-max: 1440px
---

## Brand & Style

The design system is engineered to evoke a sense of absolute security and futuristic precision. It targets high-growth enterprises and modern logistics hubs that prioritize speed and reliability. 

The aesthetic is a hybrid of **Minimalism** and **Glassmorphism**, taking cues from Apple’s structural clarity, Stripe’s vibrant accessibility, and Linear’s high-density efficiency. The interface relies on depth created through light-refracting layers, subtle motion, and high-contrast typography. It feels less like a traditional dashboard and more like a high-tech mission control center—professional, polished, and exceptionally responsive.

## Colors

The palette is anchored in a deep charcoal foundation to provide a "dark mode by default" experience that feels premium and focused. 

*   **Primary (Electric Blue):** Used for primary calls to action and active states. It should feel luminous against the dark background.
*   **Success (Emerald Green):** Dedicated to "Package Granted" or "Sorted" statuses.
*   **Alert (Crimson):** Reserved for urgent delivery exceptions or security breaches.
*   **Neutrals:** A range of grays from `#0A0A0B` (Background) to `#F9FAFB` (Primary Text). 

Use "Border Glows"—ultra-thin, semi-transparent white or primary-tinted strokes—to define edges of containers rather than heavy shadows.

## Typography

This design system utilizes **Inter** for its systematic, utilitarian clarity. The typographic hierarchy relies on extreme contrast between large, tight-tracked display headers and airy, legible body copy.

*   **Headlines:** Use tighter letter-spacing for a modern, "engineered" look.
*   **Labels:** Use all-caps with increased letter-spacing for metadata and category identifiers to distinguish them from interactive text.
*   **Contrast:** Maintain a strict adherence to pure white (#FFFFFF) for headers and a slightly muted gray (#9CA3AF) for secondary body text to direct the user's eye.

## Layout & Spacing

The layout follows a **Fixed Grid** philosophy for dashboard views and a **Fluid Grid** for mobile tracking interfaces. 

*   **Rhythm:** Use an 8px base scaling system. Standard internal padding for cards is 24px.
*   **Whitespace:** Be generous. Proactive use of empty space is required to maintain the "Premium" feel.
*   **Grid:** A 12-column grid with 24px gutters is the standard for desktop. Sidebars should be fixed at 280px to ensure the workspace remains the focus.

## Elevation & Depth

Depth in this design system is achieved through **Glassmorphism** and **Tonal Layering** rather than traditional elevation shadows.

1.  **Base Layer:** The deepest level (#0A0A0B).
2.  **Content Layer:** Cards and containers use a slightly lighter charcoal (#161618) with a 1px "Glow" border.
3.  **Overlay Layer:** Modals and dropdowns use a background blur (`backdrop-filter: blur(20px)`) with a 60% opacity fill of the surface color.
4.  **Shadows:** When used, shadows must be extremely diffused (e.g., `box-shadow: 0 20px 40px rgba(0,0,0,0.4)`), appearing more like an ambient occlusion than a directional shadow.

## Shapes

The shape language is defined by "Super-ellipses" and highly rounded corners. 

*   **Standard Containers:** Use 16px (1rem) for all cards and primary containers.
*   **Interactive Elements:** Buttons and input fields should utilize 12px (0.75rem) to feel approachable yet precise.
*   **Icons:** Contained within 8px rounded squares or circles to maintain the soft-tech aesthetic.

## Components

*   **Buttons:** Primary buttons feature a subtle gradient from Electric Blue to a slightly darker shade, with a 1px top-inner highlight. No heavy shadows; just a soft glow on hover.
*   **Input Fields:** Ghost-style inputs with a 1px border. On focus, the border transitions to Electric Blue with a soft outer glow.
*   **Glass Cards:** Used for secondary information. These should have a subtle white stroke at 10% opacity and a 20px backdrop blur.
*   **Status Chips:** Small, pill-shaped indicators. For "Success," use Emerald Green text on a 10% opacity Emerald background.
*   **Package Trackers:** A custom component featuring a vertical timeline with "Glow" nodes. Active nodes use the Electric Blue primary color with a pulsing animation.
*   **Data Grids:** Minimalist rows with no vertical lines; use horizontal dividers at 5% white opacity. Hover states should subtly lift the row using a slightly lighter background color.