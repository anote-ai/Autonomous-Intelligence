import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const PERSONS_DATA = [
  {
    id: 1,
    name: "Bi Rong Liu",
    slug: "birongliu",
    title: "AI Engineer & Entrepreneur",
    company: "Anote AI",
    description:
      "AI engineer and entrepreneur specializing in autonomous intelligence systems",
    avatar: "👨‍💻",
    chatPath: "/person/birongliu",
    category: "Technology",
    expertise: [
      "AI",
      "Machine Learning",
      "Software Engineering",
      "Entrepreneurship",
    ],
    background:
      "AI researcher with expertise in multi-agent systems and autonomous intelligence",
  },
  {
    id: 2,
    name: "Elon Musk",
    slug: "elonmusk",
    title: "CEO & Entrepreneur",
    company: "Tesla, SpaceX, X",
    description:
      "Entrepreneur and business magnate known for electric vehicles, space exploration, and social media",
    avatar: "🚀",
    chatPath: "/person/elonmusk",
    category: "Business",
    expertise: [
      "Electric Vehicles",
      "Space Technology",
      "AI",
      "Business Strategy",
    ],
    background:
      "CEO of Tesla and SpaceX, known for advancing sustainable transport and space exploration",
  },
  {
    id: 3,
    name: "Sam Altman",
    slug: "samaltman",
    title: "CEO of OpenAI",
    company: "OpenAI",
    description:
      "AI researcher and entrepreneur leading the development of advanced AI systems",
    avatar: "🧠",
    chatPath: "/person/samaltman",
    category: "AI Research",
    expertise: [
      "Artificial Intelligence",
      "Startups",
      "Technology Strategy",
      "Product Development",
    ],
    background:
      "Former Y Combinator president, now leading OpenAI in developing safe and beneficial AI",
  },
  {
    id: 4,
    name: "Satya Nadella",
    slug: "satyanadella",
    title: "CEO of Microsoft",
    company: "Microsoft",
    description:
      "Technology executive leading Microsoft's cloud and AI transformation",
    avatar: "💼",
    chatPath: "/person/satyanadella",
    category: "Technology Leadership",
    expertise: [
      "Cloud Computing",
      "Enterprise Software",
      "AI Strategy",
      "Leadership",
    ],
    background:
      "Microsoft CEO since 2014, driving the company's transformation to cloud-first, AI-first",
  },
  {
    id: 5,
    name: "Jensen Huang",
    slug: "jensenhuang",
    title: "CEO of NVIDIA",
    company: "NVIDIA",
    description: "Technology visionary leading the AI computing revolution",
    avatar: "🎮",
    chatPath: "/person/jensenhuang",
    category: "Hardware",
    expertise: [
      "GPU Computing",
      "AI Hardware",
      "Graphics Technology",
      "Semiconductor",
    ],
    background:
      "NVIDIA co-founder and CEO, pioneering GPU computing for AI and graphics applications",
  },
  {
    id: 6,
    name: "Demis Hassabis",
    slug: "demishassabis",
    title: "CEO of Google DeepMind",
    company: "Google DeepMind",
    description:
      "AI researcher and neuroscientist advancing artificial general intelligence",
    avatar: "🔬",
    chatPath: "/person/demishassabis",
    category: "AI Research",
    expertise: [
      "Artificial General Intelligence",
      "Neuroscience",
      "Game AI",
      "Scientific Discovery",
    ],
    background:
      "Co-founder of DeepMind, leading breakthrough AI research in games, protein folding, and more",
  },
];

const PersonsDirectory = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const categories = [
    "All",
    ...new Set(PERSONS_DATA.map((person) => person.category)),
  ];

  const filteredPersons = PERSONS_DATA.filter((person) => {
    const matchesSearch =
      person.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.company.toLowerCase().includes(searchTerm.toLowerCase()) ||
      person.expertise.some((skill) =>
        skill.toLowerCase().includes(searchTerm.toLowerCase())
      );
    const matchesCategory =
      selectedCategory === "All" || person.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handlePersonClick = (person) => {
    navigate(person.chatPath);
  };

  return (
    <section className="min-h-screen bg-primary text-white px-4 py-10">
      <div className="container mx-auto max-w-6xl">
        <div className="flex flex-col text-center w-full mb-10">
          <h1 className="sm:text-5xl text-4xl font-extrabold title-font text-accent mb-4">
            Person
          </h1>
          <p className="text-gray-300 max-w-2xl mx-auto">
            Chat with AI assistants trained on specific individuals' knowledge,
            expertise, and public information
          </p>
        </div>

        {/* Search and Filter */}
        <div className="mb-8 flex flex-col sm:flex-row gap-4 items-center justify-center">
          <input
            type="text"
            placeholder="Search by name, company, or expertise..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 rounded-lg bg-sidebar text-white placeholder-gray-400 border border-gray-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 max-w-md w-full"
          />

          <select
            value={selectedCategory}
            onChange={(e) => setSelectedCategory(e.target.value)}
            className="px-4 py-2 rounded-lg bg-sidebar text-white border border-gray-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
          >
            {categories.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
        </div>

        {/* Persons Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredPersons.map((person) => (
            <div
              key={person.id}
              onClick={() => handlePersonClick(person)}
              className="bg-sidebar/20 border border-gray-600 hover:border-accent p-6 rounded-lg cursor-pointer transition-all duration-300 hover:transform hover:scale-105 hover:bg-sidebar/30"
            >
              <div className="flex items-start mb-4">
                <div className="text-4xl mr-4 flex-shrink-0">
                  {person.avatar}
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-xl font-semibold text-white mb-1 truncate">
                    {person.name}
                  </h3>
                  <p className="text-accent text-sm mb-1">{person.title}</p>
                  <p className="text-gray-400 text-sm">{person.company}</p>
                </div>
              </div>

              <p className="text-gray-300 text-sm mb-4 leading-relaxed">
                {person.description}
              </p>

              <div className="mb-4">
                <div className="flex flex-wrap gap-1">
                  {person.expertise.slice(0, 3).map((skill, index) => (
                    <span
                      key={index}
                      className="bg-accent/20 text-accent px-2 py-1 rounded text-xs"
                    >
                      {skill}
                    </span>
                  ))}
                  {person.expertise.length > 3 && (
                    <span className="text-gray-400 text-xs px-2 py-1">
                      +{person.expertise.length - 3} more
                    </span>
                  )}
                </div>
              </div>

              <div className="border-t border-gray-600 pt-3">
                <p className="text-xs text-gray-400 leading-relaxed">
                  {person.background}
                </p>
              </div>
            </div>
          ))}
        </div>

        {filteredPersons.length === 0 && (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl text-gray-300 mb-2">No persons found</h3>
            <p className="text-gray-400">
              Try adjusting your search or filter criteria
            </p>
          </div>
        )}

        {/* Disclaimer */}
        <div className="mt-16 text-center">
          <div className="bg-sidebar/10 border border-gray-600 rounded-lg p-6 max-w-3xl mx-auto">
            <h3 className="text-xl font-semibold mb-3 text-accent">
              Important Note
            </h3>
            <p className="text-gray-300 text-sm leading-relaxed">
              These AI assistants are trained on publicly available information
              about these individuals. They provide responses based on known
              facts, interviews, writings, and public statements. The responses
              do not represent the actual views or opinions of these
              individuals, and should be used for informational and educational
              purposes only.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
};

export default PersonsDirectory;
