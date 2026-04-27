import { createContext, useContext, useState, useEffect } from 'react';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [signedIn, setSignedIn] = useState(false);
  const [token, setToken] = useState(localStorage.getItem('authToken') || null);
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (token) {
      setSignedIn(true);
    }
  }, [token]);

  const login = (authToken, userData) => {
    setToken(authToken);
    setUser(userData);
    setSignedIn(true);
    localStorage.setItem('authToken', authToken);
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    setSignedIn(false);
    localStorage.removeItem('authToken');
  };

  return (
    <AuthContext.Provider value={{ 
      signedIn, 
      setSignedIn, 
      token, 
      user, 
      login, 
      logout 
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}
