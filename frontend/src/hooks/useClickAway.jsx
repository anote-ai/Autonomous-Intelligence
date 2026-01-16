import { useEffect, useRef } from "react";

/**
 * Custom hook that detects clicks outside of the referenced element
 * @param {Function} onClickAway - Callback function to execute when click outside is detected
 * @returns {Object} ref - Ref to attach to the element
 */
const useClickAway = (onClickAway) => {
  const ref = useRef(null);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (ref.current && !ref.current.contains(event.target)) {
        onClickAway();
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    document.addEventListener("touchstart", handleClickOutside);

    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
      document.removeEventListener("touchstart", handleClickOutside);
    };
  }, [onClickAway]);

  return ref;
};

export default useClickAway;
