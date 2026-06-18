import React from "react";
import { Helmet } from "react-helmet-async";
import Navbar from "./Navbar";
import Footer from "./Footer";
import { CASE_STUDIES } from "./landingPageData";

function CaseStudiesPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white flex flex-col">
      <Helmet>
        <title>Case Studies | Panacea by Anote</title>
        <meta
          name="description"
          content="How teams use Panacea for documentation Q&A, repo-aware coding, and on-premise AI deployments."
        />
        <link rel="canonical" href="https://anote.ai/case-studies" />
      </Helmet>

      <Navbar />
      <main className="flex-1 mx-auto max-w-5xl w-full px-6 py-16">
        <h1 className="text-3xl font-semibold">Case studies</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">How teams put Panacea to work.</p>

        <div className="mt-10 grid gap-6 md:grid-cols-2">
          {CASE_STUDIES.map((study) => (
            <div key={study.company} className="rounded-2xl border border-gray-200 dark:border-gray-700 p-6">
              <p className="text-xs uppercase tracking-wide text-gray-400 dark:text-gray-500">{study.industry}</p>
              <h2 className="mt-2 text-lg font-semibold">{study.headline}</h2>
              <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">{study.company}</p>
              <p className="mt-4 text-sm text-gray-600 dark:text-gray-300">{study.summary}</p>
              <ul className="mt-4 space-y-2 text-sm">
                {study.results.map((result) => (
                  <li key={result} className="flex gap-2">
                    <span aria-hidden="true">✓</span>
                    <span className="text-gray-600 dark:text-gray-300">{result}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </main>
      <Footer />
    </div>
  );
}

export default CaseStudiesPage;
