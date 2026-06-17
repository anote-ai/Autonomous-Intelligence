import React from "react";
import { Link } from "react-router-dom";
import RocketLogo from "../components/RocketLogo";

const FOOTER_COLUMNS = [
  {
    heading: "Product",
    links: [
      { href: "#capabilities", label: "Capabilities" },
      { href: "#versions", label: "Product versions" },
      { href: "#pricing", label: "Pricing" },
      { href: "#how-it-works", label: "How it works" },
    ],
  },
  {
    heading: "Surfaces",
    links: [
      { href: "#versions", label: "CLI" },
      { href: "#versions", label: "VS Code extension" },
      { href: "#versions", label: "Web app" },
      { href: "#versions", label: "Mobile" },
      { href: "#versions", label: "Desktop (on-prem)" },
      { href: "#versions", label: "SDK" },
    ],
  },
  {
    heading: "Resources",
    links: [
      { href: "#faq", label: "FAQ" },
      { href: "/register", label: "Create an account" },
      { href: "/login", label: "Sign in" },
    ],
  },
];

function Footer() {
  return (
    <footer className="border-t border-gray-200 dark:border-gray-700 py-12">
      <div className="mx-auto max-w-7xl px-6">
        <div className="grid gap-10 sm:grid-cols-2 md:grid-cols-4">
          <div>
            <div className="flex items-center gap-2">
              <RocketLogo className="w-6 h-6" />
              <span className="font-semibold">Panacea</span>
            </div>
            <p className="mt-3 text-sm text-gray-500 dark:text-gray-400">
              Anote's Autonomous Intelligence platform — one assistant, six ways to use it.
            </p>
          </div>

          {FOOTER_COLUMNS.map((column) => (
            <div key={column.heading}>
              <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{column.heading}</h3>
              <ul className="mt-3 space-y-2 text-sm">
                {column.links.map((link) =>
                  link.href.startsWith("/") ? (
                    <li key={link.label}>
                      <Link to={link.href} className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
                        {link.label}
                      </Link>
                    </li>
                  ) : (
                    <li key={link.label}>
                      <a href={link.href} className="text-gray-500 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white">
                        {link.label}
                      </a>
                    </li>
                  )
                )}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-10 pt-6 border-t border-gray-200 dark:border-gray-700 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-400 dark:text-gray-500">
          <p>&copy; {new Date().getFullYear()} Anote AI. All rights reserved.</p>
          <p>Panacea is built on Anote's shared Flask API, available across CLI, VS Code, web, mobile, desktop, and SDK.</p>
        </div>
      </div>
    </footer>
  );
}

export default Footer;
