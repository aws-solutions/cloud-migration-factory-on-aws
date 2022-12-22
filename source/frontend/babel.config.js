/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: Apache-2.0
 */

module.exports = {
  plugins:['transform-flow-strip-types'],
  presets: [
    '@babel/preset-env',
    ['@babel/preset-react', {runtime: 'automatic'}]
  ],
};