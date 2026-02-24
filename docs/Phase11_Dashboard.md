# [Phase 11: User (Candidate) & Admin Dashboard Implementation]

## 1. Overview
The core AI interview engine and scoring logic are fully complete. This phase implements the "Job Selection & Management" dashboards for both Candidates and Administrators, aligned with modern HR platform standards.

## 2. User (Candidate) Dashboard (`frontend/src/pages/MyPage.jsx`)
Create a dedicated workspace for logged-in candidates.
* **Section 1: Resume Management (Rule: 1 Resume per Account)**
  * Provide a UI for the user to upload, view, or replace their default resume (PDF/Text). 
  * Ensure the system strictly maintains only 1 active resume per user account to simplify the application process.
* **Section 2: Job Board (공고 선택 페이지)**
  * Display a clean grid/list of `ACTIVE` job postings.
  * Show key info: Company/Title, Requirements, and Status.
  * Provide a simple search bar or basic filter (e.g., sort by newest).
  * Add a "지원 및 면접 시작하기 (Apply & Start Interview)" button.
* **Section 3: My Interview History (면접 결과 리포트)**
  * Display a list of all past interviews the user has completed.
  * Columns/Card data: Date, Job Title, Total Score.
  * Add a "결과 리포트 보기 (View Report)" button linking to the detailed `Report.jsx` page.

## 3. Admin Dashboard (`frontend/src/pages/AdminDashboard.jsx`)
Upgrade the admin page to manage postings and track applicant scores.
* **Feature 1: Job Posting Management (공고 관리)**
  * UI to Create, Edit, Copy, and Close (change status to `CLOSED`) job postings.
  * Ensure the form captures: Title, Experience Level, Job Description (JD), and Requirements.
* **Feature 2: Applicant Leaderboard (지원자 현황 및 랭킹)**
  * When an admin clicks on a specific Job Posting, render a Data Table displaying all candidates who applied and completed the AI interview.
  * **Columns:** Candidate Name/ID, Interview Date, Total Score, Tech Score, Non-verbal Score.
  * **Sort/Filter:** Allow sorting by Total Score to easily identify top candidates.
  * **Action:** Provide a "상세 리포트 보기 (View Full Report)" button for each row so admins can read the AI's feedback.
* **Feature 3: AI JD Generator (Optional Bonus)**
  * Next to the JD input field, add an "AI 공고 초안 작성" button that calls an LLM to generate a template based on the Job Title.

## 4. Backend API Requirements
* Ensure RESTful endpoints exist and are properly wired:
  * `GET /api/user/resume` & `POST /api/user/resume` (Handle single resume logic).
  * `GET /api/user/interviews` (Fetch user's history).
  * `GET /api/admin/jobs/{job_id}/applicants` (Fetch evaluation reports tied to a specific job ID).

**Instruction for Agent:** Implement these dashboard components using React and Tailwind CSS. Focus on a clean, modern UI (similar to platforms like Wanted or LinkedIn). Prioritize the "1-Resume Rule", the "My Interview History", and the "Admin Applicant Leaderboard".