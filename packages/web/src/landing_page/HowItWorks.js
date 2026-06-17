import React from "react";
import { HOW_IT_WORKS_STEPS } from "./landingPageData";

function HowItWorks() {
  return (
    <section id="how-it-works" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl sm:text-3xl font-semibold">One backend, every surface</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300 max-w-3xl">
        Every version of Panacea calls the same shared Flask API, so your chat history, documents,
        and account stay in sync whether you start a conversation in the CLI and finish it on
        mobile, or upload a document on desktop and ask about it from the web.
      </p>
      <ol className="mt-8 grid sm:grid-cols-4 gap-6">
        {HOW_IT_WORKS_STEPS.map((s, idx) => (
          <li
            key={s.step}
            className="rounded-xl border border-gray-200 dark:border-gray-700 p-5 hover:border-gray-400 dark:hover:border-gray-500 transition-colors"
          >
            <span className="text-xs font-medium text-gray-400 dark:text-gray-500">Step {idx + 1}</span>
            <h3 className="mt-1 font-medium">{s.step}</h3>
            <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">{s.body}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

export default HowItWorks;
