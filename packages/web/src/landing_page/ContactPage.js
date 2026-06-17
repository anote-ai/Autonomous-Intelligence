import React, { useState } from "react";
import { Helmet } from "react-helmet-async";
import Navbar from "./Navbar";
import Footer from "./Footer";

function ContactPage() {
  const [submitted, setSubmitted] = useState(false);

  const submit = (e) => {
    e.preventDefault();
    setSubmitted(true);
  };

  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white flex flex-col">
      <Helmet>
        <title>Contact Anote | Panacea</title>
        <meta
          name="description"
          content="Get in touch with the Anote team about Panacea, enterprise deployments, or partnership opportunities."
        />
        <link rel="canonical" href="https://anote.ai/contact" />
      </Helmet>

      <Navbar />
      <main className="flex-1 mx-auto max-w-2xl w-full px-6 py-16">
        <h1 className="text-3xl font-semibold">Contact us</h1>
        <p className="mt-4 text-gray-600 dark:text-gray-300">
          Questions about Panacea, enterprise or on-prem deployments, or partnerships? Send us a message and we'll
          get back to you.
        </p>

        {submitted ? (
          <p className="mt-8 rounded-lg border border-gray-200 dark:border-gray-700 p-4 text-sm">
            Thanks for reaching out — we'll reply to your email shortly.
          </p>
        ) : (
          <form onSubmit={submit} className="mt-8 space-y-4">
            <input
              type="text"
              required
              placeholder="Name"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
            />
            <input
              type="email"
              required
              placeholder="Email"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
            />
            <textarea
              required
              rows={5}
              placeholder="How can we help?"
              className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
            />
            <button
              type="submit"
              className="px-6 py-3 rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors"
            >
              Send message
            </button>
          </form>
        )}
      </main>
      <Footer />
    </div>
  );
}

export default ContactPage;
