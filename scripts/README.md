# Entity Verification Script

This directory contains scripts for verifying and validating the kernel entities in the Kai project.

## verify-entities.js

A verification script that validates all entities loaded in the kernel memory are correctly integrated.

### What it checks:

1. **INTEGRATED Status**: Ensures all entities have `status: 'INTEGRATED'`
2. **Valid URLs**: Verifies all entity content starts with `http://` or `https://`
3. **Unique IDs**: Confirms all entity IDs are unique
4. **Required Repositories**: Checks that all recommended repositories from `docs/integrations.md` are included

### Usage:

```bash
# Run the verification script
npm run verify:entities

# Or run directly with Node
node scripts/verify-entities.js
```

### Output:

The script provides:
- A grouped list of all entities by source
- Validation check results
- Total entity count summary
- Exit code 0 if all checks pass, 1 if any fail

### Example Output:

```
🔍 Entity Verification Report

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📦 Awesome List Assimilation (12 entities)
  ✅ awesome-1: https://github.com/enaqx/awesome-react
  ✅ awesome-2: https://github.com/aniftyco/awesome-tailwindcss
  ...

📦 Repositorios Recomendados (9 entities)
  ✅ recommended-1: https://github.com/chroma-core/chroma
  ...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔬 Validation Checks:

✅ All entities have INTEGRATED status
✅ All entities have valid URLs
✅ All entity IDs are unique
✅ All required recommended repositories are included

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Summary: 28 total entities loaded

✨ All validation checks passed!
```

## Adding New Entities

When adding new entities to `src/store/slices/createKernelSlice.ts`:

1. Follow the existing format
2. Use unique IDs (e.g., `awesome-X`, `recommended-X`, `evo-X`)
3. Set `status: 'INTEGRATED'` for all entities
4. Ensure content is a valid URL
5. Run `npm run verify:entities` to validate changes

## Entity Sources

Current entity sources in the kernel:

- **Directiva de Compañero**: Companion directives (e.g., aider)
- **Awesome List Assimilation**: Curated awesome lists
- **Repositorios Recomendados**: Recommended repositories from docs
- **Evolución Dirigida**: Directed evolution integrations
