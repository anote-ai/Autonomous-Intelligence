import React, { useState, useEffect } from "react";
//import NavLinks from "./NavLinksChatbot"; Changed from using nav to showing all on same page
import Switch from "react-switch";
import fetcher from "../../http/RequestConfig";
import { useDispatch } from "react-redux";
import { logout } from "../../redux/UserSlice";
import { useNavigate } from "react-router-dom";

function NavbarChatbot(props) {
  const dispatch = useDispatch();
  const navigate = useNavigate();
  const [showUserDropdown, setShowUserDropdown] = useState(false);

  const handleLogout = () => {
    dispatch(logout()).then((resp) => {
      navigate("/");
      if (props.setIsLoggedInParent) {
        props.setIsLoggedInParent(false);
      }
      // Reload the page to reset state
      window.location.reload();
    });
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showUserDropdown && !event.target.closest('.user-dropdown')) {
        setShowUserDropdown(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showUserDropdown]);

  const urlObject = new URL(window.location.origin);
  var hostname = urlObject.hostname;
  if (hostname.startsWith("www.")) {
    hostname = hostname.substring(4);
  }
  urlObject.hostname = `dashboard.${hostname}`;

  return (
    <nav className="fixed top-0 left-0 right-0 bg-anoteblack-900 z-50">
      <div className="flex items-center justify-between px-4 py-4 max-w-7xl mx-auto">
        {/* Left side - Sidebar toggle and Brand name */}
        <div className="flex items-center space-x-3">
          {/* Sidebar toggle button - only show when logged in */}
          {!props.isGuestMode && (
            <button
              onClick={props.handleMenu}
              className="p-2 text-gray-400 hover:text-white hover:bg-gray-700 rounded-lg transition-colors"
              title="Toggle chat history"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          )}
          
          <div className="flex items-center space-x-2">
            <h1 className="text-white font-semibold text-lg">Panacea</h1>
            <svg 
              className="w-4 h-4 text-gray-400" 
              fill="none" 
              stroke="currentColor" 
              viewBox="0 0 24 24"
            >
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
            {props.isGuestMode && (
              <span className="text-xs text-gray-300 bg-gray-700 px-2 py-1 rounded-full ml-2">
                Guest
              </span>
            )}
          </div>
        </div>

        {/* Right side - Auth buttons */}
        <div className="flex items-center space-x-3">
          {props.isGuestMode ? (
            <>
              <button
                onClick={() => props.onRequestLogin && props.onRequestLogin()}
                className="text-gray-300 hover:text-white px-3 py-1.5 text-sm font-medium transition-colors"
              >
                Log in
              </button>
              <button
                onClick={() => props.onRequestLogin && props.onRequestLogin()}
                className="bg-white hover:bg-gray-100 text-black px-4 py-1.5 rounded-lg text-sm font-medium transition-colors"
              >
                Sign up for free
              </button>
            </>
          ) : (
            <div className="relative user-dropdown">
              <button
                onClick={() => setShowUserDropdown(!showUserDropdown)}
                className="flex items-center space-x-2 p-1 rounded-lg hover:bg-gray-700 transition-colors"
              >
                <div className="w-8 h-8 bg-gray-700 rounded-full flex items-center justify-center">
                  <span className="text-sm font-medium text-gray-300">U</span>
                </div>
                <svg 
                  className={`w-4 h-4 text-gray-400 transform transition-transform ${showUserDropdown ? 'rotate-180' : ''}`}
                  fill="none" 
                  stroke="currentColor" 
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              {/* Dropdown menu */}
              {showUserDropdown && (
                <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50">
                  <div className="py-1">
                    <button
                      onClick={handleLogout}
                      className="w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-gray-700 hover:text-white transition-colors"
                    >
                      Log out
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </nav>
  );
}export default NavbarChatbot;
