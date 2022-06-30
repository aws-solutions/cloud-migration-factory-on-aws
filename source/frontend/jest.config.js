const config = {
  "verbose": true,
  "collectCoverage": true,
  "testResultsProcessor": "jest-sonar-reporter",
  "transform": {
    '\\.[jt]sx?$': 'babel-jest',
    'node_modules/@awsui/.+\\.js$': './node_modules/@awsui/jest-preset/js-transformer.js',
    'node_modules/@awsui/.+\\.css': './node_modules/@awsui/jest-preset/css-transformer.js'
  },
  "transformIgnorePatterns": [
    '/node_modules/(?!@awsui/).+\\.js$'
  ],
  "moduleNameMapper": {
    "ace-builds": "<rootDir>/node_modules/ace-builds"
  }
};
console.log(config)

module.exports = config;