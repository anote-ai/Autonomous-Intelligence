import React from "react";
import { Helmet } from "react-helmet-async";
import Navbar from "./Navbar";
import Footer from "./Footer";

function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white flex flex-col">
      <Helmet>
        <title>Privacy Policy | Panacea by Anote</title>
        <meta
          name="description"
          content="How Anote collects, uses, and protects your data across the Panacea CLI, VS Code extension, web app, mobile app, desktop app, and SDK."
        />
        <link rel="canonical" href="https://anote.ai/privacy" />
      </Helmet>

      <Navbar />
      <main className="flex-1 mx-auto max-w-3xl w-full px-6 py-16">
        <h1 className="text-3xl font-semibold">Privacy Policy</h1>
        <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Last updated: {new Date().getFullYear()}</p>

        <h2 className="mt-8 text-xl font-semibold">What we collect</h2>
        <p className="text-gray-600 dark:text-gray-300">
          When you create a Panacea account, we collect your name, email address, and the documents, code, and
          messages you choose to send through the CLI, VS Code extension, web app, mobile app, or SDK. Panacea
          Desktop's local mode keeps documents and chat history on your machine and does not send them to our
          servers.
        </p>

        <h2 className="mt-8 text-xl font-semibold">How we use it</h2>
        <p className="text-gray-600 dark:text-gray-300">
          We use your data to operate the chat, document Q&amp;A, and search features, to sync sessions across
          devices, and to bill API/SDK usage by credits. We do not sell your data to third parties.
        </p>

        <h2 className="mt-8 text-xl font-semibold">Third-party model providers</h2>
        <p className="text-gray-600 dark:text-gray-300">
          Messages you send may be processed by the model provider you select (such as Anthropic or OpenAI) in
          order to generate a response, subject to that provider's own data handling terms.
        </p>

        <h2 className="mt-8 text-xl font-semibold">Data retention and deletion</h2>
        <p className="text-gray-600 dark:text-gray-300">
          You can delete uploaded documents and chat sessions from your account at any time. Deleting your account
          removes your stored documents and chat history from our servers, with the exception of records we're
          required to retain for billing or legal compliance.
        </p>

        <h2 className="mt-8 text-xl font-semibold">Contact</h2>
        <p className="text-gray-600 dark:text-gray-300">
          Questions about this policy or your data can be sent through our contact page.
        </p>
      </main>
      <Footer />
    </div>
  );
}

export default PrivacyPolicyPage;
