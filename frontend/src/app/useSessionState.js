import { useCallback, useEffect, useState } from "react";
import { useDispatch } from "react-redux";
import { viewUser } from "../redux/UserSlice";

function readLoggedInState() {
  return Boolean(
    localStorage.getItem("accessToken") || localStorage.getItem("sessionToken")
  );
}

export function useSessionState() {
  const dispatch = useDispatch();
  const [isLoggedIn, setIsLoggedIn] = useState(readLoggedInState);

  const refreshSession = useCallback(() => {
    setIsLoggedIn(readLoggedInState());
  }, []);

  useEffect(() => {
    refreshSession();
    window.addEventListener("storage", refreshSession);

    return () => {
      window.removeEventListener("storage", refreshSession);
    };
  }, [refreshSession]);

  useEffect(() => {
    if (isLoggedIn) {
      dispatch(viewUser());
    }
  }, [dispatch, isLoggedIn]);

  return {
    isLoggedIn,
    refreshSession,
  };
}
