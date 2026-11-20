# AGENTS.md

Instructions for AI assistants (Claude, ChatGPT/Codex, Gemini) working in this repository.

## Local rules

If a `local-rules.md` file exists at the repository root, read it in full before any task and follow it. It holds personal, machine-specific rules for the team member working on that machine, and it is intentionally in `.gitignore` (it may not exist on your machine). Never commit it.

## Language

**Everything in this repository must be written in English.** No Portuguese anywhere.

- Applies to code, comments, identifiers, commit messages, branch names, PR/issue text, docs, context files, UI strings, logs, and demo/pitch material.
- This holds even when a team member writes to you in Portuguese: you may reply to them in chat in their language, but anything that ends up in the repository is in English.
- If you find Portuguese text in the repository, translate it to English.

## Required context

Before any task, read the files in `00_Context/`:

| File | Content |
|------|---------|
| [00_Context/challenge-and-guidelines.md](00_Context/challenge-and-guidelines.md) | Challenge, themes, rules, judging criteria, and schedule (transcribed from the official PDF) |
| [00_Context/team.md](00_Context/team.md) | Team members, available AI tools, and collaboration rules |
| `00_Context/Hackathon Portugal 2026 - Challenge & guidelines overview 1 Finalito.pdf` | Original PDF from the organizers |

## Project summary

- Hackathon Portugal 2026 — InfraHack: AI for Cloud Infrastructure (Leaseweb × Velv), 20 Nov 2026, Lisbon.
- Team of 5: Miguel, Francisco, Carolina, Diogo, Ricardo.
- Everything starts from scratch on the day; build time 08:45–15:45; pitch is 5 minutes maximum.

## Rules for agents

- The root `README.md` is the project README for the jury: concise, covering goals, structure, and build/run instructions. Do not use it for internal notes.
- The repository is public: never write secrets (API keys, passwords, VM credentials) to tracked files. Use a local `.env` listed in `.gitignore`.
- Prefer common languages (Python, Go, PHP) and publicly available open-source dependencies, always declared in the build instructions.
- The project must have an open license allowing commercial and non-commercial reuse (e.g. Apache-2.0).
- The code must run on a Linux VM (provided by the organizers) and the live demo counts towards the score: favor things that work reliably.
- Small, frequent commits; the team works in parallel on the same repository.
- When adding new context, create a `.md` file in `00_Context/` and update the table above.
