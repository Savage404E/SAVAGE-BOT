# SAVAGE Discord Bot Website

A modern, gaming-themed website for the SAVAGE Discord Bot built with React, Vite, and TailwindCSS.

## Features

- **Gaming Theme**: Clean, modern dark theme with purple accents
- **Responsive Design**: Works on all devices
- **Hero Section**: Eye-catching introduction with bot statistics
- **Features Showcase**: Highlights pet system, dungeons, economy, and more
- **Server Stats**: Displays 400+ bot users and 17K+ server members
- **Call-to-Action**: Join server buttons and links

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

## Customization

### Update Discord Invite Link

Replace `https://discord.gg/your-invite-link` in `src/App.jsx` with your actual Discord server invite link.

### Update Statistics

Modify the stats in the hero section of `src/App.jsx`:
- Bot Users
- Server Members
- Mini Games
- Uptime

### Customize Colors

Edit `tailwind.config.js` to change the color scheme:
- `savage-dark`: Background color
- `savage-purple`: Primary purple
- `savage-purplelight`: Light purple accent
- `savage-accent`: Accent color

## Tech Stack

- **React 18**: UI framework
- **Vite**: Build tool and dev server
- **TailwindCSS**: Utility-first CSS framework
- **Lucide React**: Icon library

## Project Structure

```
website of savage/
├── index.html
├── package.json
├── vite.config.js
├── tailwind.config.js
├── postcss.config.js
└── src/
    ├── main.jsx
    ├── App.jsx
    └── index.css
```

## License

© 2024 SAVAGE Discord Bot. All rights reserved.
