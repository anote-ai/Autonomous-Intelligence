import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

function GetStarted() {
  const [email, setEmail] = useState("");
  const nav = useNavigate();

  const submit = (e) => {
    e.preventDefault();
    const params = email ? `?email=${encodeURIComponent(email)}` : "";
    nav(`/register${params}`);
  };

  return (
    <section className="mx-auto max-w-5xl px-6 py-16 border-t border-gray-200 dark:border-gray-700 text-center">
      <h2 className="text-2xl sm:text-3xl font-semibold">Ready to put Autonomous Intelligence to work?</h2>
      <p className="mt-4 text-gray-600 dark:text-gray-300">
        Create a free account and start from the web, then install whichever other surfaces you need.
      </p>

      <form onSubmit={submit} className="mt-8 mx-auto max-w-md flex flex-col sm:flex-row gap-3">
        <input
          type="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@company.com"
          className="flex-1 px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
        />
        <button
          type="submit"
          className="px-6 py-3 rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors whitespace-nowrap"
        >
          Get started with Panacea
        </button>
      </form>
      <p className="mt-3 text-xs text-gray-400 dark:text-gray-500">No credit card required.</p>
    </section>
  );
}

export default GetStarted;
