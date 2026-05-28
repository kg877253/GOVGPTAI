# GitHub Push Instructions for GovGPT AI

## Step 1: Initialize Git Repository (if not already done)

```bash
cd "c:\Users\kg877\GOVGPT AI"
git init
```

## Step 2: Create .gitignore (if not exists)

The `.gitignore` file should already exist and contain:
```
.env
chroma_db/
logs/
*.log
__pycache__/
*.pyc
.DS_Store
```

## Step 3: Add All Files

```bash
git add .
```

## Step 4: Commit Changes

```bash
git commit -m "Initial commit: GovGPT AI - RTI Application Generator"
```

## Step 5: Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `govgpt-ai` (or your preferred name)
3. Description: "AI-powered RTI application generator for Indian citizens"
4. Make it **Public** (for demo purposes)
5. **DO NOT** initialize with README (you already have one)
6. Click "Create repository"

## Step 6: Add Remote Origin

```bash
git remote add origin https://github.com/YOUR_USERNAME/govgpt-ai.git
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 7: Push to GitHub

```bash
git branch -M main
git push -u origin main
```

## Step 8: Verify

Go to your GitHub repository and verify all files are uploaded.

## Important Notes

- **NEVER commit `.env` file** - it contains API keys
- The `.gitignore` file already prevents this
- If you accidentally committed `.env`, remove it:
  ```bash
  git rm --cached .env
  git commit -m "Remove .env from git"
  git push
  ```

## For Future Updates

```bash
# After making changes
git add .
git commit -m "Your commit message"
git push
```

## Deployment (Optional)

For deployment to Render.com or similar platforms:
1. Connect your GitHub repository
2. Set environment variables in the platform settings:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `GROQ_API_KEY`: Your Groq API key (optional)
   - `AUTO_INGEST`: 0 or 1
3. Deploy

## Current Project Status

- ✅ Server running on http://localhost:5000
- ✅ PDF generation using displayed content
- ✅ Multi-provider support (Gemini + Groq)
- ✅ Auto-fill address/department
- ✅ Works for all RTI types
- ✅ Professional UI
- ✅ Comprehensive error handling
