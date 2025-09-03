import React, { useState } from "react";
import { useDispatch } from "react-redux";
import { login } from "../redux/UserSlice";
import LoginComponent from "../subcomponents/login/LoginComponent.jsx";
import SignUpComponent from "../subcomponents/login/SignUpComponent";
import ForgotPasswordComponent from "../subcomponents/login/ForgotPasswordComponent";
import PasswordReset from "../subcomponents/login/PasswordReset";
import googleIcon from "../assets/google_button_blue_enh.png";
import "../styles/Login.css";

function LoginModal({ isOpen, onClose, productHash, freeTrialCode }) {
  const dispatch = useDispatch();

  const onLogin = () => {
    dispatch(
      login({
        product_hash: productHash,
        free_trial_code: freeTrialCode,
      })
    );
  };

  // 1: login, 2: sign up, 3: forget password, 4: password reset
  const [pageState, setPageState] = useState(1);
  const [statusMessage, setStatusMessage] = useState("");

  function setPageStateWithReset(newState) {
    setPageState(newState);
    setStatusMessage("");
  }

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-gray-900 rounded-xl border border-gray-700 p-6 w-full max-w-md mx-4 relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <svg
            className="w-6 h-6"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>

        {/* Logo and title */}
        <div className="text-center mb-6">
          <div className="flex items-center justify-center mb-2">
            <img src="logonew.png" className="w-8 h-8" alt="logo" />
            <span className="text-white text-xl font-semibold ml-2">
              Panacea
            </span>
          </div>
          <h2 className="text-lg text-[#F1CA57] font-medium">
            {pageState === 1
              ? "Welcome back"
              : pageState === 2
              ? "Create your account"
              : "Reset password"}
          </h2>
        </div>

        {/* Login/Signup forms */}
        <div className="text-white">
          {pageState === 1 && (
            <LoginComponent
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState === 2 && (
            <SignUpComponent
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState === 3 && (
            <ForgotPasswordComponent
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}
          {pageState === 4 && (
            <PasswordReset
              setPageState={setPageStateWithReset}
              statusMessage={statusMessage}
              setStatusMessage={setStatusMessage}
            />
          )}

          {/* Google login divider and button */}
          {pageState !== 3 && pageState !== 4 && (
            <>
              <div className="flex items-center my-4">
                <div className="flex-1 border-t border-gray-600"></div>
                <span className="px-3 text-gray-400 text-sm">Or</span>
                <div className="flex-1 border-t border-gray-600"></div>
              </div>
              <div className="text-center">
                <button
                  onClick={onLogin}
                  type="button"
                  className="login-with-google-btn-new"
                  style={{
                    backgroundImage: `url(${googleIcon})`,
                    textColor: "transparent",
                  }}
                />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default LoginModal;
