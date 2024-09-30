/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {nodePolyfills} from "vite-plugin-node-polyfills";
import { viteStaticCopy } from "vite-plugin-static-copy";
import path from "path";
import fs from "fs";

/**
 * Define a vite plugin to replace the html file during build time.
 * The index.html files have different content security policies (CSP) for dev and prod.
 */
const htmlReplace = () => {
  const isProd = process.env.NODE_ENV === 'production'; // set by script in package.json

  // noinspection JSUnusedGlobalSymbols
  return {
    name: 'html-replace',
    transformIndexHtml(html) {
      return isProd ?
        fs.readFileSync(path.resolve(__dirname, 'index.prod.html'), 'utf-8') :
        html;
    },
  };
};


export default defineConfig({
  base: '',
  build: {
    rollupOptions: {
      output: {
        inlineDynamicImports : true,
        entryFileNames: `assets/index.js`,
        chunkFileNames: `assets/[name].js`,
        assetFileNames: `assets/[name].[ext]`
      }
    }
  },
  plugins: [
    react(),
    nodePolyfills(),
    htmlReplace(),
    viteStaticCopy({
      targets: [
        {
          src: [
            'node_modules/ace-builds/src-noconflict/ace.js',
            'node_modules/ace-builds/src-noconflict/mode-json.js',
            'node_modules/ace-builds/src-noconflict/worker-json.js'
          ],
          dest: 'assets/ace-builds/src-noconflict/'
        }
      ]
    })
  ],
  server: {
    port: 3000,
  },
});
