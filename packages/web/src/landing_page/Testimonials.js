import React from "react";
import { TESTIMONIALS } from "./landingPageData";

function Testimonials() {
  return (
    <section className="mx-auto max-w-7xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
      <h2 className="text-2xl sm:text-3xl font-semibold text-center">Trusted by teams shipping with Panacea</h2>
      <div className="mt-12 grid gap-6 md:grid-cols-3">
        {TESTIMONIALS.map((t) => (
          <figure
            key={t.name}
            className="rounded-2xl border border-gray-200 dark:border-gray-700 p-6 flex flex-col justify-between"
          >
            <blockquote className="text-sm text-gray-700 dark:text-gray-200">&ldquo;{t.quote}&rdquo;</blockquote>
            <figcaption className="mt-6 text-sm">
              <p className="font-medium text-gray-900 dark:text-white">{t.name}</p>
              <p className="text-gray-500 dark:text-gray-400">{t.role}</p>
            </figcaption>
          </figure>
        ))}
      </div>
    </section>
  );
}

export default Testimonials;
