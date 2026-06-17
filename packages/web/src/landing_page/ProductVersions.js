import React, { useState } from "react";
import { PRODUCT_VERSIONS } from "./landingPageData";

function ProductVersions() {
  const [activeId, setActiveId] = useState(PRODUCT_VERSIONS[0].id);
  const [copied, setCopied] = useState(false);
  const active = PRODUCT_VERSIONS.find((v) => v.id === activeId) || PRODUCT_VERSIONS[0];

  const copyCommand = async () => {
    try {
      await navigator.clipboard.writeText(active.command);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // Clipboard API unavailable; ignore.
    }
  };

  return (
    <section id="versions" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl sm:text-3xl font-semibold">How to use every version of Panacea</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300 max-w-3xl">
        Panacea ships as six surfaces, all talking to the same backend and the same account. Pick
        whichever fits how you work today &mdash; you can use more than one at once.
      </p>

      <div className="mt-8 flex flex-wrap gap-2" role="tablist" aria-label="Panacea product versions">
        {PRODUCT_VERSIONS.map((v) => (
          <button
            key={v.id}
            role="tab"
            aria-selected={activeId === v.id}
            onClick={() => setActiveId(v.id)}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              activeId === v.id
                ? "bg-gray-900 dark:bg-white text-white dark:text-gray-900"
                : "border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
            }`}
          >
            {v.name}
          </button>
        ))}
      </div>

      <div role="tabpanel" className="mt-8 grid md:grid-cols-2 gap-6 items-start">
        <div>
          <h3 className="text-xl font-semibold">{active.fullName}</h3>
          <p className="mt-1 text-sm font-medium text-gray-500 dark:text-gray-400">{active.tagline}</p>
          <p className="mt-3 text-gray-600 dark:text-gray-300">{active.description}</p>

          <ol className="mt-4 space-y-1 text-sm text-gray-600 dark:text-gray-300 list-decimal list-inside">
            {active.steps.map((step) => (
              <li key={step}>{step}</li>
            ))}
          </ol>

          <p className="mt-4 text-sm text-gray-500 dark:text-gray-400">
            <span className="font-medium text-gray-700 dark:text-gray-300">Best for: </span>
            {active.bestFor}
          </p>
        </div>

        <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-[#F7F7F8] dark:bg-[#171717] overflow-hidden">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 dark:border-gray-700">
            <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
              {active.fullName.toLowerCase().replace(/\s+/g, "-")}.sh
            </span>
            <button
              onClick={copyCommand}
              className="text-xs font-medium px-2 py-1 rounded-md border border-gray-300 dark:border-gray-600 text-gray-600 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors"
            >
              {copied ? "Copied!" : "Copy"}
            </button>
          </div>
          <pre className="p-4 text-sm overflow-x-auto">
            <code>{active.command}</code>
          </pre>
        </div>
      </div>
    </section>
  );
}

export default ProductVersions;
