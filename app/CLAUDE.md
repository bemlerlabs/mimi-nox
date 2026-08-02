# MiMi Nox Frontend — Claude Code Context

## Product
MiMi Nox is a **local-first AI assistant** running 100% on the user's device. No cloud, no tracking, no account required.

### Key Features
- **Offline-first**: Runs locally via Ollama + gemma4:12b
- **Multimodal**: Chat, images, PDFs, files, screenshots, vision
- **Tools**: Shell, web search, browser, file system, screenshots
- **Memory**: Semantic vector memory (chromadb)
- **Skills**: `/write`, `/review`, `/files`, `/pdf`, `/scan`, `/svg`, `/chart`, `/shell`, `/research`
- **Mobile**: QR code pairing → PWA on phone (LAN-first)
- **Privacy**: No telemetry, no cloud, no account

### What MiMi Nox is NOT
- ❌ Not a training pipeline (internal R&D only)
- ❌ Not AgentWatch (separate project)
- ❌ Not about GRPO/LoRA fine-tuning

## Tech Stack
- React 19 + Vite + TypeScript
- Tailwind CSS v4
- shadcn/ui components
- Framer Motion animations
- Zustand state management
- React Router v7

## Design System
- **Colors**: Dark monochrome (#000 background, white text, subtle grays)
- **Liquid Glass**: Frosted glass cards with gradient borders
- **Typography**: Inter (body), JetBrains Mono (code)
- **Animations**: Framer Motion blur-in, fade-up, stagger
- **Video BG**: Subtle dark video backgrounds on hero sections

## Component Structure
```
src/
├── components/
│   ├── landing/     # Landing page sections
│   ├── dashboard/   # Chat UI components
│   └── ui/          # Shared shadcn/ui components
├── hooks/           # Custom React hooks
├── lib/             # Utilities
├── pages/           # Page components
├── assets/          # Images, videos
└── styles/          # Global CSS
```

## Landing Page Sections
1. **Hero**: Full viewport, video background, headline, CTA
2. **Features**: Grid of feature cards with icons
3. **Architecture**: Diagram showing local-first architecture
4. **Skills**: Showcase built-in skills
5. **Mobile**: QR pairing demo
6. **CTA**: Final call-to-action
7. **Footer**: Links, social, version

## Chat UI (Dashboard)
- Chat interface like Hermes Agent but in MiMi Nox colors
- Message bubbles, typing indicator, tool approval UI
- Sidebar with sessions, settings
- Mobile responsive

## API Integration
- Backend runs on localhost:8765
- WebSocket for real-time chat
- REST API for settings, sessions, memory