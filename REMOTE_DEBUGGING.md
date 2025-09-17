# Remote Browser Debugging for Grade Guardian

## Overview

The Grade Guardian scraper supports Chrome remote debugging, allowing you to control and inspect a headless browser running on a remote server from your local Windows machine.

## Setup

### 1. SSH Port Forwarding (Recommended)

Since Chrome debugging may bind to localhost only, use SSH port forwarding:

```bash
# On Windows, set up port forwarding in your SSH connection
ssh -L 9222:localhost:9222 user@<server_ip>

# Then access via: http://localhost:9222 on Windows
```

### 2. Run Scraper with Remote Debugging

```bash
# Direct execution (after installing Playwright deps)
DPS_USERNAME=your_username DPS_PASSWORD="your_password" node dps_scraper.js --student=StudentName --remote-debug

# Or via Docker (future implementation)
docker-compose run --rm scraper --student=StudentName --remote-debug
```

### 2. Connect from Windows Machine

Once the scraper starts, you'll see:
```
🔍 Remote debugging enabled on 0.0.0.0:9222
   Connect from Windows: http://<server_ip>:9222
   Access DevTools: chrome://inspect or direct URL
```

### 3. Access Methods

**Method A: Direct URL**
- Open Chrome on Windows
- Navigate to: `http://<server_ip>:9222`
- Click on the page you want to inspect

**Method B: Chrome DevTools**
- Open Chrome on Windows
- Go to: `chrome://inspect`
- Add network target: `<server_ip>:9222`
- Click "inspect" on the discovered page

## Usage

### Debugging DPS Login Issues
1. Start scraper with `--remote-debug`
2. Connect from Windows when you see the debugging URL
3. Watch real-time page navigation
4. Inspect elements to find correct selectors
5. Handle Duo authentication manually if needed

### Available Commands

```bash
# Basic remote debugging
node dps_scraper.js --remote-debug --student=StudentName

# Custom debug port
node dps_scraper.js --remote-debug --debug-port=9223 --student=StudentName

# With custom timeout (useful for manual Duo approval)
node dps_scraper.js --remote-debug --timeout=300000 --student=StudentName
```

## Troubleshooting

### Port Access
- Ensure port 9222 is accessible from Windows to Linux server
- Check firewall rules if connection fails
- Verify server IP address

### Duo Authentication
- Remote debugging allows manual Duo approval
- Browser will pause during MFA steps
- Complete authentication in the remote browser
- Scraper will continue automatically

### Screenshots
- Error screenshots are still saved to `data/scraped/error_*.png`
- Useful for debugging even with remote access

## Development Workflow

1. **Start with remote debugging** to understand page structure
2. **Inspect elements** to find correct selectors
3. **Test authentication flow** manually
4. **Update selectors** in scraper based on findings
5. **Run without debugging** for automated execution

## Security Notes

- Remote debugging exposes browser control interface
- Only use on trusted networks
- Port 9222 should not be exposed to internet
- Disable debugging for production runs
