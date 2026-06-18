import React, { useState } from "react";
import { Helmet } from "react-helmet-async";
import Navbar from "./Navbar";
import Footer from "./Footer";

const CONTACT_EMAIL = "nvidra@anote.ai";
const SLACK_INVITE_URL =
  "https://join.slack.com/t/anote-ai/shared_invite/zt-2vdh1p5xt-KWvtBZEprhrCzU6wrRPwNA";

function ContactPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");

  const submit = (e) => {
    e.preventDefault();
    const subject = `Panacea inquiry from ${name}`;
    const body = `${message}\n\n— ${name} (${email})`;
    window.location.href = `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(
      subject
    )}&body=${encodeURIComponent(body)}`;
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
          Questions about Panacea, enterprise or on-prem deployments, or partnerships? Send us a message, email us
          directly, or drop into our Slack community.
        </p>

        <div className="mt-6 flex flex-col sm:flex-row gap-4 text-sm">
          <a
            href={`mailto:${CONTACT_EMAIL}`}
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
          >
            Email {CONTACT_EMAIL}
          </a>
          <a
            href={SLACK_INVITE_URL}
            target="_blank"
            rel="noreferrer"
            className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
          >
            Join the Anote Slack
          </a>
        </div>

        <form onSubmit={submit} className="mt-8 space-y-4">
          <input
            type="text"
            required
            placeholder="Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
          />
          <input
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
          />
          <textarea
            required
            rows={5}
            placeholder="How can we help?"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            className="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-[#2F2F2F] text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-gray-400 dark:focus:ring-gray-500"
          />
          <button
            type="submit"
            className="px-6 py-3 rounded-lg font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors"
          >
            Send message
          </button>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            Sending opens your email client addressed to {CONTACT_EMAIL}.
          </p>
        </form>
      </main>
      <Footer />
    </div>
  );
}

export default ContactPage;
