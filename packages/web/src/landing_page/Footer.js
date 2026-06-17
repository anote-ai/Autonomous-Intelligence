import React from "react";
import RocketLogo from "../components/RocketLogo";

const FOOTER_LINKS = [
  { href: "#capabilities", label: "Capabilities" },
  { href: "#versions", label: "Product versions" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#faq", label: "FAQ" },
];

function Footer() {
  return (
    <footer className="border-t border-gray-200 dark:border-gray-700 py-10">
      <div className="mx-auto max-w-7xl px-6 flex flex-col sm:flex-row items-center justify-between gap-6 text-sm text-gray-500 dark:text-gray-400">
        <div className="flex items-center gap-2">
          <RocketLogo className="w-5 h-5" />
          <span>Panacea by Anote AI</span>
        </div>
        <div className="flex items-center gap-5">
          {FOOTER_LINKS.map((link) => (
            <a key={link.href} href={link.href} className="hover:text-gray-900 dark:hover:text-white">
              {link.label}
            </a>
          ))}
        </div>
        <p>&copy; {new Date().getFullYear()} Anote AI. All rights reserved.</p>
      </div>
    </footer>
  );
}

export default Footer;
