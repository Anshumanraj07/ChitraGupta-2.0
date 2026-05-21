# ChitraGupta 👁️
**Mind & Action Observer | Agentic AI Ledger**

ChitraGupta is an autonomous AI-driven personal assistant built to bridge the gap between unstructured thoughts and structured execution. It processes raw inputs and intelligently routes them as either actionable tasks or analytical journal entries.

## 🚀 Key Features
- **Agentic Routing:** Uses Llama-3.1-8b via Groq to categorize inputs into 'Tasks' or 'Journals' with 100% JSON schema enforcement.
- **Cross-Platform Logging:** Seamlessly log thoughts via a responsive web dashboard or a private Telegram bot.
- **Autonomous Breakdown:** Automatically generates actionable sub-tasks and execution tips for every logged item.
- **Secure Architecture:** Hard-locked user ID routing with strict PostgreSQL Row-Level Security (RLS) via Supabase.
- **Karma Analysis:** AI-powered analytical insights based on your recent task focus and journal entries.

## 🛠 Tech Stack
- **Backend:** FastAPI (Python)
- **AI Engine:** Llama-3.1-8b (Groq API)
- **Database:** Supabase (PostgreSQL)
- **Frontend:** HTML5, Tailwind CSS
- **Integration:** Telegram Bot API (Webhooks)

## 🏗 System Architecture
1. **Input Layer:** Receives input via Telegram or Web UI.
2. **Brain Layer:** Groq API processes the input, extracts intent, and enforces a strict JSON structure.
3. **Storage Layer:** Supabase handles data persistence with RLS-protected rows.
4. **Analysis Layer:** Aggregates recent activity to provide a "Karma Analysis" insight.

## 📦 Getting Started
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Set your `.env` variables:
   - `SUPABASE_URL`
   - `SUPABASE_KEY` (Service Role for backend)
   - `GROQ_API_KEY`
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `MASTER_USER_ID`
4. Deploy to Render/Railway using the `Procfile`.

---
*Built by [Anshuman Raj] - Undergraduate student in Computer Science and AI.*
