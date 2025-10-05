import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const LANGUAGES_DATA = [
  {
    id: 1,
    name: "Spanish",
    nativeName: "Español",
    description: "Chat in Spanish with AI assistants",
    flag: "🇪🇸",
    chatPath: "/languages/spanish",
    speakers: "500M+ speakers",
  },
  {
    id: 2,
    name: "Chinese",
    nativeName: "中文",
    description: "Chat in Chinese with AI assistants",
    flag: "🇨🇳",
    chatPath: "/languages/chinese",
    speakers: "1.1B+ speakers",
  },
  {
    id: 3,
    name: "Japanese",
    nativeName: "日本語",
    description: "Chat in Japanese with AI assistants",
    flag: "🇯🇵",
    chatPath: "/languages/japanese",
    speakers: "125M+ speakers",
  },
  {
    id: 4,
    name: "Korean",
    nativeName: "한국어",
    description: "Chat in Korean with AI assistants",
    flag: "🇰🇷",
    chatPath: "/languages/korean",
    speakers: "77M+ speakers",
  },
  {
    id: 5,
    name: "Arabic",
    nativeName: "العربية",
    description: "Chat in Arabic with AI assistants",
    flag: "🇸🇦",
    chatPath: "/languages/arabic",
    speakers: "400M+ speakers",
  },
  {
    id: 6,
    name: "French",
    nativeName: "Français",
    description: "Chat in French with AI assistants (Coming Soon)",
    flag: "🇫🇷",
    chatPath: "/languages/french",
    speakers: "280M+ speakers",
    comingSoon: true,
  },
  {
    id: 7,
    name: "German",
    nativeName: "Deutsch",
    description: "Chat in German with AI assistants (Coming Soon)",
    flag: "🇩🇪",
    chatPath: "/languages/german",
    speakers: "100M+ speakers",
    comingSoon: true,
  },
  {
    id: 8,
    name: "Portuguese",
    nativeName: "Português",
    description: "Chat in Portuguese with AI assistants (Coming Soon)",
    flag: "🇵🇹",
    chatPath: "/languages/portuguese",
    speakers: "250M+ speakers",
    comingSoon: true,
  },
  {
  id: 9,
  name: "Anote",
  nativeName: "Anote AI Assistant",
  description: "Chat with Anote's AI assistant",
  flag: "A",
  chatPath: "/languages/anote",
  speakers: "AI-Powered Assistant",
  },
];

const LanguagesDirectory = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");

  const filteredLanguages = LANGUAGES_DATA.filter(
    (lang) =>
      lang.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      lang.nativeName.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleLanguageClick = (language) => {
    if (!language.comingSoon) {
      navigate(language.chatPath);
    }
  };

  return (
    <section className="min-h-screen bg-primary text-white px-4 py-10">
      <div className="container mx-auto max-w-6xl">
        <div className="flex flex-col text-center w-full mb-10">
          <h1 className="sm:text-5xl text-4xl font-extrabold title-font text-accent mb-4">
            Languages
          </h1>
          <p className="text-gray-300 max-w-2xl mx-auto">
            Chat with AI in your preferred language. Our multilingual assistants
            are ready to help.
          </p>
        </div>

        {/* Search */}
        <div className="mb-8 flex justify-center">
          <input
            type="text"
            placeholder="Search languages..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 rounded-lg bg-sidebar text-white placeholder-gray-400 border border-gray-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 max-w-md w-full"
          />
        </div>

        {/* Languages Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredLanguages.map((language) => (
            <div
              key={language.id}
              onClick={() => handleLanguageClick(language)}
              className={`bg-sidebar/20 border border-gray-600 hover:border-accent p-6 rounded-lg transition-all duration-300 ${
                language.comingSoon
                  ? "opacity-60 cursor-not-allowed"
                  : "cursor-pointer hover:transform hover:scale-105 hover:bg-sidebar/30"
              }`}
            >
              <div className="text-center">
                <div className="text-5xl mb-3">{language.flag}</div>
                <h3 className="text-xl font-semibold text-white mb-1">
                  {language.name}
                </h3>
                <p className="text-accent text-lg mb-2">
                  {language.nativeName}
                </p>
                <p className="text-gray-300 text-sm mb-3 leading-relaxed">
                  {language.description}
                </p>
                <p className="text-xs text-gray-400">{language.speakers}</p>
                {language.comingSoon && (
                  <div className="mt-3">
                    <span className="bg-accent/20 text-accent px-2 py-1 rounded text-xs">
                      Coming Soon
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {filteredLanguages.length === 0 && (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl text-gray-300 mb-2">No languages found</h3>
            <p className="text-gray-400">Try adjusting your search criteria</p>
          </div>
        )}

        {/* Additional Info */}
        <div className="mt-16 text-center">
          <div className="bg-sidebar/10 border border-gray-600 rounded-lg p-6 max-w-2xl mx-auto">
            <h3 className="text-xl font-semibold mb-3 text-accent">
              Multi-Language AI Support
            </h3>
            <p className="text-gray-300 text-sm leading-relaxed">
              Our AI assistants are trained to understand and respond in
              multiple languages, providing culturally appropriate and
              contextually accurate responses. Each language model is fine-tuned
              for optimal performance in that specific language.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default LanguagesDirectory;
