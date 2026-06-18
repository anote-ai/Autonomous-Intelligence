import React, { useState } from "react";
import { CAPABILITIES } from "./landingPageData";

function Capabilities() {
  const [activeIndex, setActiveIndex] = useState(0);
  const active = CAPABILITIES[activeIndex];

  return (
    <section id="capabilities" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
      <div className="text-center">
        <div className="text-xs font-medium uppercase tracking-[0.22em] text-gray-400 dark:text-gray-500">
          Core capabilities
        </div>
        <h2 className="mt-2 text-2xl sm:text-3xl font-semibold">What Panacea can do</h2>
        <p className="mt-4 max-w-2xl mx-auto text-gray-600 dark:text-gray-300">
          One assistant, four core skills. Click a capability to see how it works.
        </p>
      </div>

      <div className="mt-10 grid md:grid-cols-[280px,1fr] gap-6">
        <div className="space-y-2" role="tablist" aria-label="Panacea capabilities">
          {CAPABILITIES.map((cap, i) => (
            <button
              key={cap.name}
              role="tab"
              aria-selected={activeIndex === i}
              onClick={() => setActiveIndex(i)}
              className={`w-full text-left rounded-xl px-4 py-3 transition-colors ${
                activeIndex === i
                  ? "bg-gray-900 dark:bg-white text-white dark:text-gray-900"
                  : "bg-[#F7F7F8] dark:bg-[#2F2F2F] text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-[#3a3a3a]"
              }`}
            >
              <div className="font-medium">{cap.name}</div>
              <div
                className={`mt-0.5 text-xs ${
                  activeIndex === i ? "text-white/80 dark:text-gray-700" : "text-gray-500 dark:text-gray-400"
                }`}
              >
                {cap.summary}
              </div>
            </button>
          ))}
        </div>

        <div
          role="tabpanel"
          className="rounded-xl border border-gray-200 dark:border-gray-700 p-6 bg-[#F7F7F8] dark:bg-[#171717]"
        >
          <h3 className="text-lg font-semibold">{active.name}</h3>
          <p className="mt-3 text-gray-600 dark:text-gray-300">{active.detail}</p>
          <ul className="mt-4 space-y-2">
            {active.bullets.map((bullet) => (
              <li key={bullet} className="flex items-start gap-2 text-sm text-gray-600 dark:text-gray-300">
                <span className="mt-1 w-1.5 h-1.5 rounded-full bg-gray-900 dark:bg-white flex-shrink-0" />
                {bullet}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default Capabilities;
