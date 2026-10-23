import "@testing-library/jest-dom/vitest";

// jsdom has no scrolling; the app scrolls to the top when a report opens.
window.scrollTo = () => {};
