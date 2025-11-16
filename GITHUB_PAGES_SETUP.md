# GitHub Pages Setup Guide for TON Connect Manifest

This guide explains how to publish your TON Connect manifest using GitHub Pages for **@tonrafflebest_bot**.

## What is TON Connect Manifest?

The TON Connect manifest (`tonconnect-manifest.json`) is a configuration file that allows TON wallets to identify and securely connect to your Telegram bot. It must be publicly accessible via HTTPS.

## Why GitHub Pages?

- **Free hosting** - No cost for public repositories
- **HTTPS enabled** - Required for TON Connect
- **Automatic deployment** - Push to GitHub, get live updates
- **Reliable CDN** - Fast global access via GitHub's infrastructure
- **Simple setup** - No server configuration needed

## Repository Structure

```
raffle-telegram-bot/
├── docs/                           # GitHub Pages root directory
│   ├── index.html                 # Landing page for your manifest
│   ├── tonconnect-manifest.json   # TON Connect manifest file
│   └── icon-180x180.png          # Bot icon (add this file)
├── tonconnect-manifest.json       # Source manifest (in repo root)
└── GITHUB_PAGES_SETUP.md         # This guide
```

## Step-by-Step Setup Instructions

### 1. Enable GitHub Pages

1. Go to your GitHub repository: **https://github.com/f2re/raffle-telegram-bot**
2. Click on **Settings** (⚙️ icon in top menu)
3. Scroll down to **Pages** section in the left sidebar
4. Under **Source**, select:
   - **Branch**: `claude/github-pages-tonraffle-01TRwa4VpLgpvqwghPW1RjGL` (or `main` if merged)
   - **Folder**: `/docs`
5. Click **Save**
6. Wait 1-2 minutes for deployment

### 2. Verify Deployment

After GitHub Pages is enabled, your site will be available at:

```
https://f2re.github.io/raffle-telegram-bot/
```

Verify the manifest is accessible:

```
https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json
```

**Test in browser**: Open the URL above - you should see the JSON content:

```json
{
  "url": "https://t.me/tonrafflebest_bot",
  "name": "TON Raffle Bot",
  "iconUrl": "https://f2re.github.io/raffle-telegram-bot/icon-180x180.png",
  "termsOfUseUrl": "https://t.me/tonrafflebest_bot",
  "privacyPolicyUrl": "https://t.me/tonrafflebest_bot"
}
```

### 3. Add Bot Icon (Important!)

The manifest references an icon at `icon-180x180.png`. You need to add this file:

#### Option A: Use Existing Bot Avatar

1. Get your bot's profile photo from Telegram
2. Resize to **180x180 pixels** (PNG format)
3. Save as `docs/icon-180x180.png`
4. Commit and push:

```bash
git add docs/icon-180x180.png
git commit -m "Add bot icon for TON Connect manifest"
git push -u origin claude/github-pages-tonraffle-01TRwa4VpLgpvqwghPW1RjGL
```

#### Option B: Create a Simple Icon

Use an online tool like:
- **Canva**: https://canva.com (free templates)
- **Figma**: https://figma.com (design tool)
- **Placeholder.com**: https://via.placeholder.com/180x180.png/667eea/ffffff?text=TR (temporary)

Save as `docs/icon-180x180.png` and commit.

#### Option C: Use Placeholder (Temporary)

You can temporarily use a generic icon:

```bash
# Download a placeholder icon
curl -o docs/icon-180x180.png https://via.placeholder.com/180x180.png/667eea/ffffff?text=TON+Raffle

git add docs/icon-180x180.png
git commit -m "Add placeholder icon for TON Connect"
git push -u origin claude/github-pages-tonraffle-01TRwa4VpLgpvqwghPW1RjGL
```

### 4. Update Bot Configuration

Update your `.env` file with the GitHub Pages URL:

```env
# Add or update this line:
TON_CONNECT_MANIFEST_URL=https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json
```

Restart your bot to apply changes:

```bash
docker-compose restart bot
# or if running locally:
# Ctrl+C and then: python app/main.py
```

### 5. Test TON Connect Integration

1. Open your bot: [@tonrafflebest_bot](https://t.me/tonrafflebest_bot)
2. Send `/start` command
3. Click **"💎 Оплатить TON"** or similar button
4. Click **"🔗 Подключить кошелек"**
5. You should see a QR code or connection link
6. Scan with Tonkeeper/MyTonWallet to test connection

## Troubleshooting

### Issue: "Failed to fetch manifest"

**Cause**: Manifest URL is not accessible or returns wrong content-type.

**Solutions**:

1. **Check URL in browser**: Open `https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json`
   - Should return JSON content
   - Should NOT show 404 error

2. **Check GitHub Pages status**:
   - Go to Settings → Pages
   - Look for green checkmark "Your site is published at..."
   - If red X, check deployment logs

3. **Verify file location**:
   ```bash
   ls -la docs/
   # Should show: tonconnect-manifest.json
   ```

4. **Check JSON validity**:
   ```bash
   cat docs/tonconnect-manifest.json | python -m json.tool
   # Should format JSON without errors
   ```

### Issue: Icon not loading in wallet

**Cause**: Icon file is missing or has wrong dimensions.

**Solutions**:

1. **Verify icon exists**:
   ```bash
   ls -la docs/icon-180x180.png
   ```

2. **Check icon URL**: Open `https://f2re.github.io/raffle-telegram-bot/icon-180x180.png`
   - Should display the image

3. **Verify dimensions**:
   ```bash
   file docs/icon-180x180.png
   # Should show: PNG image data, 180 x 180
   ```

### Issue: Changes not appearing

**Cause**: GitHub Pages cache or deployment delay.

**Solutions**:

1. **Wait 2-5 minutes** - GitHub Pages needs time to rebuild

2. **Force refresh browser**:
   - Windows/Linux: `Ctrl + Shift + R`
   - Mac: `Cmd + Shift + R`

3. **Check deployment status**:
   - Go to repository → **Actions** tab
   - Look for "pages build and deployment" workflow
   - Should show green checkmark when complete

4. **Clear browser cache** or test in incognito mode

### Issue: CORS errors in browser console

**Cause**: GitHub Pages doesn't set CORS headers by default.

**Solution**: This is usually fine for TON Connect, but if needed:

1. Add `.nojekyll` file to bypass Jekyll processing:
   ```bash
   touch docs/.nojekyll
   git add docs/.nojekyll
   git commit -m "Disable Jekyll processing"
   git push
   ```

2. Or create `_headers` file in docs folder:
   ```
   /*
     Access-Control-Allow-Origin: *
   ```

## Alternative: Custom Domain (Optional)

If you own a domain, you can use it instead of `f2re.github.io`:

1. Go to repository **Settings → Pages**
2. Under **Custom domain**, enter your domain (e.g., `tonraffle.example.com`)
3. Add DNS records at your domain provider:
   ```
   CNAME record: tonraffle → f2re.github.io
   ```
4. Wait for DNS propagation (5-60 minutes)
5. Update manifest URL in `.env`:
   ```env
   TON_CONNECT_MANIFEST_URL=https://tonraffle.example.com/tonconnect-manifest.json
   ```

## File Maintenance

### Updating the Manifest

If you need to change bot details:

1. **Edit the source file** in repository root:
   ```bash
   nano tonconnect-manifest.json
   ```

2. **Copy to docs folder**:
   ```bash
   cp tonconnect-manifest.json docs/
   ```

3. **Commit and push**:
   ```bash
   git add tonconnect-manifest.json docs/tonconnect-manifest.json
   git commit -m "Update TON Connect manifest"
   git push -u origin claude/github-pages-tonraffle-01TRwa4VpLgpvqwghPW1RjGL
   ```

4. **Wait 2-5 minutes** for GitHub Pages to update

### Keeping Files in Sync

To avoid manual copying, you can create a symbolic link (advanced):

```bash
cd docs
ln -s ../tonconnect-manifest.json tonconnect-manifest.json
git add tonconnect-manifest.json
git commit -m "Link manifest to root file"
git push
```

Or use a pre-commit hook to auto-copy (see `.git/hooks/pre-commit`).

## Security Considerations

### Public Repository

- ✅ **Safe**: Manifest file contains only public information
- ✅ **Safe**: Bot username and icon are already public
- ⚠️ **Warning**: Never commit `.env` file with tokens/secrets!

### HTTPS Requirement

- GitHub Pages automatically provides HTTPS
- TON Connect requires HTTPS (won't work with HTTP)
- Certificate is managed by GitHub (auto-renewed)

### Content Validation

TON wallets will validate your manifest:
- `url` must match your bot's actual Telegram link
- `iconUrl` must be accessible and proper PNG format
- Invalid manifest = connection will fail

## Monitoring

### Check Manifest Accessibility

Create a monitoring script (optional):

```bash
#!/bin/bash
# check-manifest.sh

URL="https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json"

if curl -sf "$URL" > /dev/null; then
    echo "✅ Manifest is accessible"
    curl -s "$URL" | python -m json.tool
else
    echo "❌ Manifest is NOT accessible"
    exit 1
fi
```

Run daily via cron:
```cron
0 9 * * * /path/to/check-manifest.sh
```

### GitHub Pages Status

GitHub provides status page:
- https://www.githubstatus.com/
- Subscribe to notifications for Pages incidents

## Next Steps

After setting up GitHub Pages:

1. ✅ **Test the integration**: Connect a wallet and verify it works
2. ✅ **Update documentation**: Add manifest URL to `TON_CONNECT_GUIDE.md`
3. ✅ **Monitor logs**: Check bot logs for TON Connect errors
4. ✅ **Inform users**: Announce TON Connect support in bot messages

## Resources

- **TON Connect Documentation**: https://docs.ton.org/develop/dapps/ton-connect
- **GitHub Pages Docs**: https://docs.github.com/pages
- **Manifest Specification**: https://github.com/ton-connect/docs/blob/main/requests-responses.md#app-manifest
- **pytonconnect SDK**: https://github.com/XaBbl4/pytonconnect

## Support

If you encounter issues:

1. **Check bot logs**: `docker-compose logs -f bot`
2. **Test manifest URL**: Open in browser and verify JSON is valid
3. **Review TON Connect guide**: See `TON_CONNECT_GUIDE.md` in repo
4. **GitHub Issues**: Report problems at repository issues page

---

**Summary**: Your TON Connect manifest is now publicly accessible at:
```
https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json
```

Don't forget to:
1. ✅ Add `icon-180x180.png` to docs folder
2. ✅ Update `.env` with manifest URL
3. ✅ Enable GitHub Pages in repository settings
4. ✅ Test TON Connect integration with real wallet

Good luck with your raffle bot! 🎲🚀
