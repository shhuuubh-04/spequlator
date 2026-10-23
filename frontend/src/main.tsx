import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/literata/latin-400.css";
import "@fontsource/literata/latin-600.css";
import "@fontsource/public-sans/latin-400.css";
import "@fontsource/public-sans/latin-600.css";
import "@fontsource/ibm-plex-mono/latin-400.css";
import App from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);