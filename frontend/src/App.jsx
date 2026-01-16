import { useState } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Navbar from "./components/navigation/Navbar";
import ProfileSettings from "./components/profile/ProfileSettings";
import AuthModal from "./components/authentication/AuthModal";
import ChatInterface from "./components/chat/ChatInterface";
import { ThemeProvider } from "./context/ThemeContext";
import { AuthProvider } from "./context/AuthContext";
import { ChatHistoryProvider } from "./context/ChatHistoryContext";
import { useAuth } from "./hooks/useAuth";
import { useTheme } from "./hooks/useTheme";

function AppContent() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const { theme } = useTheme();
  const {
    user,
    isAuthenticated,
    logout,
    openAuthModal,
  } = useAuth();

  const handleLogout = async () => {
    await logout();
    setIsProfileOpen(false);
    setIsSidebarOpen(false);
  };

  const element = (
    <ChatInterface
      userData={user}
      isSidebarOpen={isSidebarOpen}
      isAuthenticated={isAuthenticated}
    />
  );

  return (
    <ChatHistoryProvider isAuthenticated={isAuthenticated}>
      <div
        className={`min-h-screen flex transition-colors ${
          theme === "dark" ? "bg-gray-900" : "bg-gray-50"
        }`}
      >
        <Navbar
          isSidebarOpen={isSidebarOpen}
          setIsSidebarOpen={setIsSidebarOpen}
          isProfileOpen={isProfileOpen}
          setIsProfileOpen={setIsProfileOpen}
          setIsAuthOpen={openAuthModal}
          isAuthenticated={isAuthenticated}
        />

        <Routes>
          <Route path="/" element={element} />
          <Route path="/chats/:chatId" element={element} />
          <Route path="/shares/:shareId" element={element} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>

        {isAuthenticated && (
          <ProfileSettings
            isOpen={isProfileOpen}
            onClose={() => setIsProfileOpen(false)}
            onLogout={handleLogout}
            userData={user}
          />
        )}
        <AuthModal />
      </div>
    </ChatHistoryProvider>
  );
}

function AppWithLoading() {
  const { theme } = useTheme();
  const { isLoading } = useAuth();
  if (isLoading) {
    return (
      <div
        className={`min-h-screen flex items-center justify-center ${
          theme === "dark" ? "bg-gray-900" : "bg-gray-50"
        }`}
      >
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
          <p
            className={`mt-4 ${
              theme === "dark" ? "text-gray-400" : "text-gray-600"
            }`}
          >
            Loading...
          </p>
        </div>
      </div>
    );
  }

  return <AppContent />;
}

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <BrowserRouter>
          <AppWithLoading />
        </BrowserRouter>
      </AuthProvider>
    </ThemeProvider>
  );
}

export default App;
