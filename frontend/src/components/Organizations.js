import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

const ORGANIZATIONS = [
  {
    id: 1,
    name: "Microsoft",
    description:
      "Technology corporation specializing in software, services, and solutions",
    logo: "🏢",
    chatPath: "/organizations/microsoft",
    category: "Technology",
  },
  {
    id: 2,
    name: "Google",
    description:
      "Multinational technology company focusing on internet-related services",
    logo: "🔍",
    chatPath: "/organizations/google",
    category: "Technology",
  },
  {
    id: 3,
    name: "Apple",
    description:
      "Technology company known for consumer electronics and software",
    logo: "🍎",
    chatPath: "/organizations/apple",
    category: "Technology",
  },
  {
    id: 4,
    name: "Amazon",
    description: "E-commerce and cloud computing company",
    logo: "📦",
    chatPath: "/organizations/amazon",
    category: "E-commerce",
  },
  {
    id: 5,
    name: "Tesla",
    description: "Electric vehicle and clean energy company",
    logo: "⚡",
    chatPath: "/organizations/tesla",
    category: "Automotive",
  },
  {
    id: 6,
    name: "Meta",
    description: "Social media and virtual reality technology company",
    logo: "🌐",
    chatPath: "/organizations/meta",
    category: "Social Media",
  },
];

const Organizations = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("All");

  const categories = [
    "All",
    ...new Set(ORGANIZATIONS.map((org) => org.category)),
  ];

  const filteredOrganizations = ORGANIZATIONS.filter((org) => {
    const matchesSearch =
      org.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      org.description.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesCategory =
      selectedCategory === "All" || org.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleOrganizationClick = (org) => {
    navigate(org.chatPath);
  };

  return (
    <section className="min-h-screen bg-primary text-white px-4 py-10">
      <div className="container mx-auto max-w-6xl">
        <div className="flex flex-col text-center w-full mb-10">
          <h1 className="sm:text-5xl text-4xl font-extrabold title-font text-accent mb-4">
            Organizations
          </h1>
          <p className="text-gray-300 max-w-2xl mx-auto">
            Chat with AI assistants trained on specific organizations' data and
            knowledge
          </p>
        </div>

        {/* Search and Filter */}
        <div className="mb-8 flex flex-col sm:flex-row gap-4 items-center justify-center">
          <input
            type="text"
            placeholder="Search organizations..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="px-4 py-2 rounded-lg bg-sidebar text-white placeholder-gray-400 border border-gray-600 focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20"
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

        {/* Organizations Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredOrganizations.map((org) => (
            <div
              key={org.id}
              onClick={() => handleOrganizationClick(org)}
              className="bg-sidebar/20 border border-gray-600 hover:border-accent p-6 rounded-lg cursor-pointer transition-all duration-300 hover:transform hover:scale-105 hover:bg-sidebar/30"
            >
              <div className="flex items-center mb-4">
                <div className="text-4xl mr-4">{org.logo}</div>
                <div>
                  <h3 className="text-xl font-semibold text-white">
                    {org.name}
                  </h3>
                  <span className="text-sm text-accent">{org.category}</span>
                </div>
              </div>
              <p className="text-gray-300 text-sm leading-relaxed">
                {org.description}
              </p>
            </div>
          ))}
        </div>

        {filteredOrganizations.length === 0 && (
          <div className="text-center py-12">
            <div className="text-4xl mb-4">🔍</div>
            <h3 className="text-xl text-gray-300 mb-2">
              No organizations found
            </h3>
            <p className="text-gray-400">
              Try adjusting your search or filter criteria
            </p>
          </div>
        )}
      </div>
    </section>
  );
};

export default Organizations;
