#!/bin/bash
#
# Alloy - Context Generation Script v1
# This script gathers all relevant source code from the backend and web,
# then appends an updated architectural prompt and directory trees to create a comprehensive context file.
#

echo "--- Generating complete context for Alloy ---"

# --- Step 1: Clear previous context for a fresh start ---
echo "[1/4] Clearing old context file..."
> claude_context.txt

# --- Step 2: Append Backend Source (Python/FastAPI) ---
echo "[2/4] Appending backend source files (*.py)..."
find backend/src -name "*.py" -exec sh -c '
  echo "File: {}" >> claude_context.txt && cat {} >> claude_context.txt && echo -e "\n-e\n" >> claude_context.txt
' \;
find backend/tests -name "*.py" -exec sh -c '
  echo "File: {}" >> claude_context.txt && cat {} >> claude_context.txt && echo -e "\n-e\n" >> claude_context.txt
' \;

# --- Step 3: Append Web App Source (Next.js/React) ---
echo "[3/4] Appending web source files (*.ts, *.tsx)..."
find web/src -type f \( -name "*.ts" -o -name "*.tsx" \) -exec sh -c '
  echo "File: $1" >> claude_context.txt && cat "$1" >> claude_context.txt && echo -e "\n-e\n" >> claude_context.txt
' sh {} \;

# --- Step 4: Append Directory Trees & Final Prompt ---
echo "[4/4] Appending directory trees and project prompt..."
{
  echo "--- DIRECTORY TREES ---"
  echo ""
  echo "Backend Tree:"
  tree backend/src
  echo ""
  echo "Backend Tests Tree:"
  tree backend/tests
  echo ""
  echo "Web App Tree:"
  tree web/src
  echo ""
  echo "-----------------------"
  echo ""
} >> claude_context.txt

# Append your startup context at the bottom
cat <<'EOT' >> claude_context.txt
Project Context: Alloy - The Cultural Due Diligence Platform

Core Concept: A financial-grade intelligence platform for M&A, VC, and corporate strategy firms that de-risks multi-billion dollar acquisitions by replacing executive "gut feeling" with a data-driven "Cultural Compatibility Score."

System Architecture: Two-Part System

The project is composed of two distinct but interconnected components:

1. FastAPI Backend (backend):

Role: The "Intelligence & Qloo Engine." This is the core brain of the operation.

Function:
- Its primary responsibility is to receive an authenticated request with two brand names (an Acquirer and a Target).
- It makes foundational, parallel calls to the Qloo Taste AI™ API to retrieve the complete, raw cultural taste profiles for both brand audiences. This is the "Source of Truth."
- It then processes this rich Qloo data to generate the core analytical modules: an Affinity Overlap score, a Culture Clash "red flag" report, and an Untapped Growth opportunities map.
- In the final step, it feeds ONLY the raw Qloo cultural affinity lists (e.g., top 50 movies, books, artists) to a Large Language Model, tasking it to act as an expert brand strategist and deduce the "Brand Archetype" from the data alone.
- It is entirely stateless, relying on JWTs for authentication.

Endpoints: A primary `/v1/report/create` for generating the analysis, and robust OAuth2 endpoints (`/auth/...`) for user management.

2. Next.js Web App (web):

Role: The "Executive Dashboard & Command Center." This is the user-facing application.

Function:
- Handles user signup, login (via OAuth against the FastAPI backend), and future billing/settings.
- Provides a clean, professional interface for users to input the two brands they wish to analyze.
- Its most critical function is to receive the complete JSON report from the backend and render it into a stunning, multi-module, interactive dashboard. This includes data visualizations like Venn diagrams for overlap, comparison tables for clashes, and strategic summaries.
- It guides the user through the data story, turning complex cultural intelligence into clear, actionable business insights.

User Experience & Core Loop:

1. Onboarding: An analyst from a VC firm signs up and logs in via the web app's secure OAuth flow.
2. Core Action: From their dashboard, they create a new analysis, entering "Disney" as the Acquirer and "A24 Films" as the Target, then click "Generate Report."
3. Processing: The frontend shows a professional loading state, indicating that deep analysis is underway ("Analyzing Taste DNA... Synthesizing Thesis...").
4. The Reveal: The complete, multi-part "Alloy Report" is displayed. The user can interact with the Affinity Overlap chart, review the stark brand differences in the Culture Clash table, explore growth opportunities, and read the final, AI-generated Brand Archetype summary that explains the "why" behind the data. The report is automatically saved to their account for future reference.
EOT

echo "--- Context generation complete. File 'claude_context.txt' is ready. ---"