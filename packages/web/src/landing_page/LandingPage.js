import React from "react";
import { Helmet } from "react-helmet-async";
import Navbar from "./Navbar";
import Hero from "./Hero";
import Capabilities from "./Capabilities";
import ProductVersions from "./ProductVersions";
import Pricing from "./Pricing";
import HowItWorks from "./HowItWorks";
import FAQSection from "./FAQSection";
import GetStarted from "./GetStarted";
import Footer from "./Footer";
import { PRODUCT_VERSIONS, FAQS } from "./landingPageData";

const softwareSchema = {
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  name: "Panacea",
  applicationCategory: "DeveloperApplication",
  operatingSystem: "Web, macOS, Windows, Linux, iOS, Android",
  description:
    "Panacea is an Autonomous Intelligence platform from Anote that ships as a coding CLI, VS Code extension, web chatbot, mobile app, desktop app, and SDK, all backed by a shared Flask API.",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
  },
};

const howToSchema = {
  "@context": "https://schema.org",
  "@type": "HowTo",
  name: "How to use Panacea, the Autonomous Intelligence platform",
  description:
    "Panacea by Anote ships as a CLI, VS Code extension, web chatbot, mobile app, desktop app, and SDK. Here is how to get started with each.",
  step: PRODUCT_VERSIONS.map((v, i) => ({
    "@type": "HowToStep",
    position: i + 1,
    name: v.fullName,
    text: v.description,
  })),
};

const faqSchema = {
  "@context": "https://schema.org",
  "@type": "FAQPage",
  mainEntity: FAQS.map((faq) => ({
    "@type": "Question",
    name: faq.question,
    acceptedAnswer: {
      "@type": "Answer",
      text: faq.answer,
    },
  })),
};

function LandingPage() {
  return (
    <div className="min-h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white">
      <Helmet>
        <title>Panacea by Anote | Autonomous Intelligence Platform</title>
        <meta
          name="description"
          content="Panacea is Anote's Autonomous Intelligence platform: a coding CLI, VS Code extension, web chatbot, mobile app, desktop app, and SDK, all powered by one Flask backend. See how to use every version."
        />
        <meta
          name="keywords"
          content="Panacea, Anote, autonomous intelligence, AI agent, coding CLI, VS Code extension, AI chatbot, AI SDK, private AI desktop app, autonomous AI platform"
        />
        <link rel="canonical" href="https://anote.ai/" />
        <meta property="og:type" content="website" />
        <meta property="og:title" content="Panacea by Anote | Autonomous Intelligence Platform" />
        <meta
          property="og:description"
          content="One Autonomous Intelligence platform, six ways to use it: CLI, VS Code, web, mobile, desktop, and SDK."
        />
        <meta property="og:url" content="https://anote.ai/" />
        <meta name="twitter:card" content="summary_large_image" />
        <script type="application/ld+json">{JSON.stringify(softwareSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(howToSchema)}</script>
        <script type="application/ld+json">{JSON.stringify(faqSchema)}</script>
      </Helmet>

      <Navbar />
      <main>
        <Hero />
        <Capabilities />
        <ProductVersions />
        <Pricing />
        <HowItWorks />
        <FAQSection />
        <GetStarted />
      </main>
      <Footer />
    </div>
  );
}

export default LandingPage;
