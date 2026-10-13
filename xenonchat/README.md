# XenonChat

A responsive messaging interface built with Vite, React, and TypeScript. It starts with a private empty inbox and requires authentication before messaging access is available.

## Getting Started

```bash
npm install
npm run dev
```

Open the local URL printed by Vite. For a production build:

```bash
npm run build
npm run preview
```

## Windows App

Install the desktop dependencies and build the Windows installer and portable executable:

```bash
npm install
npm run desktop:build
```

The output is written to `release/`. The same `dist/` build can be deployed to any static host for online access.

## Secure Authentication

XenonChat does not expose the inbox or composer until Firebase Authentication confirms a signed-in user. It supports Google OAuth and email/password accounts. Copy `.env.example` to `.env.local`, fill in the Firebase web app values, and enable Google and Email/Password providers in Firebase Authentication.

Create a Firestore database in Firebase Console before using **New conversation**. The app stores signed-in user profiles in `users/{uid}` and checks that the recipient email belongs to a registered user. Apply the included `firestore.rules` when configuring the database.

```bash
copy .env.example .env.local
```

Never commit `.env.local` or its values. The Firebase web configuration is safe to use in a frontend when the authorized domains and provider settings are configured in Firebase Console.

## GitHub Pages

The included GitHub Actions workflow deploys the `dist` build on every push to `main`. In the repository settings, set **Pages → Source** to **GitHub Actions**, then add the six `VITE_FIREBASE_*` values from `.env.local` as repository Actions secrets. Add your GitHub Pages domain to Firebase Authentication's authorized domains.

## Included

- Searchable conversation list with unread counts
- Online and offline presence states
- Responsive mobile conversation navigation
- Local message composer with Enter-to-send
- Mock delivery and read states
- Accessible icon buttons and form controls
