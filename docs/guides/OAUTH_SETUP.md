# AniList OAuth Setup Guide

This guide explains how to set up AniList OAuth authentication for the Eastern Tales Shelf application.

## 1. Register an AniList API Client

1. Go to [AniList Developer Settings](https://anilist.co/settings/developer)
2. Click on "Create Client"
3. Fill in the required information:
   - **Name**: Eastern Tales Shelf
   - **Redirect URL**: The callback URL where AniList will redirect after authentication
     - For local development: `http://localhost:5000/auth/anilist/callback`
     - For production: `https://your-domain.com/auth/anilist/callback`

4. After creating the client, you'll receive a **Client ID** and **Client Secret**

## 2. Configure Environment Variables

Add the following environment variables to your `.env` file or environment:

```
ANILIST_CLIENT_ID=your_client_id
ANILIST_CLIENT_SECRET=your_client_secret
ANILIST_REDIRECT_URI=http://localhost:5000/auth/anilist/callback
ANILIST_REDIRECT_URI_LOCAL=http://localhost:5001/auth/anilist/callback
```

## 3. Run Database Migration

Run the migration script to update your database schema:

```
python migrate_users_table.py
```

This will add the necessary columns to the `users` table to support OAuth authentication.

## 4. Privacy-First Authentication Approach

Eastern Tales Shelf uses a privacy-first approach to AniList authentication, giving users two options:

### Privacy Mode (Default)
- We authenticate the user with AniList
- We collect only basic profile information (username, avatar)
- We DO NOT store the user's access token
- Features that require persistent API access to AniList will be unavailable

### Enhanced Features Mode (Opt-in)
- We authenticate the user with AniList
- We collect basic profile information
- We DO store the user's access token securely in our database
- This enables personalized features like notifications and AniList list syncing

Users can explicitly choose which mode they prefer during login.

## 5. How the Authentication Flow Works

1. User selects either Privacy Mode or Enhanced Features login
2. User is redirected to AniList's authorization page
3. User authorizes the application on AniList
4. AniList redirects back to the callback URL with an authorization code
5. The application exchanges the code for an access token
6. The application uses the token to fetch the user's information
7. Depending on the user's choice:
   - Privacy Mode: Token is used for the current session only and not stored in the database
   - Enhanced Features: Token is securely stored for ongoing use

## 6. In-Depth Explanation of OAuth 2.0

### What is OAuth 2.0?

OAuth 2.0 is an authorization framework that enables a third-party application to obtain limited access to a user's account on another service. It works by delegating user authentication to the service that hosts the user account and authorizing third-party applications to access that account.

### Security Aspects

OAuth 2.0 is highly secure when implemented correctly. Here's why:

1. **No Password Sharing**: The user never shares their AniList password with our application. They log in directly with AniList.

2. **Limited Access**: The access token has limited scope and can be restricted to only access specific data.

3. **State Parameter**: The state parameter prevents Cross-Site Request Forgery (CSRF) attacks by ensuring the request and callback are part of the same session.

4. **Client Secret Security**: The client secret never leaves our server, protecting it from exposure.

5. **HTTPS**: All OAuth communications should use HTTPS to prevent man-in-the-middle attacks.

6. **Token Security**: When stored, the access token is kept securely in the database and never exposed to client-side code.

## 7. Security Considerations

- The state parameter is used to prevent CSRF attacks
- Access tokens are stored securely in the database only with explicit user consent
- User data is validated before being stored
- We never store or have access to user passwords
- Client secrets are kept secure on the server

## 8. Understanding AniList OAuth Permissions

### AniList's OAuth Implementation

AniList does not support scopes in their OAuth implementation, which means when a user authorizes our application, the access token granted has full permissions to the user's account. Unlike other OAuth providers (like GitHub or Google), there's no way to request limited access.

This is why we've implemented our privacy-first approach:
1. By default, we don't store the token, limiting what we can do with the user's account
2. Only users who explicitly opt-in to enhanced features have their tokens stored

### What This Means for Users

1. **Privacy Mode - What We Can Do**:
   - Identify who you are (username, profile picture)
   - Use your identity for login purposes
   - Session-only access to your data

2. **Enhanced Features - What We Can Do**:
   - Everything in Privacy Mode, plus:
   - Access your AniList data for personalized features
   - Fetch your notifications
   - Sync your manga/anime list changes

3. **What We NEVER Do (Regardless of Mode)**:
   - Post or comment on your behalf without explicit action
   - Follow/unfollow users
   - Change your profile information
   - Share your data with third parties

### Our Privacy Commitment

Even though AniList's OAuth implementation grants full access tokens, our application is designed with strict self-imposed limitations:

1. We only use the minimum functionality needed for the app to work
2. We provide clear options so users know exactly what they're authorizing
3. All code handling tokens is open source and can be reviewed

## 9. Troubleshooting

If you encounter issues with the OAuth login:

- Check that your Client ID and Client Secret are correctly set
- Verify the Redirect URL matches exactly what's registered on AniList
- Check the Flask logs for detailed error messages
- Ensure environment variables are properly set
- Confirm that your AniList developer app is approved and active 