/**
 * Tests for DPS Scraper functionality
 */

const { DPSScraper } = require('../dps_scraper');
const fs = require('fs').promises;
const path = require('path');

// Mock Playwright
jest.mock('playwright', () => ({
  chromium: {
    launch: jest.fn(),
  },
}));

// Mock yargs for CLI testing
jest.mock('yargs/yargs');
jest.mock('yargs/helpers');

describe('DPSScraper', () => {
  let scraper;
  let mockBrowser;
  let mockContext;
  let mockPage;

  beforeEach(() => {
    // Set up environment variables
    process.env.DPS_USERNAME = 'test_user';
    process.env.DPS_PASSWORD = 'test_pass';

    // Create scraper instance
    scraper = new DPSScraper({
      outputDir: '/tmp/test_output',
      headless: true,
    });

    // Set up Playwright mocks
    mockPage = {
      setDefaultTimeout: jest.fn(),
      goto: jest.fn(),
      waitForSelector: jest.fn(),
      fill: jest.fn(),
      click: jest.fn(),
      waitForLoadState: jest.fn(),
      waitForFunction: jest.fn(),
      $: jest.fn(),
      $$: jest.fn(),
      url: jest.fn().mockReturnValue('https://example.com'),
      screenshot: jest.fn(),
    };

    mockContext = {
      newPage: jest.fn().mockResolvedValue(mockPage),
    };

    mockBrowser = {
      newContext: jest.fn().mockResolvedValue(mockContext),
      close: jest.fn(),
    };

    const { chromium } = require('playwright');
    chromium.launch.mockResolvedValue(mockBrowser);
  });

  afterEach(() => {
    jest.clearAllMocks();
    delete process.env.DPS_USERNAME;
    delete process.env.DPS_PASSWORD;
  });

  describe('Constructor', () => {
    test('should initialize with environment variables', () => {
      expect(scraper.username).toBe('test_user');
      expect(scraper.password).toBe('test_pass');
      expect(scraper.outputDir).toBe('/tmp/test_output');
      expect(scraper.headless).toBe(true);
    });

    test('should throw error when credentials missing', () => {
      delete process.env.DPS_USERNAME;
      delete process.env.DPS_PASSWORD;

      expect(() => {
        new DPSScraper();
      }).toThrow('DPS_USERNAME and DPS_PASSWORD environment variables required');
    });

    test('should use default options', () => {
      const defaultScraper = new DPSScraper();
      expect(defaultScraper.outputDir).toBe('../data/scraped');
      expect(defaultScraper.headless).toBe(true);
      expect(defaultScraper.timeout).toBe(30000);
    });
  });

  describe('ensureOutputDir', () => {
    test('should create output directory', async () => {
      const mkdirSpy = jest.spyOn(fs, 'mkdir').mockResolvedValue();

      await scraper.ensureOutputDir();

      expect(mkdirSpy).toHaveBeenCalledWith('/tmp/test_output', { recursive: true });
      mkdirSpy.mockRestore();
    });

    test('should handle mkdir errors gracefully', async () => {
      const mkdirSpy = jest.spyOn(fs, 'mkdir').mockRejectedValue(new Error('Permission denied'));
      const consoleSpy = jest.spyOn(console, 'warn').mockImplementation();

      await scraper.ensureOutputDir();

      expect(consoleSpy).toHaveBeenCalledWith('Output directory creation warning:', 'Permission denied');
      mkdirSpy.mockRestore();
      consoleSpy.mockRestore();
    });
  });

  describe('performLogin', () => {
    test('should perform successful login', async () => {
      mockPage.waitForSelector.mockResolvedValue();

      await scraper.performLogin(mockPage);

      expect(mockPage.waitForSelector).toHaveBeenCalledWith(
        'input[name="username"], input[type="email"]',
        { timeout: 10000 }
      );
      expect(mockPage.fill).toHaveBeenCalledTimes(2);
      expect(mockPage.click).toHaveBeenCalledWith('button[type="submit"], input[type="submit"]');
      expect(mockPage.waitForLoadState).toHaveBeenCalledWith('networkidle');
    });

    test('should handle login failure', async () => {
      mockPage.waitForSelector.mockRejectedValue(new Error('Selector not found'));

      await expect(scraper.performLogin(mockPage)).rejects.toThrow('Login failed: Selector not found');
    });
  });

  describe('handleDuoAuth', () => {
    test('should handle missing Duo frame', async () => {
      mockPage.waitForSelector.mockRejectedValue(new Error('Timeout'));
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      await scraper.handleDuoAuth(mockPage);

      expect(consoleSpy).toHaveBeenCalledWith('ℹ️  No Duo authentication required');
      consoleSpy.mockRestore();
    });

    test('should handle Duo authentication flow', async () => {
      const mockDuoFrame = {};
      mockPage.waitForSelector.mockResolvedValue(mockDuoFrame);
      mockPage.waitForFunction.mockResolvedValue();
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      await scraper.handleDuoAuth(mockPage);

      expect(consoleSpy).toHaveBeenCalledWith('🔒 Duo MFA detected - manual approval required');
      expect(consoleSpy).toHaveBeenCalledWith('✅ Duo authentication completed');
      consoleSpy.mockRestore();
    });
  });

  describe('saveScrapedData', () => {
    test('should save data to file', async () => {
      const writeFileSpy = jest.spyOn(fs, 'writeFile').mockResolvedValue();
      const consoleSpy = jest.spyOn(console, 'log').mockImplementation();

      const testData = { test: 'data' };
      const result = await scraper.saveScrapedData(testData, 'TestStudent');

      expect(writeFileSpy).toHaveBeenCalled();
      expect(result).toContain('scrape_TestStudent_');
      expect(result).toContain('.json');
      expect(consoleSpy).toHaveBeenCalledWith(expect.stringContaining('💾 Data saved to:'));

      writeFileSpy.mockRestore();
      consoleSpy.mockRestore();
    });
  });
});
