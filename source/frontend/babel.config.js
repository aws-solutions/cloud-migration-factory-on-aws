module.exports = {
  plugins:['transform-flow-strip-types'],
  presets: [
    '@babel/preset-env',
    ['@babel/preset-react', {runtime: 'automatic'}]
  ],
};