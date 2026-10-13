import React, { createContext, useContext, useState, useEffect } from 'react';

export type Theme = 'light' | 'dark';

interface ThemeContextType {
  theme: Theme;
  toggleTheme: () => void;
  setTheme: (theme: Theme) => void;
}

const ThemeContext = createContext<ThemeContextType>({
  theme: 'dark',
  toggleTheme: () => {},
  setTheme: () => {},
});

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      const saved = localStorage.getItem('qresq-theme');
      if (saved === 'light' || saved === 'dark') {
        return saved;
      }
    } catch {
      // Ignore localStorage access restrictions
    }
    return 'dark'; // Default to Dark Mode as required
  });

  useEffect(() => {
    try {
      localStorage.setItem('qresq-theme', theme);
    } catch {
      // Ignore
    }

    const root = document.documentElement;
    if (theme === 'light') {
      root.classList.remove('dark');
      root.classList.add('light');
      root.style.colorScheme = 'light';
      document.body.style.backgroundColor = '#f8fafc';
      document.body.style.color = '#0f172a';
    } else {
      root.classList.add('dark');
      root.classList.remove('light');
      root.style.colorScheme = 'dark';
      document.body.style.backgroundColor = '#060911';
      document.body.style.color = '#f1f5f9';
    }
  }, [theme]);

  const toggleTheme = () => {
    setThemeState((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  const setTheme = (t: Theme) => {
    setThemeState(t);
  };

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => useContext(ThemeContext);
