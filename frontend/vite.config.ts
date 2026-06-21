import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const defaultMapKey = 'yxooegymggcadugrvewdohokcacaqhqashdl';
const mapMyIndiaKey = process.env.VITE_MAPMYINDIA_MAP_KEY || process.env.MAPMYINDIA_MAP_KEY || defaultMapKey;

export default defineConfig({
  plugins: [react()],
  define: {
    __PARKPULSE_MAPMYINDIA_MAP_KEY__: JSON.stringify(mapMyIndiaKey)
  },
  server: {
    host: '127.0.0.1',
    port: 5173
  },
  preview: {
    host: '127.0.0.1',
    port: 4173
  }
});
