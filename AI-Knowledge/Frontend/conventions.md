# Frontend Conventions

## TypeScript
- Strict mode on (`strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`)
- No `any`. Use `unknown` and narrow, or define a proper type.
- All component props have explicit interfaces — never inline object types on the function signature.

## React
- Components in `PascalCase.tsx`, hooks in `camelCase.ts`
- Side effects always in custom hooks, not directly in components
- No business logic in components — keep them presentational where possible
- `useCallback`/`useMemo` only when there's a real performance reason, not by default

## CSS
- Vanilla CSS in `index.css` with CSS custom properties for theming
- Class names reflect BEM-lite structure: `.block`, `.block-element`, `.modifier`
- No inline styles
- Dark theme by default via `color-scheme: dark`

## Testing
- Vitest + `@testing-library/react` for unit and component tests
- Test behaviour, not implementation (assert what the user sees, not internal state)
- Playwright for end-to-end tests — tests live in `e2e/`
