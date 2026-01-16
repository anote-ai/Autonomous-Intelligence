import { createContext, useState, useCallback, useEffect } from "react";
import { authAPI, APIError } from "../utils/api";

const AuthContext = createContext(null);

/**
 * AuthProvider manages authentication state and provides auth methods
 * to all child components via context
 */
function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  /**
   * Check authentication status on mount and after page reload
   */
  const checkAuth = useCallback(async () => {
    try {
      setError(null);
      const data = await authAPI.checkAuth();
      setUser({
        name: data.username,
        email: data.email,
      });
      setIsAuthenticated(true);
    } catch (err) {
      // If auth check fails, user is not authenticated
      setUser(null);
      setIsAuthenticated(false);
      // Only set error if it's not a 401 (unauthorized)
      if (err instanceof APIError && err.status !== 401) {
        setError(err.message);
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  /**
   * Login with email and password
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  const login = async (email, password) => {
    try {
      setError(null);
      setIsLoading(true);

      const data = await authAPI.login(email, password);

      setUser({
        name: data.username,
        email: data.email,
      });
      setIsAuthenticated(true);

      return { success: true };
    } catch (err) {
      const errorMessage =
        err instanceof APIError
          ? err.message
          : "Login failed. Please try again.";

      setError(errorMessage);
      setIsAuthenticated(false);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Sign up new user
   * @param {string} username
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{success: boolean, error?: string}>}
   */
  const signup = async (username, email, password) => {
    try {
      setError(null);
      setIsLoading(true);

      const data = await authAPI.signup(username, email, password);

      setUser({
        name: data.username,
        email: data.email,
      });
      setIsAuthenticated(true);

      return { success: true };
    } catch (err) {
      const errorMessage =
        err instanceof APIError
          ? err.message
          : "Signup failed. Please try again.";

      setError(errorMessage);
      return { success: false, error: errorMessage };
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Logout current user
   */
  const logout = async () => {
    try {
      setError(null);
      await authAPI.logout();
    } catch (err) {
      // Log error but still clear local state
      console.error("Logout request failed:", err);
    } finally {
      // Always clear local state even if API call fails
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  /**
   * Clear any auth errors
   */
  const clearError = () => {
    setError(null);
  };

  /**
   * Manually refresh user data (useful after profile updates)
   */
  const refreshUser = async () => {
    if (isAuthenticated) {
      await checkAuth();
    }
  };

  /**
   * Open auth modal
   */
  const openAuthModal = () => {
    setIsAuthModalOpen(true);
  };

  /**
   * Close auth modal
   */
  const closeAuthModal = () => {
    setIsAuthModalOpen(false);
  };

  // Check auth on mount
  useEffect(() => {
    try {
      checkAuth();
    } catch {
      console.log("lol")
    }
  }, [checkAuth]);

  // Auto-close auth modal on successful authentication
  useEffect(() => {
    if (isAuthenticated && isAuthModalOpen) {
      closeAuthModal();
    }
  }, [isAuthenticated, isAuthModalOpen]);

  const value = {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    signup,
    logout,
    clearError,
    refreshUser,
    isAuthModalOpen,
    openAuthModal,
    closeAuthModal,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export { AuthContext, AuthProvider };
