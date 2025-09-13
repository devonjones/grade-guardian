module.exports = {
  testEnvironment: 'node',
  collectCoverageFrom: ['*.js', '!jest.config.js', '!.eslintrc.js'],
  coverageDirectory: 'coverage',
  coverageReporters: ['text', 'lcov', 'html'],
  testMatch: ['**/__tests__/**/*.js', '**/*.test.js'],
  verbose: true,
};
