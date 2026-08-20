import { defineConfig } from 'astro/config';

export default defineConfig({
  site: 'https://salvage.network',
  output: 'static',
  build: {
    format: 'directory',
  },
});
