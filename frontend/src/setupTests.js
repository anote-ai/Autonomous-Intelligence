// jest-dom adds custom jest matchers for asserting on DOM nodes.
// allows you to do things like:
// expect(element).toHaveTextContent(/react/i)
// learn more: https://github.com/testing-library/jest-dom
import '@testing-library/jest-dom';

// Alias jest → vi so pre-existing jest-style tests work under Vitest.
// Guard with typeof so this file can still be loaded by react-scripts/Jest
// (where `vi` doesn't exist) without crashing.
if (typeof vi !== 'undefined') {
  globalThis.jest = vi;
}
