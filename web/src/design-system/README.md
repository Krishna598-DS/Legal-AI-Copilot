# Design System

Reusable UI for AI Legal Copilot. Built on **shadcn/ui (Radix)**, Tailwind, Framer Motion, Lucide, React Hook Form, Zod, and TanStack Query.

## Import rule

```ts
import { Button, EmptyState, useZodForm, toast } from "@/design-system";
```

Prefer `@/design-system` in feature code. `@/components/ui/*` is the low-level shadcn layer — do not duplicate those primitives elsewhere.

## What’s included

| Area | Exports |
|---|---|
| Tokens | `spacing`, `motion`, `typography`, `StatusTone` |
| Type | `Text`, `Heading` |
| Motion | `FadeIn`, `Presence` (respects `prefers-reduced-motion`) |
| Providers | `DesignSystemProvider`, `ThemeProvider`, `QueryProvider` |
| Forms | `useZodForm`, `FormRoot`, field helpers, `PasswordInput` |
| Feedback | `toast`, `Modal`, `ConfirmDialog`, skeletons, `EmptyState`, `StatusBadge` |
| Nav | `AppNav`, `AppBreadcrumbs`, `PageHeader`, `AppSidebar`, `UserMenu` |
| Data | `DataTable` |
| Primitives | Button, Input, Dialog, Tabs, Dropdown, Table, Sidebar, … |

## Theming

- CSS variables in `src/app/globals.css` (`:root` light, `.dark` dark)
- `next-themes` via `ThemeProvider` (`attribute="class"`)
- Teal primary for actions/evidence; severity via `success` / `warning` / `destructive`

## Accessibility

- Focus rings on interactive controls
- Form fields wire `aria-invalid` / `aria-describedby`
- Dialogs/menus use Radix focus management
- Motion disabled under `prefers-reduced-motion`

## Providers

Wrap the app once:

```tsx
<DesignSystemProvider>{children}</DesignSystemProvider>
```

Use `withSidebar` when the shell uses `AppSidebar`.
