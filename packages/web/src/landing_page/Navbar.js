import React, { useState } from "react";
import { Link } from "react-router-dom";
import RocketLogo from "../components/RocketLogo";
import { useTheme } from "../App";

const NAV_LINKS = [
  { href: "#capabilities", label: "Capabilities" },
  { href: "#versions", label: "Product versions" },
  { href: "#pricing", label: "Pricing" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#faq", label: "FAQ" },
];

function Navbar() {
  const { dark, toggle } = useTheme();
  const [open, setOpen] = useState(false);

  return (
    <nav className="sticky top-0 z-50 border-b border-gray-200 dark:border-gray-700 bg-white/90 dark:bg-[#212121]/90 backdrop-blur">
      <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <RocketLogo className="w-7 h-7" />
          <span className="font-semibold">Panacea</span>
          <span className="hidden sm:inline text-gray-400 dark:text-gray-500 text-sm">by Anote</span>
        </div>

        <div className="hidden md:flex items-center gap-6 text-sm text-gray-600 dark:text-gray-300">
          {NAV_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-gray-900 dark:hover:text-white">
              {link.label}
            </a>
          ))}
        </div>

        <div className="hidden md:flex items-center gap-3">
          <button
            onClick={toggle}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400"
            aria-label="Toggle dark mode"
          >
            {dark ? "☀️" : "🌙"}
          </button>
          <Link
            to="/login"
            className="px-4 py-2 rounded-lg text-sm font-medium text-gray-900 dark:text-white hover:bg-gray-100 dark:hover:bg-[#2F2F2F]"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100"
          >
            Get started
          </Link>
        </div>

        <button
          className="md:hidden p-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-200"
          onClick={() => setOpen((o) => !o)}
          aria-label="Toggle menu"
          aria-expanded={open}
        >
          {open ? "✕" : "☰"}
        </button>
      </div>

      <div
        className={`md:hidden overflow-hidden border-t border-gray-200 dark:border-gray-700 transition-all duration-300 ${
          open ? "max-h-96" : "max-h-0"
        }`}
      >
        <div className="px-6 py-4 flex flex-col gap-3 text-sm">
          {NAV_LINKS.map((link) => (
            <a
              key={link.href}
              href={link.href}
              onClick={() => setOpen(false)}
              className="py-1 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
            >
              {link.label}
            </a>
          ))}
          <div className="flex items-center gap-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            <button
              onClick={toggle}
              className="p-2 rounded-lg border border-gray-300 dark:border-gray-600 text-gray-500 dark:text-gray-400"
              aria-label="Toggle dark mode"
            >
              {dark ? "☀️" : "🌙"}
            </button>
            <Link
              to="/login"
              onClick={() => setOpen(false)}
              className="flex-1 text-center px-4 py-2 rounded-lg text-sm font-medium border border-gray-300 dark:border-gray-600"
            >
              Sign in
            </Link>
            <Link
              to="/register"
              onClick={() => setOpen(false)}
              className="flex-1 text-center px-4 py-2 rounded-lg text-sm font-medium bg-gray-900 dark:bg-white text-white dark:text-gray-900"
            >
              Get started
            </Link>
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
