import React from "react";
import { Helmet } from "react-helmet-async";
import Navbar from "./Navbar";
import Footer from "./Footer";
import { CAREERS } from "./landingPageData";

const CONTACT_EMAIL = "nvidra@anote.ai";

function CareersPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white flex flex-col">
      <Helmet>
        <title>Careers | Panacea by Anote</title>
        <meta
          name="description"
          content="Open roles at Anote, the team building Panacea, an Autonomous Intelligence platform across CLI, VS Code, web, mobile, desktop, and SDK."
        />
        <link rel="canonical" href="https://anote.ai/careers" />
      </Helmet>

      <Navbar />
      <main className="flex-1 mx-auto max-w-3xl w-full px-6 py-16">
        <h1 className="text-3xl font-semibold">Careers</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">
          We're a small remote team building Panacea across six surfaces on one shared backend. Here's what we're
          hiring for.
        </p>

        <div className="mt-10 space-y-6">
          {CAREERS.map((role) => (
            <div key={role.title} className="rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h2 className="text-lg font-semibold">{role.title}</h2>
                <span className="text-xs text-gray-400 dark:text-gray-500">
                  {role.location} · {role.type}
                </span>
              </div>
              <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">{role.description}</p>
              <a
                href={`mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`Application: ${role.title}`)}`}
                className="mt-4 inline-block text-sm font-medium text-gray-900 dark:text-white hover:underline"
              >
                Apply via {CONTACT_EMAIL} →
              </a>
            </div>
          ))}
        </div>

        <p className="mt-10 text-sm text-gray-500 dark:text-gray-400">
          Don't see a fit?{" "}
          <a href={`mailto:${CONTACT_EMAIL}`} className="text-gray-900 dark:text-white font-medium hover:underline">
            Reach out anyway
          </a>
          .
        </p>
      </main>
      <Footer />
    </div>
  );
}

export default CareersPage;
