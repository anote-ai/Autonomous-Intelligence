import { Link } from "react-router-dom";
import { Helmet } from "react-helmet-async";
import { useTheme } from "../App";
import RocketLogo from "../components/RocketLogo";

interface ProductVersion {
  id: string;
  name: string;
  tagline: string;
  description: string;
  steps: string[];
  command: string;
}

const PRODUCT_VERSIONS: ProductVersion[] = [
  {
    id: "cli",
    name: "Panacea CLI",
    tagline: "Autonomous Intelligence in your terminal",
    description:
      "Run Panacea as a command-line agent that reads your codebase, plans changes, and edits files directly from the terminal. Built with 23 commands and TF-IDF powered search.",
    steps: [
      "Install the CLI from the monorepo workspace",
      "Authenticate with your API key",
      "Run a command against your project",
    ],
    command: "npm install -g @anote-ai/cli\nanote auth login\nanote chat \"refactor this module\"",
  },
  {
    id: "vscode",
    name: "Panacea for VS Code",
    tagline: "Autonomous Intelligence inside your editor",
    description:
      "Install the VS Code extension to get a chat sidebar, inline diff review, and streaming responses without leaving your editor.",
    steps: [
      "Open the Extensions panel in VS Code",
      "Search for \"Panacea\" (Anote AI)",
      "Sign in and open the chat sidebar to start",
    ],
    command: "code --install-extension anote-ai.panacea",
  },
  {
    id: "web",
    name: "Panacea Web",
    tagline: "Autonomous Intelligence in your browser",
    description:
      "A ChatGPT-style web chatbot with light and dark mode, session history, and streaming responses backed by multiple LLM providers.",
    steps: [
      "Create a free account",
      "Pick a model (Claude, GPT-4o, and more)",
      "Start chatting and review your session history any time",
    ],
    command: "open https://app.anote.ai",
  },
  {
    id: "mobile",
    name: "Panacea Mobile",
    tagline: "Autonomous Intelligence on the go",
    description:
      "An Expo React Native app so you can chat with your AI assistant and review your projects from anywhere.",
    steps: [
      "Download the app from the App Store or Google Play",
      "Sign in with your Panacea account",
      "Pick up your conversation where the web or desktop app left off",
    ],
    command: "expo install panacea-mobile",
  },
  {
    id: "desktop",
    name: "Panacea Desktop",
    tagline: "Private, on-premise Autonomous Intelligence",
    description:
      "An Electron desktop app bundling a local Python backend, so enterprises can run Panacea fully on-premise and keep sensitive documents off the cloud.",
    steps: [
      "Download the installer for macOS, Windows, or Linux",
      "Point Panacea at your local documents folder",
      "Ask questions and get cited answers, entirely offline",
    ],
    command: "make desktop-build",
  },
  {
    id: "sdk",
    name: "Panacea SDK",
    tagline: "Autonomous Intelligence for your own apps",
    description:
      "A TypeScript SDK that wraps the Panacea backend API, so you can embed chat, document Q&A, and search into your own products.",
    steps: [
      "Install the SDK package",
      "Initialize the client with your API key",
      "Call the chat or document endpoints directly from your code",
    ],
    command:
      "npm install @anote-ai/sdk\n\nimport { Panacea } from \"@anote-ai/sdk\";\nconst client = new Panacea({ apiKey: process.env.PANACEA_API_KEY });\nawait client.chat.send({ message: \"Summarize this 10-K\" });",
  },
];

const howToSchema = {
  "@context": "https://schema.org",
  "@type": "HowTo",
  name: "How to use Panacea, the Autonomous Intelligence platform",
  description:
    "Panacea by Anote ships as a CLI, VS Code extension, web chatbot, mobile app, desktop app, and SDK. Here is how to get started with each.",
  step: PRODUCT_VERSIONS.map((v, i) => ({
    "@type": "HowToStep",
    position: i + 1,
    name: v.name,
    text: v.description,
  })),
};

const softwareSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Panacea",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web, macOS, Windows, Linux, iOS, Android",
  description:
    "Panacea is an Autonomous Intelligence platform from Anote that ships as a coding CLI, VS Code extension, web chatbot, mobile app, desktop app, and SDK, all backed by a shared Flask API.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

export default function LandingPage() {
  const { dark, toggle } = useTheme();

  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white">
      <Helmet>
        <title>Panacea by Anote | Autonomous Intelligence Platform</title>
        <meta
          name="description"
          content="Panacea is Anote's Autonomous Intelligence platform: a coding CLI, VS Code extension, web chatbot, mobile app, desktop app, and SDK, all powered by one Flask backend. See how to use every version."
        />
        <meta
          name="keywords"
          content="Panacea, Anote, autonomous intelligence, AI agent, coding CLI, VS Code extension, AI chatbot, AI SDK, private AI desktop app, autonomous AI platform"
        />
        <link rel="canonical" href="https://anote.ai/" />
        <meta property="og:type" content="website" />
        <meta property="og:title" content="Panacea by Anote | Autonomous Intelligence Platform" />
        <meta
          property="og:description"
          content="One Autonomous Intelligence platform, six ways to use it: CLI, VS Code, web, mobile, desktop, and SDK."
        />
        <meta property="og:url" content="https://anote.ai/" />
        <meta name="twitter:card" content="summary_large_image" />
        <script type="application/ld+json">{JSON.stringify(softwareSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(howToSchema)}</script>
      </Helmet>

      {/* Nav */}
      <header className="sticky top-0 z-10 border-b border-gray-200 dark:border-gray-700 bg-white/90 dark:bg-[#212121]/90 backdrop-blur">
        <nav className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <RocketLogo className="w-7 h-7" />
            <span className="font-semibold">Panacea</span>
            <span className="hidden sm:inline text-gray-400 dark:text-gray-500 text-sm">by Anote</span>
          </div>
          <div className="hidden md:flex items-center gap-6 text-sm text-gray-600 dark:text-gray-300">
            <a href="#what-is-panacea" className="hover:text-gray-900 dark:hover:text-white">What is Panacea</a>
            <a href="#versions" className="hover:text-gray-900 dark:hover:text-white">Product versions</a>
            <a href="#how-it-works" className="hover:text-gray-900 dark:hover:text-white">How it works</a>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={toggle}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400"
              aria-label="Toggle dark mode"
            >
              {dark ? "☀️" : "🌙"}
            </button>
            <Link
              to="/login"
              className="hidden sm:inline px-4 py-2 rounded-lg text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100"
            >
              Get started
            </Link>
          </div>
        </nav>
      </header>

      <main>
        {/* Hero */}
        <section className="mx-auto max-w-5xl px-6 pt-20 pb-16 text-center">
          <h1 className="text-4xl sm:text-6xl font-bold tracking-tight">Panacea</h1>
          <p className="mt-4 text-xl sm:text-2xl font-medium text-gray-600 dark:text-gray-300">
            The Autonomous Intelligence platform from Anote
          </p>
          <p className="mt-6 max-w-2xl mx-auto text-base sm:text-lg text-gray-500 dark:text-gray-400">
            Panacea is a single AI assistant that follows you everywhere you work: it writes and reviews
            code from the terminal, answers questions inside your editor, chats in the browser, runs
            privately on your desktop, and embeds into your own apps through an SDK &mdash; all backed by
            one shared autonomous reasoning engine.
          </p>
          <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-center">
            <Link
              to="/register"
              className="px-6 py-3 rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100"
            >
              Try Panacea free
            </Link>
            <a
              href="#versions"
              className="px-6 py-3 rounded-lg font-medium border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
            >
              See every version
            </a>
          </div>
        </section>

        {/* What is Panacea */}
        <section id="what-is-panacea" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl sm:text-3xl font-semibold">What is Autonomous Intelligence?</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300 max-w-3xl">
            Autonomous Intelligence means an AI agent that can plan and carry out multi-step work on its
            own &mdash; reading your files, calling your APIs, asking clarifying questions, and only checking
            in with you for the decisions that matter. Panacea pairs a shared reasoning core with
            Anthropic and OpenAI models, a Flask backend, and retrieval over your own documents and
            codebase, so it can act with the right context instead of guessing.
          </p>
          <div className="mt-8 grid sm:grid-cols-3 gap-6">
            {[
              { title: "Plans before it acts", body: "Panacea breaks a request into steps, searches relevant code or documents, then executes." },
              { title: "Grounded in your data", body: "Answers cite your uploaded documents and codebase instead of relying on memory alone." },
              { title: "Works everywhere you do", body: "The same assistant is available from the terminal, your editor, the browser, mobile, and desktop." },
            ].map((card) => (
              <div key={card.title} className="rounded-xl border border-gray-200 dark:border-gray-700 p-5 bg-[#F7F7F8] dark:bg-[#2F2F2F]">
                <h3 className="font-medium">{card.title}</h3>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{card.body}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Product versions */}
        <section id="versions" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl sm:text-3xl font-semibold">How to use every version of Panacea</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300 max-w-3xl">
            Panacea ships as six surfaces, all talking to the same backend. Pick whichever fits how you
            work today &mdash; you can use more than one at once.
          </p>

          <div className="mt-10 space-y-10">
            {PRODUCT_VERSIONS.map((v, i) => (
              <article key={v.id} id={v.id} className="grid md:grid-cols-2 gap-6 items-start">
                <div>
                  <h3 className="text-xl font-semibold">
                    {i + 1}. {v.name}
                  </h3>
                  <p className="mt-1 text-sm font-medium text-gray-500 dark:text-gray-400">{v.tagline}</p>
                  <p className="mt-3 text-gray-600 dark:text-gray-300">{v.description}</p>
                  <ol className="mt-4 space-y-1 text-sm text-gray-600 dark:text-gray-300 list-decimal list-inside">
                    {v.steps.map((step) => (
                      <li key={step}>{step}</li>
                    ))}
                  </ol>
                </div>
                <pre className="rounded-xl border border-gray-200 dark:border-gray-700 bg-[#F7F7F8] dark:bg-[#171717] p-4 text-sm overflow-x-auto">
                  <code>{v.command}</code>
                </pre>
              </article>
            ))}
          </div>
        </section>

        {/* How it works */}
        <section id="how-it-works" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
          <h2 className="text-2xl sm:text-3xl font-semibold">One backend, every surface</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300 max-w-3xl">
            Every version of Panacea calls the same shared Flask API, so your chat history, documents,
            and account stay in sync whether you start a conversation in the CLI and finish it on
            mobile, or upload a document on desktop and ask about it from the web.
          </p>
          <ol className="mt-8 grid sm:grid-cols-4 gap-6">
            {[
              { step: "Upload", body: "Bring in code, PDFs, or connect a data source." },
              { step: "Ask", body: "Chat in natural language from any Panacea surface." },
              { step: "Reason", body: "Panacea retrieves context and plans the steps to answer." },
              { step: "Act", body: "Get a cited answer, an edited file, or a generated document." },
            ].map((s, idx) => (
              <li key={s.step} className="rounded-xl border border-gray-200 dark:border-gray-700 p-5">
                <span className="text-xs font-medium text-gray-400 dark:text-gray-500">Step {idx + 1}</span>
                <h3 className="mt-1 font-medium">{s.step}</h3>
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{s.body}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* CTA */}
        <section className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700 text-center">
          <h2 className="text-2xl sm:text-3xl font-semibold">Ready to put Autonomous Intelligence to work?</h2>
          <p className="mt-4 text-gray-600 dark:text-gray-300">
            Create a free account and start from the web, then install whichever other surfaces you need.
          </p>
          <div className="mt-6">
            <Link
              to="/register"
              className="px-6 py-3 rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 inline-block"
            >
              Get started with Panacea
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-gray-200 dark:border-gray-700 py-8">
        <div className="mx-auto max-w-7xl px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-gray-500 dark:text-gray-400">
          <div className="flex items-center gap-2">
            <RocketLogo className="w-5 h-5" />
            <span>Panacea by Anote AI</span>
          </div>
          <p>&copy; {new Date().getFullYear()} Anote AI. All rights reserved.</p>
        </div>
      </footer>
    </div>
  );
}
