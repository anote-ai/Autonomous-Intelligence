import React from "react";
import { Link } from "react-router-dom";
import { PRICING_PLANS } from "./landingPageData";

function Pricing() {
  return (
    <section id="pricing" className="mx-auto max-w-7xl px-6 py-16 border-t border-gray-200 dark:border-gray-700">
      <div className="text-center max-w-2xl mx-auto">
        <h2 className="text-2xl sm:text-3xl font-semibold">Simple, usage-based pricing</h2>
        <p className="mt-4 text-gray-600 dark:text-gray-300">
          Chat for a flat monthly rate, or pay only for the API credits you use.
        </p>
      </div>

      <div className="mt-12 grid gap-6 md:grid-cols-3">
        {PRICING_PLANS.map((plan) => (
          <div
            key={plan.id}
            className={`flex flex-col rounded-2xl border p-8 ${
              plan.highlighted
                ? "border-gray-900 dark:border-white bg-gray-50 dark:bg-[#2A2A2A] shadow-sm"
                : "border-gray-200 dark:border-gray-700"
            }`}
          >
            {plan.highlighted && (
              <span className="self-start mb-4 text-xs font-medium px-2 py-1 rounded-full bg-gray-900 dark:bg-white text-white dark:text-gray-900">
                Most popular
              </span>
            )}
            <h3 className="text-lg font-semibold">{plan.name}</h3>
            <p className="mt-4 flex items-baseline gap-1">
              <span className="text-3xl font-semibold">{plan.price}</span>
              {plan.period && <span className="text-gray-500 dark:text-gray-400">{plan.period}</span>}
            </p>
            <p className="mt-3 text-sm text-gray-600 dark:text-gray-300">{plan.description}</p>

            <ul className="mt-6 space-y-3 text-sm flex-1">
              {plan.features.map((feature) => (
                <li key={feature} className="flex gap-2">
                  <span aria-hidden="true">✓</span>
                  <span className="text-gray-600 dark:text-gray-300">{feature}</span>
                </li>
              ))}
            </ul>

            <Link
              to={plan.href}
              className={`mt-8 text-center px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                plan.highlighted
                  ? "bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100"
                  : "border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
              }`}
            >
              {plan.cta}
            </Link>
          </div>
        ))}
      </div>
      <p className="mt-8 text-center text-xs text-gray-400 dark:text-gray-500">
        Credit pricing is metered per request; see your account dashboard for current rates. No credit card required to start.
      </p>
    </section>
  );
}

export default Pricing;
