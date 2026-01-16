import { useCallback, useEffect, useRef } from "react";

/**
 * Custom hook to auto-resize a textarea element based on its content.
 * @param {React.RefObject<HTMLTextAreaElement>} textareaRef - Ref to the textarea DOM node
 * @param {string} value - The value of the textarea (dependency)
 * @param {number} maxRows - Maximum number of rows to expand to (optional, default 4)
 */
const useAutoResizeTextarea = (value, maxRows = 4) => {
  const resizeTextarea = useCallback(
    (textarea) => {
      if (!textarea) return;

      // Reset height to get accurate scrollHeight
      textarea.style.height = "auto";

      const scrollHeight = textarea.scrollHeight;
      const styles = window.getComputedStyle(textarea);
      const lineHeight = parseInt(styles.lineHeight);

      // Handle cases where lineHeight might be "normal" or invalid
      const computedLineHeight = isNaN(lineHeight)
        ? parseInt(styles.fontSize) * 1.2
        : lineHeight;

      const maxHeight = computedLineHeight * maxRows;
      textarea.style.height = Math.min(scrollHeight, maxHeight) + "px";

      // Control overflow
      textarea.style.overflowY = scrollHeight > maxHeight ? "auto" : "hidden";
    },
    [maxRows]
  );

  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    resizeTextarea(textarea);
  }, [value, resizeTextarea]);
  return textareaRef;
};

export default useAutoResizeTextarea;
