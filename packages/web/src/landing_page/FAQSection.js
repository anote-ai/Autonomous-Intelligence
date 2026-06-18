import React, { useState } from "react";
import { FAQS } from "./landingPageData";

function FAQSection() {
  const [openIndex, setOpenIndex] = useState(0);

  return (
    <section id="faq" className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl sm:text-3xl font-semibold">Frequently asked questions</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300 max-w-3xl">
        Still have questions about Panacea? Here are the ones we hear most often.
      </p>

      <div className="mt-8 space-y-3">
        {FAQS.map((faq, index) => {
          const isOpen = openIndex === index;
          return (
            <div
              key={faq.question}
              className={`rounded-xl border transition-colors ${
                isOpen
                  ? "border-gray-400 dark:border-gray-500 bg-[#F7F7F8] dark:bg-[#2F2F2F]"
                  : "border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600"
              }`}
            >
              <button
                type="button"
                aria-expanded={isOpen}
                aria-controls={`faq-panel-${index}`}
                onClick={() => setOpenIndex(isOpen ? null : index)}
                className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
              >
                <span className="font-medium">{faq.question}</span>
                <span
                  className={`flex-shrink-0 w-7 h-7 rounded-full border border-gray-300 dark:border-gray-600 flex items-center justify-center text-sm transition-transform ${
                    isOpen ? "rotate-45" : ""
                  }`}
                >
                  +
                </span>
              </button>
              {isOpen && (
                <div id={`faq-panel-${index}`} className="px-5 pb-4 text-sm text-gray-600 dark:text-gray-300">
                  {faq.answer}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default FAQSection;
