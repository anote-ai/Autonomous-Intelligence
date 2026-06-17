export const STATS = [
  { value: "6", label: "ways to use Panacea" },
  { value: "1", label: "shared backend & account" },
  { value: "<5 min", label: "to your first answer" },
  { value: "100%", label: "cited, grounded responses" },
];

export const CAPABILITIES = [
  {
    name: "Autonomous Coding",
    summary: "Plan, edit, and review code across your whole repo.",
    detail:
      "Panacea reads your project, proposes a plan, edits the files that matter, and shows you a diff before anything is applied. It uses TF-IDF powered search to find the right files instead of guessing from a single prompt.",
    bullets: [
      "Multi-file edits with diff review before applying",
      "Repo-aware search across your codebase",
      "Works from the CLI, VS Code, or the SDK",
    ],
  },
  {
    name: "Document Q&A",
    summary: "Ask questions and get cited answers from your own files.",
    detail:
      "Upload PDFs, CSVs, or text files and Panacea retrieves the most relevant passages before answering, citing the exact source so you can verify every claim.",
    bullets: [
      "Retrieval augmented answers with source citations",
      "Supports PDFs, CSVs, and plain text",
      "Available in the web app, desktop app, and SDK",
    ],
  },
  {
    name: "Multi-provider Chat",
    summary: "Switch between Claude, GPT-4o, and more in one conversation.",
    detail:
      "Pick the model that fits the task and switch mid-project. Panacea streams responses in real time and keeps your full session history searchable.",
    bullets: [
      "Claude, GPT-4o, and GPT-4o-mini supported out of the box",
      "Streaming responses with stop/resume controls",
      "Session history synced across every surface",
    ],
  },
  {
    name: "Private, On-Prem Mode",
    summary: "Run Panacea entirely on your own infrastructure.",
    detail:
      "The desktop app bundles a local Python backend so regulated teams can keep documents and chat history off the cloud entirely, with no change to the workflow.",
    bullets: [
      "Electron desktop app with a bundled local backend",
      "No documents or messages leave your machine",
      "Same UI and capabilities as the hosted product",
    ],
  },
];

export const PRODUCT_VERSIONS = [
  {
    id: "cli",
    name: "CLI",
    fullName: "Panacea CLI",
    tagline: "Autonomous Intelligence in your terminal",
    description:
      "A TypeScript Commander CLI with 23 commands and TF-IDF powered repo search. Point it at a project and ask it to explain, fix, or extend the code.",
    steps: [
      "Install the CLI from the workspace",
      "Authenticate with your API key",
      "Run a command against your project",
    ],
    command: [
      "npm install -g @anote-ai/cli",
      "anote auth login",
      'anote chat "refactor this module"',
    ].join("\n"),
    bestFor: "Engineers who live in the terminal and want repo-aware automation.",
  },
  {
    id: "vscode",
    name: "VS Code",
    fullName: "Panacea for VS Code",
    tagline: "Autonomous Intelligence inside your editor",
    description:
      "A chat sidebar with inline diff review and streaming responses, so you can ask questions and apply changes without leaving your editor.",
    steps: [
      "Open the Extensions panel in VS Code",
      'Search for "Panacea" (Anote AI)',
      "Sign in and open the chat sidebar to start",
    ],
    command: "code --install-extension anote-ai.panacea",
    bestFor: "Teams who want AI assistance reviewed as a diff, right in the editor.",
  },
  {
    id: "web",
    name: "Web",
    fullName: "Panacea Web",
    tagline: "Autonomous Intelligence in your browser",
    description:
      "A ChatGPT-style web chatbot with light and dark mode, session history, and streaming responses backed by multiple LLM providers.",
    steps: [
      "Create a free account",
      "Pick a model (Claude, GPT-4o, and more)",
      "Start chatting and revisit your session history any time",
    ],
    command: "open https://app.anote.ai",
    bestFor: "Anyone who wants to start chatting in seconds, no install required.",
  },
  {
    id: "mobile",
    name: "Mobile",
    fullName: "Panacea Mobile",
    tagline: "Autonomous Intelligence on the go",
    description:
      "An Expo React Native app so you can chat with your AI assistant and review your projects from anywhere, picking up exactly where you left off.",
    steps: [
      "Download the app from the App Store or Google Play",
      "Sign in with your Panacea account",
      "Continue any conversation started on web or desktop",
    ],
    command: "expo install panacea-mobile",
    bestFor: "Checking in on long-running tasks or chatting away from your desk.",
  },
  {
    id: "desktop",
    name: "Desktop",
    fullName: "Panacea Desktop",
    tagline: "Private, on-premise Autonomous Intelligence",
    description:
      "An Electron desktop app bundling a local Python backend, so enterprises can run Panacea fully on-premise and keep sensitive documents off the cloud.",
    steps: [
      "Download the installer for macOS, Windows, or Linux",
      "Point Panacea at your local documents folder",
      "Ask questions and get cited answers, entirely offline",
    ],
    command: "make desktop-build",
    bestFor: "Regulated teams that need data to stay on local infrastructure.",
  },
  {
    id: "sdk",
    name: "SDK",
    fullName: "Panacea SDK",
    tagline: "Autonomous Intelligence for your own apps",
    description:
      "A TypeScript SDK that wraps the Panacea backend API, so you can embed chat, document Q&A, and search directly into your own products.",
    steps: [
      "Install the SDK package",
      "Initialize the client with your API key",
      "Call the chat or document endpoints from your code",
    ],
    command: [
      "npm install @anote-ai/sdk",
      "",
      'import { Panacea } from "@anote-ai/sdk";',
      "const client = new Panacea({ apiKey: process.env.PANACEA_API_KEY });",
      'await client.chat.send({ message: "Summarize this 10-K" });',
    ].join("\n"),
    bestFor: "Developers who want to embed Panacea into a product they're building.",
  },
];

export const PRICING_PLANS = [
  {
    id: "web",
    name: "Web App",
    price: "$20",
    period: "/month",
    description: "Unlimited chats in the browser with every model Panacea supports.",
    features: [
      "Unlimited conversations with Claude and GPT-4o models",
      "Document upload and cited Q&A",
      "Session history synced across devices",
      "Light and dark mode",
    ],
    cta: "Start with the web app",
    href: "/register",
    highlighted: true,
  },
  {
    id: "api",
    name: "API / SDK",
    price: "Pay per credit",
    period: "",
    description: "Bring Panacea into your own product. Buy credits and spend them on chat, document, and search calls as you use them.",
    features: [
      "Credits cover chat, document Q&A, and search calls",
      "No monthly minimum — pay only for what you use",
      "Works with the CLI, VS Code extension, and SDK",
      "Top up or auto-recharge from your account dashboard",
    ],
    cta: "Get API credits",
    href: "/register",
    highlighted: false,
  },
  {
    id: "enterprise",
    name: "Enterprise / On-Prem",
    price: "Custom",
    period: "",
    description: "Run Panacea Desktop fully on your own infrastructure with volume credit pricing and dedicated support.",
    features: [
      "Electron desktop app with a bundled local backend",
      "Volume credit pricing for API usage",
      "Dedicated onboarding and support",
      "Custom data retention and security review",
    ],
    cta: "Talk to us",
    href: "/register",
    highlighted: false,
  },
];

export const TESTIMONIALS = [
  {
    quote:
      "We moved our whole documentation Q&A workflow onto Panacea in an afternoon. The citations make it easy to trust the answers.",
    name: "Engineering Lead",
    role: "Mid-size SaaS company",
  },
  {
    quote:
      "Having the CLI, VS Code extension, and web app share one account made adoption easy — nobody had to relearn a new tool per surface.",
    name: "Staff Engineer",
    role: "Fintech infrastructure team",
  },
  {
    quote:
      "The desktop app let us run everything on-prem for a regulated client without changing how the team actually works day to day.",
    name: "Solutions Architect",
    role: "Enterprise services consultancy",
  },
];

export const HOW_IT_WORKS_STEPS = [
  {
    step: "Upload",
    body: "Bring in code, PDFs, or connect a data source from any Panacea surface.",
  },
  {
    step: "Ask",
    body: "Chat in natural language from the CLI, editor, browser, mobile, or desktop.",
  },
  {
    step: "Reason",
    body: "Panacea retrieves the relevant context and plans the steps needed to answer.",
  },
  {
    step: "Act",
    body: "Get a cited answer, a reviewed code diff, or a generated document back.",
  },
];

export const FAQS = [
  {
    question: "What is Panacea?",
    answer:
      "Panacea is Anote's Autonomous Intelligence platform: a single AI assistant available as a coding CLI, a VS Code extension, a web chatbot, a mobile app, a private desktop app, and an SDK, all backed by one shared Flask API and account.",
  },
  {
    question: "Do I need to install anything to try it?",
    answer:
      "No. Panacea Web runs entirely in the browser. Create a free account and start chatting; you can install the CLI, VS Code extension, desktop app, or SDK later if you need them.",
  },
  {
    question: "Which AI models does Panacea use?",
    answer:
      "Panacea supports Anthropic's Claude models and OpenAI's GPT-4o family out of the box, and you can switch models mid-conversation depending on the task.",
  },
  {
    question: "How does Panacea avoid hallucinating answers?",
    answer:
      "When you ask about your own documents or code, Panacea retrieves the most relevant passages first and cites them in its answer, so you can verify the source instead of trusting the model blindly.",
  },
  {
    question: "Can I run Panacea fully on-premise?",
    answer:
      "Yes. Panacea Desktop bundles a local Python backend so your documents, code, and chat history never leave your machine, while keeping the same features as the hosted product.",
  },
  {
    question: "Is my data shared across the CLI, web, mobile, and desktop apps?",
    answer:
      "Every Panacea surface talks to the same backend API, so your account, documents, and chat sessions stay in sync no matter which version you use, unless you choose the fully offline desktop mode.",
  },
  {
    question: "How does pricing work?",
    answer:
      "The web app is a flat $20/month for unlimited chat. The CLI, VS Code extension, and SDK are billed per credit, so you only pay for the chat, document, and search calls you actually make. Enterprise and on-premise deployments use custom volume pricing.",
  },
];
