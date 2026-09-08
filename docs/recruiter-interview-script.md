# Recruiter Demo Script

This script is designed for a 5-minute walkthrough of Research Bridge AI during technical interviews or portfolio reviews.

## Setup
1. Ensure the stack is running locally (`docker compose up -d`).
2. Open `http://localhost:3000` in a clean browser window.

## The Walkthrough

### 1. Introduction (0:00 - 1:00)
> *"Research Bridge AI is a platform I built to solve a specific problem: finding verifiable research opportunities and sending evidence-backed outreach to professors. The core principle of the application is **evidence before generation**—the AI is not allowed to invent facts."*

- Navigate to `/login` and sign in (or click "View Demo" to use the deterministic fallback data).

### 2. Discovery & Ranking (1:00 - 2:30)
> *"Let's say I'm looking for research in computational biology. I'll enter that into the discovery tool."*

- Type "Computational Biology" into the discovery search bar and click **Find Mentors**.
- Wait for the results to stream in.
> *"The backend uses FastAPI to query the OpenAlex API concurrently. Notice how fast it is. Instead of using a black-box LLM to rank these professors, it uses a deterministic heuristic based on four explicit factors: query evidence, profile alignment, supporting depth, and recent activity."*
- Click on a mentor to expand their evidence panel.
> *"Every claim here is backed by a specific paper or institution ID. There's no hallucination."*

### 3. Evidence-Grounded Outreach (2:30 - 4:00)
- Select 1 or 2 papers from the mentor's evidence list.
- Click **Generate Outreach Draft**.
> *"Now we use an LLM via LangGraph. But because of our strict architecture rules, the LLM is only given the verified JSON metadata of the professor and the papers we selected. It's prompted to draft an email that explicitly cites this evidence."*
- Show the generated draft.
> *"Notice the editor. The draft is generated, but the system will **never** send an email automatically. Human approval is an explicit architectural boundary."*

### 4. Technical Architecture (4:00 - 5:00)
- Briefly show the `docker-compose.yml` or GitHub Actions pipeline.
> *"Under the hood, this is a Next.js App Router frontend and a FastAPI backend using SQLAlchemy, async HTTPX, and Redis for rate limiting. The entire stack is heavily tested with Pytest and Playwright E2E tests, including automated axe-core accessibility audits on every commit."*

## Expected Questions
- **Why not use LangChain instead of LangGraph?** *LangGraph provides explicit state-machine control, allowing for human-in-the-loop pauses (like waiting for paper selection).*
- **How do you handle rate limits from OpenAlex?** *The backend uses HTTPX with bounded retries, exponential backoff, and a process-local cache.*
- **What happens if OpenAI goes down?** *The system falls back to a deterministic string-template generation, so the user can still get a functional draft.*
