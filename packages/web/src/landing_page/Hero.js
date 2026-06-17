import React from "react";
import { Link } from "react-router-dom";
import { STATS } from "./landingPageData";

function Hero() {
  return (
    <section className="mx-auto max-w-5xl px-6 pt-20 pb-16 text-center">
      <div className="inline-flex items-center gap-2 rounded-full border border-gray-300 dark:border-gray-600 px-4 py-1.5 text-xs font-medium text-gray-500 dark:text-gray-400">
        <span className="w-1.5 h-1.5 rounded-full bg-gray-900 dark:bg-white" />
        Now generally available
      </div>

      <h1 className="mt-6 text-4xl sm:text-6xl font-bold tracking-tight">Panacea</h1>
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
          className="px-6 py-3 rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors"
        >
          Try Panacea free
        </Link>
        <a
          href="#versions"
          className="px-6 py-3 rounded-lg font-medium border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-[#2F2F2F] transition-colors"
        >
          See every version
        </a>
      </div>

      <dl className="mt-16 grid grid-cols-2 sm:grid-cols-4 gap-6 max-w-3xl mx-auto">
        {STATS.map((stat) => (
          <div key={stat.label} className="rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <dd className="text-2xl sm:text-3xl font-bold">{stat.value}</dd>
            <dt className="mt-1 text-xs text-gray-500 dark:text-gray-400">{stat.label}</dt>
          </div>
        ))}
      </dl>
    </section>
  );
}

export default Hero;
