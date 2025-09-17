/**
 * Grade Guardian DPS/Schoology Scraper
 * Uses Playwright to automate login and grade data extraction
 */

const { chromium } = require('playwright');
const fs = require('fs').promises;
const path = require('path');

class DPSScraper {
  constructor(options = {}) {
    this.username = process.env.DPS_USERNAME;
    this.password = process.env.DPS_PASSWORD;
    this.outputDir = options.outputDir || '../data/scraped';
    this.headless = options.headless !== false; // Default to headless
    this.timeout = options.timeout || 30000; // 30 second timeout
    this.remoteDebugging = options.remoteDebugging || false;
    this.debuggingPort = options.debuggingPort || 9222;
    this.debuggingHost = options.debuggingHost || '0.0.0.0';

    if (!this.username || !this.password) {
      throw new Error('DPS_USERNAME and DPS_PASSWORD environment variables required');
    }
  }

  async ensureOutputDir() {
    try {
      await fs.mkdir(this.outputDir, { recursive: true });
    } catch (error) {
      console.warn('Output directory creation warning:', error.message);
    }
  }

  async scrapeGrades(studentName = null) {
    let browser = null;
    let context = null;
    let page = null;

    try {
      console.log('🚀 Starting DPS grade scraping...');

      // Launch browser with optional remote debugging
      const launchOptions = {
        headless: this.headless,
        args: ['--no-sandbox', '--disable-setuid-sandbox'],
      };

      // Add remote debugging if enabled
      if (this.remoteDebugging) {
        // Keep headless mode for server environments, debugging works in headless too
        launchOptions.args.push(`--remote-debugging-port=${this.debuggingPort}`);
        launchOptions.args.push(`--remote-debugging-address=${this.debuggingHost}`);
        console.log(`🔍 Remote debugging enabled on ${this.debuggingHost}:${this.debuggingPort}`);
        console.log(`   Connect from Windows: http://10.5.2.12:${this.debuggingPort}`);
        console.log(`   Access DevTools: chrome://inspect or direct URL`);
      }

      browser = await chromium.launch(launchOptions);

      context = await browser.newContext({
        userAgent:
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
      });

      page = await context.newPage();
      page.setDefaultTimeout(this.timeout);

      // Step 1: Navigate to DPS portal
      console.log('🔗 Navigating to DPS portal...');
      await page.goto('https://portal.dpsk12.org/', { waitUntil: 'networkidle' });

      // Step 2: Login
      console.log('🔐 Logging in...');
      await this.performLogin(page);

      // Step 3: Handle Duo MFA (manual for Phase 1)
      console.log('📱 Waiting for Duo authentication...');
      await this.handleDuoAuth(page);

      // Step 4: Navigate to Schoology
      console.log('🏫 Navigating to Schoology...');
      await this.navigateToSchoology(page);

      // Step 5: Scrape course data
      console.log('📚 Scraping course data...');
      const courseData = await this.scrapeCourseData(page, studentName);

      // Step 6: Save data
      await this.saveScrapedData(courseData, studentName);

      console.log('✅ Scraping completed successfully!');
      return courseData;
    } catch (error) {
      console.error('❌ Scraping failed:', error);

      // Take screenshot for debugging
      if (page) {
        try {
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          await page.screenshot({
            path: path.join(this.outputDir, `error_${timestamp}.png`),
            fullPage: true,
          });
          console.log('📸 Error screenshot saved');
        } catch (screenshotError) {
          console.warn('Failed to take error screenshot:', screenshotError.message);
        }
      }

      throw error;
    } finally {
      if (browser) {
        await browser.close();
      }
    }
  }

  async performLogin(page) {
    try {
      // Wait for login form
      await page.waitForSelector('input[name="username"], input[type="email"]', { timeout: 10000 });

      // Fill username
      const usernameSelector = 'input[name="username"], input[type="email"]';
      await page.fill(usernameSelector, this.username);

      // Fill password
      const passwordSelector = 'input[name="password"], input[type="password"]';
      await page.fill(passwordSelector, this.password);

      // Submit form
      await page.click('button[type="submit"], input[type="submit"]');

      // Wait for either Duo or next page
      await page.waitForLoadState('networkidle');
    } catch (error) {
      throw new Error(`Login failed: ${error.message}`);
    }
  }

  async handleDuoAuth(page) {
    try {
      // Check if Duo iframe is present
      const duoFrame = await page
        .waitForSelector('iframe[id*="duo"], iframe[src*="duosecurity"]', {
          timeout: 5000,
        })
        .catch(() => null);

      if (duoFrame) {
        console.log('🔒 Duo MFA detected - manual approval required');
        console.log('📱 Please approve the authentication on your device...');

        // Wait for Duo to complete (up to 2 minutes)
        await page.waitForFunction(
          () => !document.querySelector('iframe[id*="duo"], iframe[src*="duosecurity"]'),
          { timeout: 120000 }
        );

        console.log('✅ Duo authentication completed');
        await page.waitForLoadState('networkidle');
      } else {
        console.log('ℹ️  No Duo authentication required');
      }
    } catch (error) {
      throw new Error(`Duo authentication failed: ${error.message}`);
    }
  }

  async navigateToSchoology(page) {
    try {
      // Look for Schoology app tile or direct link
      const schoologySelectors = [
        'a[href*="schoology"]',
        '.app-tile[title*="Schoology"]',
        '.application-tile[title*="Schoology"]',
        'div[title*="Schoology"] a',
      ];

      let schoologyLink = null;
      for (const selector of schoologySelectors) {
        schoologyLink = await page.$(selector);
        if (schoologyLink) break;
      }

      if (!schoologyLink) {
        // Try to find "See All Apps" or similar
        const allAppsSelector = 'a[href*="app"], button:has-text("See All")';
        const allAppsButton = await page.$(allAppsSelector);
        if (allAppsButton) {
          await allAppsButton.click();
          await page.waitForLoadState('networkidle');

          // Try again to find Schoology
          for (const selector of schoologySelectors) {
            schoologyLink = await page.$(selector);
            if (schoologyLink) break;
          }
        }
      }

      if (!schoologyLink) {
        throw new Error('Schoology application not found in portal');
      }

      // Click Schoology link
      await schoologyLink.click();
      await page.waitForLoadState('networkidle');

      // Handle potential Google authentication
      await this.handleGoogleAuth(page);
    } catch (error) {
      throw new Error(`Schoology navigation failed: ${error.message}`);
    }
  }

  async handleGoogleAuth(page) {
    // Check if we're on a Google authentication page
    if (page.url().includes('accounts.google.com')) {
      console.log('🔐 Google authentication detected...');

      // This would typically be auto-filled or require additional handling
      // For Phase 1, we'll just wait for manual completion
      console.log('⏳ Waiting for Google authentication to complete...');
      await page.waitForFunction(() => !window.location.href.includes('accounts.google.com'), {
        timeout: 60000,
      });

      await page.waitForLoadState('networkidle');
      console.log('✅ Google authentication completed');
    }
  }

  async scrapeCourseData(page, studentName) {
    try {
      // Wait for Schoology to load
      await page.waitForSelector('.course-title, .course-name, h2', { timeout: 10000 });

      const scrapedData = {
        scrape_timestamp: new Date().toISOString(),
        student: studentName || 'Unknown Student',
        courses: [],
      };

      // Look for courses dropdown or navigation
      const coursesSelector = '[href*="courses"], .courses-dropdown, nav a:has-text("Courses")';
      const coursesLink = await page.$(coursesSelector);

      if (coursesLink) {
        await coursesLink.click();
        await page.waitForLoadState('networkidle');
      }

      // Find all course links
      const courseSelectors = [
        '.course-item a',
        '.course-title a',
        '.course-card a',
        'a[href*="/course/"]',
      ];

      let courseLinks = [];
      for (const selector of courseSelectors) {
        courseLinks = await page.$$(selector);
        if (courseLinks.length > 0) break;
      }

      console.log(`📚 Found ${courseLinks.length} courses`);

      // Scrape all courses found
      const maxCourses = courseLinks.length;
      for (let i = 0; i < maxCourses; i++) {
        try {
          console.log(`📖 Scraping course ${i + 1}/${maxCourses}...`);
          const courseData = await this.scrapeSingleCourse(page, i);
          if (courseData) {
            scrapedData.courses.push(courseData);
          }
        } catch (error) {
          console.warn(`⚠️  Failed to scrape course ${i + 1}: ${error.message}`);
        }
      }

      return scrapedData;
    } catch (error) {
      throw new Error(`Course data scraping failed: ${error.message}`);
    }
  }

  async scrapeSingleCourse(page, courseIndex) {
    // This is a simplified implementation for Phase 1
    // In reality, we'd need to navigate to each course's grade book

    return {
      schoology_id: `course_${courseIndex + 1}`,
      name: `Sample Course ${courseIndex + 1}`,
      teacher: 'Sample Teacher',
      semester: 'Fall 2024',
      assignments: [
        {
          schoology_id: `assign_${courseIndex + 1}_1`,
          name: `Assignment ${courseIndex + 1}.1`,
          category: 'work_product',
          category_weight: 55,
          due_date: new Date(Date.now() + 86400000 * (courseIndex + 1)).toISOString(),
          assigned_date: new Date(Date.now() - 86400000 * 7).toISOString(),
          points_possible: 100,
          points_earned: null,
          status: 'missing',
          raw_display: 'Missing',
          can_be_resubmitted: true,
        },
      ],
    };
  }

  async saveScrapedData(data, studentName) {
    await this.ensureOutputDir();

    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `scrape_${studentName || 'test'}_${timestamp}.json`;
    const filepath = path.join(this.outputDir, filename);

    await fs.writeFile(filepath, JSON.stringify(data, null, 2));
    console.log(`💾 Data saved to: ${filepath}`);

    return filepath;
  }
}

// CLI execution
async function main() {
  const yargs = require('yargs/yargs');
  const { hideBin } = require('yargs/helpers');

  const argv = yargs(hideBin(process.argv))
    .option('student', {
      alias: 's',
      type: 'string',
      description: 'Specific student name to scrape data for',
    })
    .option('headless', {
      type: 'boolean',
      default: true,
      description: 'Run browser in headless mode',
    })
    .option('output-dir', {
      alias: 'o',
      type: 'string',
      description: 'Directory to save scraped JSON files',
      default: process.env.OUTPUT_DIR || '../data/scraped',
    })
    .option('timeout', {
      alias: 't',
      type: 'number',
      default: 30000,
      description: 'Timeout in milliseconds for page operations',
    })
    .option('remote-debug', {
      alias: 'd',
      type: 'boolean',
      default: false,
      description: 'Enable Chrome remote debugging (accessible from remote machine)',
    })
    .option('debug-port', {
      type: 'number',
      default: 9222,
      description: 'Port for Chrome remote debugging',
    })
    .help()
    .alias('help', 'h')
    .version('0.1.0').argv;

  try {
    const scraper = new DPSScraper({
      headless: argv.headless,
      outputDir: argv.outputDir,
      timeout: argv.timeout,
      remoteDebugging: argv.remoteDebug,
      debuggingPort: argv.debugPort,
    });

    await scraper.scrapeGrades(argv.student);
    process.exit(0);
  } catch (error) {
    console.error('💥 Scraper failed:', error.message);
    process.exit(1);
  }
}

// Run if called directly
if (require.main === module) {
  main();
}

module.exports = { DPSScraper };
