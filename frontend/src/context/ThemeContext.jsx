import { useEffect, useState, createContext } from "react";
const ThemeContext = createContext();

const ThemeProvider = ({ children }) => {
  const [theme, setTheme] = useState(() => {
    // Check localStorage first, then system preference
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme) return savedTheme;

    return window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark"
      : "light";
  });

  useEffect(() => {
    const root = window.document.documentElement;

    console.log("useEffect running - theme is:", theme);

    if (theme === "dark") {
      root.classList.add("dark");
      console.log("Added 'dark' class to html element");
    } else {
      root.classList.remove("dark");
      console.log("Removed 'dark' class from html element");
    }

    localStorage.setItem("theme", theme);
    console.log("Saved to localStorage:", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prevTheme) => {
      const newTheme = prevTheme === "light" ? "dark" : "light";
      console.log("Toggling theme from", prevTheme, "to", newTheme);
      return newTheme;
    });
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};


export { ThemeContext, ThemeProvider }