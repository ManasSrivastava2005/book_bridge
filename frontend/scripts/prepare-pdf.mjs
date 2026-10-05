import { cpSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
import { dirname, resolve } from 'node:path';
const require = createRequire(import.meta.url);
const root = dirname(require.resolve('pdfjs-dist/package.json'));
const output = new URL('../public/pdfjs/', import.meta.url);
mkdirSync(output, { recursive: true });
for (const name of ['cmaps', 'standard_fonts', 'wasm']) cpSync(resolve(root, name), new URL(name, output), { recursive: true });
