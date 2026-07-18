import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { App } from "./App";
import { AppProviders } from "./providers/AppProviders";
import "./styles/global.css";
import "./styles/theme.css";
import "./styles/admin.css";
import "./styles/chat.css";
import "./styles/widget.css";
import "./styles/json-view.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AppProviders>
        <App />
      </AppProviders>
    </BrowserRouter>
  </React.StrictMode>,
);
