import { useState } from "react";
import Navbar from "./components/navigation/Navbar";
import ProfileSettings from "./components/profile/ProfileSettings";
import AuthModal from "./components/authentication/AuthModal";
import ChatInterface from "./components/chat/ChatInterface";
import { ThemeProvider } from "./context/ThemeContext";
import { useTheme } from "./hooks/useTheme";

function AppContent() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [userData, setUserData] = useState({ name: "", email: "" });
  const { theme } = useTheme();

  const handleLogin = (user) => {
    setUserData(user);
    setIsAuthenticated(true);
    setIsAuthOpen(false);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    setIsProfileOpen(false);
    setIsSidebarOpen(false);
    setUserData({ name: "", email: "" });
  };

  return (
    <div
      className={`min-h-screen flex transition-colors ${
        theme === "dark" ? "bg-gray-900" : "bg-white"
      }`}
    >
      <Navbar
        isSidebarOpen={isSidebarOpen}
        setIsSidebarOpen={setIsSidebarOpen}
        isProfileOpen={isProfileOpen}
        setIsProfileOpen={setIsProfileOpen}
        setIsAuthOpen={setIsAuthOpen}
        isAuthenticated={isAuthenticated}
      />

      <ChatInterface
        userData={userData}
        isSidebarOpen={isSidebarOpen}
        isAuthenticated={isAuthenticated}
      />

      {isAuthenticated && (
        <ProfileSettings
          isOpen={isProfileOpen}
          onClose={() => setIsProfileOpen(false)}
          onLogout={handleLogout}
          userData={userData}
        />
      )}

      <AuthModal
        isOpen={isAuthOpen}
        onClose={() => setIsAuthOpen(false)}
        onLogin={handleLogin}
      />
    </div>
  );
}

function App() {
  return (
    <ThemeProvider>
      <AppContent />
    </ThemeProvider>
  );
}

export default App;
