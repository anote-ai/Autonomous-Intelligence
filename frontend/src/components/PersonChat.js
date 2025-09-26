import React, { useState, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";

// Person data - in a real app, this would come from an API or database
const PERSONS_KNOWLEDGE = {
  birongliu: {
    name: "Bi Rong Liu",
    title: "AI Engineer & Entrepreneur",
    company: "Anote AI",
    avatar: "👨‍💻",
    knowledge: {
      background:
        "AI engineer and entrepreneur specializing in autonomous intelligence systems. Currently working on multi-agent AI systems and intelligent automation platforms.",
      expertise: [
        "Artificial Intelligence",
        "Machine Learning",
        "Multi-Agent Systems",
        "Software Engineering",
        "Entrepreneurship",
      ],
      experience:
        "Has experience in developing AI-powered systems, working with large language models, and building scalable software solutions. Currently focused on autonomous intelligence platforms.",
      personality:
        "Technical, innovative, focused on practical AI applications and building useful systems.",
      projects:
        "Working on advanced AI systems including multi-agent frameworks, autonomous intelligence platforms, and AI-powered automation tools.",
    },
  },
  elonmusk: {
    name: "Elon Musk",
    title: "CEO & Entrepreneur",
    company: "Tesla, SpaceX, X",
    avatar: "🚀",
    knowledge: {
      background:
        "Entrepreneur and business magnate known for his work in electric vehicles, space exploration, and social media. CEO of Tesla and SpaceX.",
      expertise: [
        "Electric Vehicles",
        "Space Technology",
        "Sustainable Energy",
        "Neural Interfaces",
        "Business Strategy",
      ],
      experience:
        "Founded and leads multiple companies including Tesla (electric vehicles), SpaceX (space exploration), Neuralink (brain-computer interfaces), and X (social media).",
      personality:
        "Visionary, ambitious, focused on advancing humanity through technology and sustainable solutions.",
      projects:
        "Leading efforts in electric vehicle adoption, Mars colonization, sustainable energy, and advanced AI development.",
    },
  },
  samaltman: {
    name: "Sam Altman",
    title: "CEO of OpenAI",
    company: "OpenAI",
    avatar: "🧠",
    knowledge: {
      background:
        "AI researcher and entrepreneur leading OpenAI, the company behind GPT and ChatGPT. Former president of Y Combinator.",
      expertise: [
        "Artificial Intelligence",
        "Startups",
        "Technology Strategy",
        "Product Development",
        "AI Safety",
      ],
      experience:
        "Led Y Combinator from 2014-2019, helping launch hundreds of startups. Now leading OpenAI in developing advanced AI systems safely.",
      personality:
        "Strategic thinker, focused on AI safety and beneficial AI development, strong background in startup ecosystem.",
      projects:
        "Leading development of GPT models, ChatGPT, and working on artificial general intelligence (AGI) research.",
    },
  },
};

const PersonChat = () => {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [messages, setMessages] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const personData = PERSONS_KNOWLEDGE[slug];

  useEffect(() => {
    if (!personData) {
      navigate("/person");
      return;
    }

    // Initialize with a welcome message
    setMessages([
      {
        id: 1,
        content: `Hello! I'm an AI assistant trained on publicly available information about ${personData.name}. I can discuss their background, expertise, and publicly known work. What would you like to know?`,
        isUser: false,
        timestamp: new Date(),
      },
    ]);
  }, [slug, personData, navigate]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const generateResponse = (userMessage) => {
    if (!personData) return "I don't have information about this person.";

    const message = userMessage.toLowerCase();
    const knowledge = personData.knowledge;

    // Simple keyword-based responses - in a real app, this would use an AI API
    if (
      message.includes("background") ||
      message.includes("about") ||
      message.includes("who")
    ) {
      return `${knowledge.background} ${
        personData.name
      } has expertise in ${knowledge.expertise.join(", ")}.`;
    }

    if (
      message.includes("experience") ||
      message.includes("work") ||
      message.includes("career")
    ) {
      return knowledge.experience;
    }

    if (
      message.includes("project") ||
      message.includes("working on") ||
      message.includes("current")
    ) {
      return knowledge.projects;
    }

    if (
      message.includes("expertise") ||
      message.includes("skills") ||
      message.includes("good at")
    ) {
      return `${personData.name} has expertise in: ${knowledge.expertise.join(
        ", "
      )}. ${knowledge.experience}`;
    }

    if (
      message.includes("personality") ||
      message.includes("like") ||
      message.includes("character")
    ) {
      return knowledge.personality;
    }

    // Default response
    return `Based on publicly available information, ${personData.name} is ${
      knowledge.background
    }. Their main areas of expertise include ${knowledge.expertise
      .slice(0, 3)
      .join(
        ", "
      )}. Is there something specific you'd like to know about their work or background?`;
  };

  const handleSend = async () => {
    if (!inputValue.trim() || isLoading) return;

    const userMessage = {
      id: Date.now(),
      content: inputValue.trim(),
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue("");
    setIsLoading(true);

    // Simulate API delay
    setTimeout(() => {
      const botResponse = {
        id: Date.now() + 1,
        content: generateResponse(userMessage.content),
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, botResponse]);
      setIsLoading(false);
    }, 1000 + Math.random() * 1000); // Random delay between 1-2 seconds
  };

  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!personData) {
    return null; // Will redirect in useEffect
  }

  return (
    <div className="min-h-screen bg-primary text-white flex flex-col">
      {/* Header */}
      <div className="bg-sidebar/20 border-b border-gray-600 p-4">
        <div className="container mx-auto max-w-4xl flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => navigate("/person")}
              className="text-accent hover:text-accent-light transition-colors"
            >
              ← Back to Persons
            </button>
            <div className="flex items-center space-x-3">
              <div className="text-3xl">{personData.avatar}</div>
              <div>
                <h1 className="text-xl font-semibold">{personData.name}</h1>
                <p className="text-sm text-gray-400">
                  {personData.title} • {personData.company}
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Chat Messages */}
      <div className="flex-1 container mx-auto max-w-4xl p-4 overflow-y-auto">
        <div className="space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${
                message.isUser ? "justify-end" : "justify-start"
              }`}
            >
              <div
                className={`max-w-xs lg:max-w-md xl:max-w-lg px-4 py-3 rounded-lg ${
                  message.isUser
                    ? "bg-accent text-white"
                    : "bg-sidebar/20 text-gray-100"
                }`}
              >
                <p className="text-sm leading-relaxed">{message.content}</p>
                <p className="text-xs opacity-70 mt-2">
                  {message.timestamp.toLocaleTimeString([], {
                    hour: "2-digit",
                    minute: "2-digit",
                  })}
                </p>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-sidebar/20 text-gray-100 px-4 py-3 rounded-lg">
                <div className="flex items-center space-x-2">
                  <div className="animate-pulse">💭</div>
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Input Area */}
      <div className="bg-sidebar/10 border-t border-gray-600 p-4">
        <div className="container mx-auto max-w-4xl">
          <div className="flex space-x-3">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder={`Ask about ${personData.name}...`}
              className="flex-1 px-4 py-3 bg-primary border border-gray-600 rounded-lg focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/20 text-white placeholder-gray-400"
            />
            <button
              onClick={handleSend}
              disabled={!inputValue.trim() || isLoading}
              className="px-6 py-3 bg-accent hover:bg-accent-dark disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
            >
              Send
            </button>
          </div>

          {/* Disclaimer */}
          <p className="text-xs text-gray-400 mt-2 text-center">
            This AI assistant provides information based on publicly available
            data about {personData.name}. Responses do not represent their
            actual views or opinions.
          </p>
        </div>
      </div>
    </div>
  );
};

export default PersonChat;
