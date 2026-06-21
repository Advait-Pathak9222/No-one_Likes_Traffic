import * as esbuild from 'esbuild';
import fs from 'node:fs';
import path from 'node:path';

const projectRoot = process.cwd();
const distDir = path.join(projectRoot, 'dist');
const publicDir = path.join(projectRoot, 'public');
const assetsDir = path.join(distDir, 'assets');
const defaultMapKey = 'yxooegymggcadugrvewdohokcacaqhqashdl';
const mapMyIndiaKey = process.env.VITE_MAPMYINDIA_MAP_KEY || process.env.MAPMYINDIA_MAP_KEY || defaultMapKey;

fs.rmSync(distDir, { recursive: true, force: true });
fs.mkdirSync(assetsDir, { recursive: true });

if (fs.existsSync(publicDir)) {
  fs.cpSync(publicDir, distDir, { recursive: true });
}

await esbuild.build({
  entryPoints: [path.join(projectRoot, 'src/main.tsx')],
  bundle: true,
  outfile: path.join(assetsDir, 'app.js'),
  format: 'esm',
  platform: 'browser',
  target: ['es2020'],
  minify: true,
  sourcemap: false,
  jsx: 'automatic',
  loader: {
    '.css': 'css',
    '.png': 'file',
    '.jpg': 'file',
    '.jpeg': 'file',
    '.svg': 'file',
    '.gif': 'file',
    '.webp': 'file',
    '.woff': 'file',
    '.woff2': 'file',
    '.ttf': 'file'
  },
  define: {
    'process.env.NODE_ENV': '"production"',
    __PARKPULSE_MAPMYINDIA_MAP_KEY__: JSON.stringify(mapMyIndiaKey)
  },
  logLevel: 'info'
});

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>ParkPulse Bengaluru</title>
    <link rel="stylesheet" href="/assets/app.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/assets/app.js"></script>
  </body>
</html>
`;

fs.writeFileSync(path.join(distDir, 'index.html'), html);
console.log(`Built ParkPulse frontend into ${distDir}`);
