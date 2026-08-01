# SalvageNet public website

Static Astro website published at [salvage.network](https://salvage.network).

## Local development

```sh
npm ci
npm run dev
```

## Production build

```sh
npm run build
```

The output is written to `dist/`. GitHub Actions builds this directory and deploys the exact artifact to GitHub Pages whenever website files change on `main`.

Public product detail is intentionally progressive: the top-level pages explain why SalvageNet is useful; engineering records remain in the repository.
