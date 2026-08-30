# ControlPlane.ai

ControlPlane.ai is an enterprise AI runtime control layer that intercepts,
evaluates, and governs AI-generated responses before they reach the end user.
It evaluates prompts and AI responses for semantic risks, bias, privacy
violations, and required verification depths based on customizable policies.

This project includes both a FastAPI backend decision engine and a React-based
frontend User/Admin interface designed to demonstrate the safety controls
during the hackathon.

## Table of contents

- Requirements
- Recommended modules
- Installation
- Configuration
- Troubleshooting
- FAQ

## Requirements

This project requires the following software to work:

- [Python](https://www.python.org/) (3.10 or higher)
- [Node.js](https://nodejs.org/) (18.x or higher)

## Recommended modules

The project does not require any optional modules beyond its declared backend
and frontend dependencies. [React Markdown](https://www.npmjs.com/package/react-markdown)
may be used for rendering rich verified responses safely in the frontend.

## Installation

To install and run the project locally, follow these steps:

1. Navigate to the project root directory.
1. Install backend dependencies by running `pip install -r requirements.txt`.
1. Copy the `.env.example` file to `.env` and configure your Gemini API key.
1. Navigate to the `frontend` directory.
1. Install frontend dependencies by running `npm install`.

## Configuration

1. Start the backend server by running `python -m uvicorn backend.main:app --reload`
   from the project directory. The backend will run on port 8000.
1. Start the frontend development server by running `npm run dev` from the
   `frontend` directory. The frontend will be available at port 5173.
1. Ensure `DEMO_SAFE_MODE=true` is set in your environment if you need
   graceful degradation during provider outages.

## Troubleshooting

If the application fails to start or process requests, check the following:

- Is your Gemini API key correctly set in the `.env` file?
- Is port 8000 or 5173 blocked or occupied by another service?
- If the frontend fails to render Markdown, verify that `@tailwindcss/typography`
  and `react-markdown` were successfully installed via npm.

## FAQ

**Q: Can I run this without an active Gemini API key?**

**A:** Yes. The application features a fallback mode that will use simulated
safe responses if the provider is temporarily unavailable or rate-limited,
provided `DEMO_SAFE_MODE` is active.

**Q: How does the AI Judge work?**

**A:** The AI Judge performs a secondary semantic verification check on the
primary LLM's response. If it detects a violation of policy or bias, the
decision engine automatically escalates the action to human review.
