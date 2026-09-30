import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource/anybody/latin-400.css";
import "@fontsource/anybody/latin-ext-400.css";
import "@fontsource/anybody/latin-500.css";
import "@fontsource/anybody/latin-ext-500.css";
import "@fontsource/anybody/latin-600.css";
import "@fontsource/anybody/latin-ext-600.css";
import "@fontsource/manrope/latin-400.css";
import "@fontsource/manrope/latin-ext-400.css";
import "@fontsource/manrope/latin-500.css";
import "@fontsource/manrope/latin-ext-500.css";
import "@fontsource/manrope/latin-600.css";
import "@fontsource/manrope/latin-ext-600.css";
import "@fontsource/jetbrains-mono/latin-500.css";
import "@fontsource/jetbrains-mono/latin-ext-500.css";
import App from "./App";
import { I18nProvider } from "./i18n";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <I18nProvider>
      <App />
    </I18nProvider>
  </StrictMode>,
);
