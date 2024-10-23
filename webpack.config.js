//@ts-check

const webpack = require('webpack');
const path = require('path');

const { WEBPACK_WATCH, WITH_TOTAL_COVERAGE } = process.env;

/** @type {import('webpack').Configuration} */
const config = {
  output: {
    clean: true,
  },
  target: 'web',
  devtool: 'source-map',
  mode: WEBPACK_WATCH ? 'development' : 'production',
  module: {
    rules: [
      {
        test: /\.js$/,
        use:
          WITH_TOTAL_COVERAGE || WEBPACK_WATCH
            ? ['@ephesoft/webpack.istanbul.loader']
            : ['source-map-loader'],
      },
    ],
  },

  plugins: [],
  ignoreWarnings: [/Failed to parse source map/],
};

module.exports = config;
