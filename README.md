# SAVAGE Discord Bot Website

A modern, gaming-themed website for the SAVAGE Discord Bot built with React and Vite.

## Features

- **Gaming Theme**: Clean, modern dark theme with purple accents
- **Responsive Design**: Works on all devices
- **Hero Section**: Eye-catching introduction with animated gradient text
- **Features Showcase**: Highlights pet system, dungeons, economy, and 20+ mini-games
- **Game Pictures**: Visual showcase of Card RNG, Clan Teams, Dungeon Fights, and Pet Lovers
- **Server Stats**: Displays 400+ bot users and 17K+ server members
- **Call-to-Action**: Join server buttons and links
- **Background GIFs**: Animated backgrounds for hero, features, and CTA sections

## Setup Instructions

1. **Install Dependencies**
   ```bash
   npm install
   ```

2. **Start Development Server**
   ```bash
   npm run dev
   ```

3. **Build for Production**
   ```bash
   npm run build
   ```

4. **Preview Production Build**
   ```bash
   npm run preview
   ```

## Deployment to GitHub Pages

This project uses GitHub Actions for automatic deployment to GitHub Pages.

### Manual Deployment

1. Push changes to GitHub
2. GitHub Actions automatically builds and deploys
3. Site is available at: `https://your-username.github.io/your-repo/`

### Required Files

Ensure these files are uploaded to GitHub:
- `vite.config.js` (configured with base path)
- `.github/workflows/static.yml` (GitHub Actions workflow)
- `public/` folder (contains all GIF and PNG images)

## Customization

### Update Discord Invite Link

Replace `https://discord.gg/besavage` in `src/App.jsx` with your actual Discord server invite link.

### Update Statistics

Modify the stats in the hero and CTA sections of `src/App.jsx`:
- Bot Users
- Server Members
- Mini Games
- AURA Badge
- Daily Rewards

### Customize Images

Add your own GIF and PNG images to the `public/` folder:
- `hero-bg.gif` - Hero section background
- `wall-bg.gif` - Features section background
- `door-bg.gif` - CTA section background
- `card-rng.png` - Card RNG game picture
- `clan.png` - Clan Teams game picture
- `dungeon.png` - Dungeon Fights game picture
- `pets.png` - Pet Lovers game picture

## Tech Stack

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **Inline Styles**: CSS styling for reliability
- **Emojis**: Icon replacements for better compatibility
- **GitHub Actions**: Automated deployment

## Project Structure

```
website of savage/
├── index.html
├── package.json
├── vite.config.js
├── postcss.config.js
├── .github/
│   └── workflows/
│       └── static.yml
├── public/
│   ├── hero-bg.gif
│   ├── wall-bg.gif
│   ├── door-bg.gif
│   ├── card-rng.png
│   ├── clan.png
│   ├── dungeon.png
│   └── pets.png
└── src/
    ├── main.jsx
    ├── App.jsx
    └── index.css
```

## License

© 2024 SAVAGE Discord Bot. All rights reserved.
