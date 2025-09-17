# Google Sheets Auto-Updater

Automatically updates Google Sheets with scraped signature counts from Change.org petitions every 2 minutes using GitHub Actions.

## Files Structure

```
├── main.py                    # Main script
├── token.pickle              # Google OAuth token (auto-generated)
├── credentials.json          # Google OAuth credentials (you provide)
├── requirements.txt          # Python dependencies
├── .github/workflows/        # GitHub Actions workflow
│   └── update-sheets.yml     # Automated execution every 2 minutes
└── README.md                 # This file
```

## Setup Instructions

### 1. Google OAuth Setup
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google Sheets API
4. Create credentials (OAuth 2.0 Client ID)
5. Download the credentials JSON file
6. Save it as `credentials.json` in this repository

### 2. GitHub Repository Setup
1. Push all files to your GitHub repository
2. The workflow will automatically run every 2 minutes
3. You can also trigger it manually from the Actions tab

### 3. First Run
- The first time the workflow runs, it will need to authenticate
- You'll need to manually run the script once locally to generate the initial `token.pickle`
- Then commit and push the `token.pickle` file to GitHub

## Manual Execution

```bash
# Check token status
python main.py --check-token

# Run the updater
python main.py

# Run with custom spreadsheet URL
python main.py --csv-url "your-spreadsheet-url"
```

## GitHub Actions

The workflow runs every 2 minutes and:
- Installs Python dependencies
- Sets up Chrome and ChromeDriver for Selenium
- Runs the main script
- Updates your Google Sheets automatically

## Token Management

The script automatically handles token refresh, so you don't need to re-authenticate manually. The token will be refreshed automatically when it expires.
