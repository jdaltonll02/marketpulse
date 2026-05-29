import { createContext, useContext, useState, useCallback } from "react";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // localStorage used for demo purposes — production would use httpOnly cookies
  const [token, setToken] = useState(() => localStorage.getItem("mp_token") || null);
  const [user,  setUser]  = useState(() => {
    try { return JSON.parse(localStorage.getItem("mp_user") || "null"); }
    catch { return null; }
  });

  const login = useCallback((tokenVal, userInfo) => {
    setToken(tokenVal);
    setUser(userInfo);
    localStorage.setItem("mp_token", tokenVal);
    localStorage.setItem("mp_user", JSON.stringify(userInfo));
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
    localStorage.removeItem("mp_token");
    localStorage.removeItem("mp_user");
  }, []);

  return (
    <AuthContext.Provider value={{
      token,
      user,
      login,
      logout,
      isAuth:  !!token,
      isAdmin: user?.role === "admin",
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
