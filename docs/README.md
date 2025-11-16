# TON Connect Manifest - GitHub Pages

This directory contains files served via GitHub Pages for TON Connect integration.

## Files

- **`index.html`** - Landing page with bot information
- **`tonconnect-manifest.json`** - TON Connect manifest file (required for wallet integration)
- **`icon-180x180.png`** - Bot icon (180x180 pixels, PNG format)
- **`.nojekyll`** - Disables Jekyll processing for proper JSON serving

## Live URLs

- **Home Page**: https://f2re.github.io/raffle-telegram-bot/
- **Manifest**: https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json
- **Icon**: https://f2re.github.io/raffle-telegram-bot/icon-180x180.png

## Setup Instructions

See [GITHUB_PAGES_SETUP.md](../GITHUB_PAGES_SETUP.md) for complete setup guide.

## Important Notes

1. **Do NOT delete this folder** - it's required for TON Connect to work
2. **Keep manifest in sync** - when updating `tonconnect-manifest.json` in root, copy to `docs/`
3. **Icon required** - add `icon-180x180.png` (180x180 pixels, PNG format)

## Testing

Verify manifest is accessible:
```bash
curl https://f2re.github.io/raffle-telegram-bot/tonconnect-manifest.json
```

Should return valid JSON without errors.
